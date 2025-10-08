import asyncio
import os
from enum import Enum
from operator import itemgetter
from typing import List, Union
from uuid import uuid4

os.environ.setdefault("FAISS_OPT_LEVEL", "GENERIC")
import faiss
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_anthropic import ChatAnthropic
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.language_models import LanguageModelLike
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import BaseLLMOutputParser, StrOutputParser
from langchain_core.prompts import (ChatPromptTemplate,
                                    MessagesPlaceholder, PromptTemplate,
                                    format_document)
from langchain_core.runnables import (RunnableLambda,
                                      RunnablePassthrough,
                                      RunnableWithMessageHistory)
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pydantic import BaseModel, Field

from lib.core import ChatSettings
from lib.user_profile import get_user_profile_manager, get_current_user_id, get_current_session_id
from lib.mcp_client import get_mcp_client

LLMS = Enum("LLMS", ["OPENAI", "ANTROPHIC", "OLLAMA"])
EMBEDDINGS = Enum("EMBEDDINGS", ["openai", "huggingface"])

class UptatableChatHistory(BaseChatMessageHistory, BaseModel):
    messages: List[BaseMessage] = Field(default_factory=list)
    
    def check_message_update(self, message_or_id: BaseMessage | str):
        id = message_or_id.id if isinstance(message_or_id, BaseMessage) else message_or_id
        existing = next((x for x in self.messages if x.id == id), None)
        if existing:
            index = self.messages.index(existing)
            del self.messages[-(len(self.messages) - index):] 

    def add_message(self, message: BaseMessage) -> None:
        self.check_message_update(message)
        return super().add_message(message)
    
    def add_messages(self, messages: List[BaseMessage]) -> None:
        self.messages.extend(messages)

    def clear(self) -> None:
        self.messages = []

class Rag:
    def __init__(self, inputFolder: str, promptFile: str, output_formatter: BaseLLMOutputParser = StrOutputParser(), embedding: EMBEDDINGS = EMBEDDINGS.openai, contextualize_prompt: str = None, structured_output = None,  chat_settings: ChatSettings = ChatSettings(), enable_mcp: bool = True):
        inputFiles = os.listdir(f"rag_source/{inputFolder}")
        self.inputFiles = list(map(lambda x: os.path.abspath(f"rag_source/{inputFolder}/{x}"), inputFiles))
        with open(f"prompt/{promptFile}", "r") as file:
            prompt = file.read()
        system_prompt = prompt + "\n\n" + """
            User Context Information:
            {user_context}

            Use this information about the user to provide more personalized and relevant responses.
            If the user context contains preferences about communication style, response format, or specific interests, please incorporate them into your response.
            If the user context contains the user's name, address them by name.
            If the user context mentions test results or medical history, you can reference this when relevant.
            """
        
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder("chat_history"),
            #("system", "Generate JSON based on the format you are given before."),
            ("human", "{input}")
        ])
        self.enable_mcp = enable_mcp
        self.structured_output = structured_output
        self.embedding = embedding
        self.chat_settings = chat_settings
        self.inputFolder =  inputFolder
        self.output_formatter = output_formatter
        self.llm_functions = {
            LLMS.OPENAI: ChatOpenAI,
            LLMS.ANTROPHIC: ChatAnthropic,
            LLMS.OLLAMA: ChatOllama,
        }
        self.contextualize_prompt = contextualize_prompt or (
            """Given a chat history and the latest user question \
            which might reference context in the chat history, formulate a standalone question \
            which can be understood without the chat history. """ 
        )
        
        self.contextualize_template = ChatPromptTemplate.from_messages(
            [
                ("system", self.contextualize_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "Latest Question: {input}")
            ]
        )
        
        self.contextualize_llm = None

        
    def get_embedding(self) -> Union[OpenAIEmbeddings, HuggingFaceEmbeddings]:
        if self.embedding == EMBEDDINGS.openai:
            return OpenAIEmbeddings(api_key=os.getenv("OPENAI_API_KEY"))
        elif self.embedding == EMBEDDINGS.huggingface:
            model_kwargs = {'device': 'mps'}
            encode_kwargs = {'normalize_embeddings': False}
            hf = HuggingFaceEmbeddings(
                model_name=os.getenv("HUGGINGFACE_EMBED_MODEL"),
                model_kwargs=model_kwargs,
                encode_kwargs=encode_kwargs
            )
            return hf
        
    def create_vector_store(self) -> FAISS:
        embedding = self.get_embedding()
        index = faiss.IndexFlatL2(len(embedding.embed_query("hello world")))
        vector_store = FAISS(
            embedding_function=embedding,
            docstore=InMemoryDocstore(),
            index=index,
            index_to_docstore_id={}
        )
        
        return vector_store
    
    def initialize_store(self) -> FAISS:
        embedding = self.get_embedding()
        base_store_path = os.getenv("VECTOR_STORE_PATH", "vector_store")
        dir = os.path.join(
            base_store_path,
            self.inputFolder,
            self.embedding.name,
            self.inputFolder,
        )
        chunkSize: int = 2000
        chunkOverlap: int = 400
        self.store: FAISS = None
        if os.path.exists(dir):
            self.store = store = FAISS.load_local(
                dir, embedding, allow_dangerous_deserialization=True
            )
            print(f"Loading from local store {dir}")
        else:
            documents = []
            for file in self.inputFiles:
                ext = os.path.splitext(file)[1].lower()
                if ext == ".pdf":
                    loader = PyPDFLoader(file)
                elif ext in {".md", ".txt", ".json"}:
                    loader = TextLoader(file, encoding="utf-8")
                else:
                    raise ValueError(f"Unsupported document type for RAG source: {file}")
                documents.extend(loader.load())
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunkSize, chunk_overlap=chunkOverlap)
            splits = text_splitter.split_documents(documents)
            uuids = [str(uuid4()) for _ in range(len(splits))]
            self.store = self.create_vector_store()
            self.store.add_documents(documents=splits, ids=uuids)
            self.store.save_local(dir)
            print(f"Saved to local store {dir}")
            
        
    def create_runnable(self, llm: LanguageModelLike) -> RunnableWithMessageHistory:   
        
        def format_docs(inputs: dict) -> str:
            return "\n\n".join(
                format_document(doc, PromptTemplate.from_template("{page_content}")) for doc in inputs["context"]
            )
        
        async def get_user_context_async(inputs: dict) -> str:
            """Get user context from MCP if enabled"""
            if not self.enable_mcp:
                return ""
            
            try:
                user_id = get_current_user_id()
                session_id = get_current_session_id()
                print(f"DEBUG: Getting context for user: {user_id}, session: {session_id}")
                
                # Get base user context
                profile_manager = await get_user_profile_manager()
                context = await profile_manager.get_user_context_for_rag(user_id, session_id)
                
                # Check if query is about orders and get order info if needed
                query_text = inputs.get("input", "").lower()
                order_keywords = [
                    "đơn hàng",
                    "order",
                    "giao",
                    "delivery",
                    "vận chuyển",
                    "ship",
                    "thanh toán",
                    "payment",
                    "sắp giao",
                    "chờ giao",
                    "pending",
                    "hoàn thành",
                    "completed",
                    "trung bình",
                    "average",
                    "cao nhất",
                    "highest",
                    "thấp nhất",
                    "lowest",
                    "giá trị",
                    "giá",
                    "tổng quan",
                    "thống kê"
                ]
                balance_keywords = [
                    "số dư",
                    "balance",
                    "điểm o2",
                    "điểm 02",
                    "o2 points",
                    "balance điểm",
                    "điểm thưởng",
                    "tài khoản",
                    "points balance",
                    "ví"
                ]

                if any(keyword in query_text for keyword in order_keywords):
                    try:
                        print(f"DEBUG: Query about orders detected, getting order context...")
                        mcp_client = await get_mcp_client()

                        pending_keywords = [
                            "chờ giao",
                            "pending",
                            "đang chờ",
                            "chưa giao",
                            "chưa nhận",
                            "đơn hàng chưa",
                            "đơn hàng nào chưa",
                            "đơn hàng nào",
                            "còn giao",
                            "đơn chưa hoàn thành",
                            "đơn đang xử lý"
                        ]
                        payment_keywords = [
                            "tiền",
                            "thanh toán",
                            "phải trả",
                            "payment",
                            "money",
                            "công nợ",
                            "còn nợ"
                        ]
                        delivery_keywords = [
                            "giao hàng",
                            "delivery",
                            "dự kiến",
                            "khi nào đến",
                            "bao giờ giao",
                            "sắp giao",
                            "khi nào nhận",
                            "ngày giao",
                            "bao giờ đến"
                        ]
                        summary_keywords = [
                            "tổng quan",
                            "summary",
                            "thống kê",
                            "overview",
                            "tình hình",
                            "báo cáo",
                            "toàn cảnh"
                        ]
                        recent_keywords = [
                            "gần đây",
                            "recent",
                            "mới nhất",
                            "latest",
                            "gần nhất",
                            "vừa đặt"
                        ]
                        completed_keywords = [
                            "hoàn thành",
                            "completed",
                            "đã giao",
                            "đơn đã xong",
                            "đơn hoàn tất"
                        ]
                        latest_order_keywords = [
                            "đơn mới nhất",
                            "latest order",
                            "vừa đặt",
                            "gần đây nhất",
                            "đơn cuối cùng",
                            "last order"
                        ]
                        next_delivery_keywords = [
                            "sắp giao",
                            "next delivery",
                            "đơn tiếp theo",
                            "sớm nhất",
                            "khi nào đến",
                            "bao giờ nhận"
                        ]
                        highest_value_keywords = [
                            "cao nhất",
                            "highest value",
                            "đơn giá trị nhất",
                            "đơn đắt nhất",
                            "max order"
                        ]
                        lowest_value_keywords = [
                            "thấp nhất",
                            "lowest value",
                            "đơn rẻ nhất",
                            "đơn giá trị thấp",
                            "min order"
                        ]
                        average_value_keywords = [
                            "trung bình",
                            "average",
                            "giá trị trung bình",
                            "chi tiêu trung bình",
                            "avg order"
                        ]

                        pending_requested = any(keyword in query_text for keyword in pending_keywords)
                        payment_requested = any(keyword in query_text for keyword in payment_keywords)
                        delivery_requested = any(keyword in query_text for keyword in delivery_keywords)
                        summary_requested = any(keyword in query_text for keyword in summary_keywords)
                        recent_requested = any(keyword in query_text for keyword in recent_keywords)
                        completed_requested = any(keyword in query_text for keyword in completed_keywords)
                        latest_requested = any(keyword in query_text for keyword in latest_order_keywords)
                        next_delivery_requested = any(keyword in query_text for keyword in next_delivery_keywords)
                        highest_value_requested = any(keyword in query_text for keyword in highest_value_keywords)
                        lowest_value_requested = any(keyword in query_text for keyword in lowest_value_keywords)
                        average_value_requested = any(keyword in query_text for keyword in average_value_keywords)

                        order_context_sections: List[str] = []

                        if pending_requested:
                            try:
                                pending = await mcp_client.get_pending_orders_count(user_id)
                                if pending and not pending.get("error"):
                                    orders_count = pending.get("pending_orders_count", 0)
                                    items_count = pending.get("pending_items_count", 0)
                                    order_context_sections.append(
                                        f"- Pending orders: {orders_count} (items awaiting delivery: {items_count})"
                                    )
                                else:
                                    order_context_sections.append("- Pending orders: No data available")
                            except Exception as pending_error:
                                print(f"DEBUG: Error getting pending orders: {pending_error}")
                                order_context_sections.append("- Pending orders: Unable to retrieve data")

                        if payment_requested:
                            try:
                                payment = await mcp_client.get_pending_payment_amount(user_id)
                                if payment and not payment.get("error"):
                                    unpaid_amount = payment.get("unpaid_amount", 0) or 0
                                    unpaid_orders = payment.get("unpaid_orders", 0)
                                    total_pending_amount = payment.get("total_pending_amount", 0) or 0
                                    order_context_sections.append(
                                        f"- Outstanding payments: {unpaid_amount:,} VND across {unpaid_orders} unpaid orders (total processing value: {total_pending_amount:,} VND)"
                                    )
                                else:
                                    order_context_sections.append("- Outstanding payments: No data available")
                            except Exception as payment_error:
                                print(f"DEBUG: Error getting payment data: {payment_error}")
                                order_context_sections.append("- Outstanding payments: Unable to retrieve data")

                        if delivery_requested:
                            try:
                                deliveries = await mcp_client.get_delivery_estimates(user_id, 7)
                                if deliveries and not deliveries.get("error"):
                                    upcoming = deliveries.get("upcoming_deliveries", 0)
                                    estimates = deliveries.get("delivery_estimates", []) or []
                                    if estimates:
                                        first_estimate = estimates[0]
                                        order_context_sections.append(
                                            f"- Upcoming deliveries (next 7 days): {upcoming}. Next order {first_estimate.get('order_id', 'N/A')} expected between {first_estimate.get('estimated_delivery_min', '')[:10]} and {first_estimate.get('estimated_delivery_max', '')[:10]}"
                                        )
                                    else:
                                        order_context_sections.append(
                                            f"- Upcoming deliveries (next 7 days): {upcoming}"
                                        )
                                else:
                                    order_context_sections.append("- Upcoming deliveries: No data available")
                            except Exception as delivery_error:
                                print(f"DEBUG: Error getting delivery estimates: {delivery_error}")
                                order_context_sections.append("- Upcoming deliveries: Unable to retrieve data")

                        if next_delivery_requested:
                            try:
                                next_order_result = await mcp_client.get_next_delivery_order(user_id)
                                next_order = next_order_result.get("next_delivery_order") if next_order_result else None
                                if next_order and not next_order_result.get("error"):
                                    order_context_sections.append(
                                        "- Next delivery: {order_id} expected between {min_date} and {max_date} (value: {value:,} VND)".format(
                                            order_id=next_order.get("order_id", "N/A"),
                                            min_date=next_order.get("estimated_delivery_min", "")[:10],
                                            max_date=next_order.get("estimated_delivery_max", "")[:10],
                                            value=next_order.get("total_value", 0) or 0
                                        )
                                    )
                                else:
                                    order_context_sections.append("- Next delivery: No upcoming shipments found")
                            except Exception as next_delivery_error:
                                print(f"DEBUG: Error getting next delivery order: {next_delivery_error}")
                                order_context_sections.append("- Next delivery: Unable to retrieve data")

                        if summary_requested:
                            try:
                                summary_result = await mcp_client.get_order_summary(user_id)
                                summary_data = summary_result.get("summary") if summary_result else None
                                if summary_data and not summary_result.get("error"):
                                    order_context_sections.append(
                                        "- Order summary: {total_orders} orders, {total_items} items, total value {total_value:,} VND (delivered: {delivered_items}, shipping: {shipping_items}, pending: {pending_items})".format(
                                            total_orders=summary_data.get("total_orders", 0),
                                            total_items=summary_data.get("total_items", 0),
                                            total_value=summary_data.get("total_value", 0) or 0,
                                            delivered_items=summary_data.get("delivered_items", 0),
                                            shipping_items=summary_data.get("shipping_items", 0),
                                            pending_items=summary_data.get("pending_items", 0)
                                        )
                                    )
                                else:
                                    order_context_sections.append("- Order summary: No data available")
                            except Exception as summary_error:
                                print(f"DEBUG: Error getting order summary: {summary_error}")
                                order_context_sections.append("- Order summary: Unable to retrieve data")

                        if completed_requested:
                            try:
                                completed = await mcp_client.get_completed_orders_summary(user_id)
                                if completed and not completed.get("error"):
                                    order_context_sections.append(
                                        "- Completed orders: {count} orders, {items} items, total {total:,} VND".format(
                                            count=completed.get("completed_orders", 0),
                                            items=completed.get("completed_items", 0),
                                            total=completed.get("completed_value", 0) or 0
                                        )
                                    )
                                else:
                                    order_context_sections.append("- Completed orders: No data available")
                            except Exception as completed_error:
                                print(f"DEBUG: Error getting completed orders summary: {completed_error}")
                                order_context_sections.append("- Completed orders: Unable to retrieve data")

                        if recent_requested:
                            try:
                                recent = await mcp_client.get_recent_orders(user_id, 5)
                                print(f"DEBUG: Recent orders data: {recent}")
                                if recent and not recent.get("error"):
                                    orders = recent.get("recent_orders", []) or []
                                    if orders:
                                        recent_lines = [
                                            "- Recent orders:"
                                        ]
                                        for order in orders[:3]:
                                            recent_lines.append(
                                                f"  * {order.get('order_id', 'N/A')} ({order.get('status', 'unknown')}) - {order.get('total_value', 0):,} VND"
                                            )
                                        order_context_sections.append("\n".join(recent_lines))
                                    else:
                                        order_context_sections.append("- Recent orders: No recent orders found")
                                else:
                                    order_context_sections.append("- Recent orders: No data available")
                            except Exception as recent_error:
                                print(f"DEBUG: Error getting recent orders: {recent_error}")
                                order_context_sections.append("- Recent orders: Unable to retrieve data")

                        if latest_requested and not recent_requested:
                            try:
                                latest = await mcp_client.get_latest_order(user_id)
                                latest_data = latest.get("latest_order") if latest else None
                                if latest_data and not latest.get("error"):
                                    order_context_sections.append(
                                        "- Latest order: {order_id} ({items} items) {status} on {date} worth {value:,} VND".format(
                                            order_id=latest_data.get("order_id", "N/A"),
                                            items=latest_data.get("item_count", 0),
                                            status="completed" if latest_data.get("is_completed") else "in progress",
                                            date=(latest_data.get("created_at") or "")[:10],
                                            value=latest_data.get("total_value", 0) or 0
                                        )
                                    )
                                else:
                                    order_context_sections.append("- Latest order: No data available")
                            except Exception as latest_error:
                                print(f"DEBUG: Error getting latest order: {latest_error}")
                                order_context_sections.append("- Latest order: Unable to retrieve data")

                        if highest_value_requested:
                            try:
                                highest = await mcp_client.get_highest_value_order(user_id)
                                highest_data = highest.get("highest_value_order") if highest else None
                                if highest_data and not highest.get("error"):
                                    order_context_sections.append(
                                        "- Highest value order: {order_id} worth {value:,} VND ({items} items)".format(
                                            order_id=highest_data.get("order_id", "N/A"),
                                            value=highest_data.get("total_value", 0) or 0,
                                            items=highest_data.get("item_count", 0)
                                        )
                                    )
                                else:
                                    order_context_sections.append("- Highest value order: No data available")
                            except Exception as highest_error:
                                print(f"DEBUG: Error getting highest value order: {highest_error}")
                                order_context_sections.append("- Highest value order: Unable to retrieve data")

                        if lowest_value_requested:
                            try:
                                lowest = await mcp_client.get_lowest_value_order(user_id)
                                lowest_data = lowest.get("lowest_value_order") if lowest else None
                                if lowest_data and not lowest.get("error"):
                                    order_context_sections.append(
                                        "- Lowest value order: {order_id} worth {value:,} VND ({items} items)".format(
                                            order_id=lowest_data.get("order_id", "N/A"),
                                            value=lowest_data.get("total_value", 0) or 0,
                                            items=lowest_data.get("item_count", 0)
                                        )
                                    )
                                else:
                                    order_context_sections.append("- Lowest value order: No data available")
                            except Exception as lowest_error:
                                print(f"DEBUG: Error getting lowest value order: {lowest_error}")
                                order_context_sections.append("- Lowest value order: Unable to retrieve data")

                        if average_value_requested:
                            try:
                                average = await mcp_client.get_average_order_value(user_id)
                                if average and not average.get("error"):
                                    order_context_sections.append(
                                        "- Average order value: {value:,} VND".format(
                                            value=average.get("average_order_value", 0) or 0
                                        )
                                    )
                                else:
                                    order_context_sections.append("- Average order value: No data available")
                            except Exception as average_error:
                                print(f"DEBUG: Error getting average order value: {average_error}")
                                order_context_sections.append("- Average order value: Unable to retrieve data")

                        if order_context_sections:
                            order_context = "\nOrder Information:\n" + "\n".join(order_context_sections)
                            context = (context or "") + order_context
                        else:
                            # Fallback to dashboard if no specific tool matched the query intent
                            order_dashboard = await mcp_client.get_user_order_dashboard(user_id)
                            if order_dashboard and "dashboard" in order_dashboard:
                                dashboard_data = order_dashboard["dashboard"]
                                order_context = f"\nOrder Information:\n"
                                order_context += f"- Pending orders: {dashboard_data.get('pending_orders', {}).get('count', 0)}\n"
                                order_context += f"- Unpaid amount: {dashboard_data.get('financial', {}).get('unpaid_amount', 0):,} VND\n"
                                order_context += f"- Upcoming deliveries (7 days): {dashboard_data.get('deliveries', {}).get('upcoming_7_days', 0)}\n"

                                recent_orders = dashboard_data.get('recent_orders', [])
                                if recent_orders:
                                    order_context += f"- Recent orders:\n"
                                    for order in recent_orders[:3]:
                                        order_context += f"  * {order.get('order_id', 'N/A')} ({order.get('status', 'unknown')}) - {order.get('total_value', 0):,} VND\n"

                                context = (context or "") + order_context
                            else:
                                context = (context or "") + "\nOrder Information: No order data available for this user."

                    except Exception as order_error:
                        print(f"DEBUG: Error getting order context: {order_error}")
                        context = (context or "") + f"\nOrder Information: Unable to retrieve order data (Error: {str(order_error)})"

                if any(keyword in query_text for keyword in balance_keywords):
                    try:
                        print(f"DEBUG: Query about balance detected, getting balance context...")
                        mcp_client = await get_mcp_client()
                        balance_result = await mcp_client.query_user_data(
                            user_id,
                            "balance điểm 02 information"
                        )

                        balance_context = "\nAccount Balance Information:\n"
                        result_payload = balance_result.get("result") if balance_result else None
                        balance_payload = result_payload.get("balance") if isinstance(result_payload, dict) else None

                        if isinstance(balance_payload, dict):
                            formatted_balance = balance_payload.get("formatted")
                            points_formatted = balance_payload.get("points_formatted")
                            raw_value = balance_payload.get("value") or balance_payload.get("amount")
                            raw_points = balance_payload.get("points")

                            if formatted_balance:
                                balance_context += f"- Available balance: {formatted_balance}\n"
                            elif raw_value is not None:
                                balance_context += f"- Available balance: {raw_value}\n"

                            if points_formatted:
                                balance_context += f"- Loyalty points: {points_formatted}\n"
                            elif raw_points is not None:
                                balance_context += f"- Loyalty points: {raw_points}\n"

                            if balance_context.strip() == "Account Balance Information:":
                                balance_context += "- No detailed balance fields provided.\n"
                        else:
                            balance_context += "- No balance data available for this user.\n"

                        context = (context or "") + balance_context
                    except Exception as balance_error:
                        print(f"DEBUG: Error getting balance context: {balance_error}")
                        context = (context or "") + f"\nAccount Balance Information: Unable to retrieve balance data (Error: {str(balance_error)})"
                
                print(f"DEBUG: Retrieved MCP context: {context}")
                return context if context else f"User ID: {user_id}"
                
            except Exception as e:
                print(f"Error getting user context: {e}")
                try:
                    user_id = get_current_user_id()
                    return f"User ID: {user_id}"
                except Exception:
                    return "User context unavailable"
        
        def ensureContextualize(input_: dict):
            retriever = RunnableLambda(lambda input: self.store.similarity_search(input, k=4))
            if self.contextualize_llm is None or input_.get("chat_history") is None or len(input_.get("chat_history")) == 0:
                return RunnablePassthrough().assign(context=itemgetter("input") | retriever)
            else:
                return  ( self.contextualize_template 
                        | self.contextualize_llm 
                        | RunnableLambda(lambda x: input_ | {"input_contextual": x.content}) 
                        | RunnablePassthrough().assign(context=itemgetter("input") | retriever)
                        )
                
        rag_chain = ( RunnableLambda(ensureContextualize).with_config({"run_name":"ContextualizationCheck"}) 
                    | RunnablePassthrough.assign(context = format_docs).with_config({"run_name":"QueryDocuments"})
                    | RunnablePassthrough.assign(user_context = RunnableLambda(get_user_context_async)).with_config({"run_name":"GetUserContext"})
                    | self.prompt_template 
                    | llm 
                    | self.output_formatter
                    )
        
        return rag_chain
    

    def create_llm(self, llm_type: LLMS, model: str = None, chat_settings: ChatSettings = None) -> LanguageModelLike:
        model = model if model else os.getenv(f"{llm_type.name.upper()}_MODEL")
        chat_settings = chat_settings if chat_settings else self.chat_settings
        args = {
           "streaming": True,
           "model": model,
           "api_key": os.getenv(f"{llm_type.name.upper()}_API_KEY"),
           "temperature": chat_settings.temperature,
           "top_p": chat_settings.top_p,
        }

        
        llm = self.llm_functions[llm_type](**args)
        llm = llm if self.structured_output == None else llm.with_structured_output(self.structured_output)
        return llm
    
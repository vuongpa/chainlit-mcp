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
                order_keywords = ["đơn hàng", "order", "giao hàng", "delivery", "vận chuyển", "ship", "thanh toán", "payment", "sắp giao", "chờ giao", "pending"]
                
                if any(keyword in query_text for keyword in order_keywords):
                    try:
                        print(f"DEBUG: Query about orders detected, getting order context...")
                        from lib.mcp_client import get_mcp_client
                        mcp_client = await get_mcp_client()
                        
                        # Get order dashboard for user
                        order_dashboard = await mcp_client.get_user_order_dashboard(user_id)
                        if order_dashboard and "dashboard" in order_dashboard:
                            dashboard_data = order_dashboard["dashboard"]
                            order_context = f"\nOrder Information:\n"
                            order_context += f"- Pending orders: {dashboard_data.get('pending_orders', {}).get('count', 0)}\n"
                            order_context += f"- Unpaid amount: {dashboard_data.get('financial', {}).get('unpaid_amount', 0):,} VND\n"
                            order_context += f"- Upcoming deliveries (7 days): {dashboard_data.get('deliveries', {}).get('upcoming_7_days', 0)}\n"
                            
                            # Add recent orders info
                            recent_orders = dashboard_data.get('recent_orders', [])
                            if recent_orders:
                                order_context += f"- Recent orders:\n"
                                for order in recent_orders[:3]:  # Top 3
                                    order_context += f"  * {order.get('order_id', 'N/A')} ({order.get('status', 'unknown')}) - {order.get('total_value', 0):,} VND\n"
                            
                            context = (context or "") + order_context
                        else:
                            context = (context or "") + "\nOrder Information: No order data available for this user."
                        
                        # Keep the MCP client alive for reuse within the same event loop
                        
                    except Exception as order_error:
                        print(f"DEBUG: Error getting order context: {order_error}")
                        context = (context or "") + f"\nOrder Information: Unable to retrieve order data (Error: {str(order_error)})"
                
                print(f"DEBUG: Retrieved MCP context: {context}")
                return context if context else f"User ID: {user_id}"
                
            except Exception as e:
                print(f"Error getting user context: {e}")
                return f"User ID: {get_current_user_id() if 'get_current_user_id' in globals() else 'unknown'}"
        
        def get_user_context(inputs: dict) -> str:
            """Sync wrapper for user context retrieval"""
            try:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        user_id = get_current_user_id()
                        return f"User ID: {user_id}"
                    else:
                        return loop.run_until_complete(get_user_context_async(inputs))
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(get_user_context_async(inputs))
                    finally:
                        loop.close()
                        
            except Exception as e:
                print(f"Error in sync user context wrapper: {e}")
                try:
                    user_id = get_current_user_id()
                    return f"User ID: {user_id}"
                except:
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
                    | RunnablePassthrough.assign(user_context = RunnableLambda(get_user_context)).with_config({"run_name":"GetUserContext"})
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
    
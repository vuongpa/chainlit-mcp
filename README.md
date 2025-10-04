# ChatBot with RAG App

This sample app enables intelligent, dynamic interactions by retrieving relevant information from a vector store and addressing users personally based on their queries.

## Features

**Contextualization**: The bot can contextualize user questions and retrieve more relevant chunks from the vector store, improving the accuracy of its responses.

**Reusable classes**: The app includes reusable classes for handling RAG, chat settings, chat history  and more.

**Follow-up questions**: App generates intelligent follow-up questions to drive deeper engagement.

**Updatable chat history**: Users can update previous messages in the conversation.

**Authentication and personalized user interactions**: The bot authenticates users and addresses them by their name during interactions.

**Speech To Text and Text to Speech**: This app provides a seamless chat experience with speech-to-text and text-to-speech capabilities, enhancing accessibility and convenience for users.

![Sample](/assets/home-screen.png?raw=true "Rag Demo using LangChain, Chainlit, Faiss & FastApi")

## Setup

Run quick_start.sh file or install dependencies and run the application using uv:

```bash
# Sync dependencies
uv sync

# Create virtual environment
uv venv .venv
source .venv/bin/activate

# Set API keys
Rename .env.sample file to .env file and add your API keys. 

# Start the application
uv run src/main.py
```

## To Use Your Prompt & Data

By default, the repository is configured with the Oreka.vn customer support knowledge base.

- Prompt: prompt/oreka_faqs.txt
- Knowledge source: rag_source/oreka_faqs/zendesk-2025-10-04T06-54-33.md

To use your own prompt and data, follow these steps:

Place your custom prompt inside the prompt folder (e.g., myprompt.txt), and upload the corresponding PDF files to the rag_source folder (e.g., rag_source/myrag/myfile.pdf).

Update create_rag method in src/chat_app.py file.

```python
rag = Rag(
    inputFolder="myrag",
    promptFile="myprompt.txt",
    chat_settings=chat_settings
)
```

## Text to Speech (TTS)

To use TTS:

1.Add below environment variables.

```bash
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=
```

2.Open chat settings and enable TTS.

![Sample](/assets/settings.png?raw=true "TTS")

## Contextualization

You can enable or disable contextualization by setting the environment variable:

```bash
CONTEXTUALIZATION=True
```

### What is contextualization?

Contextualization allows the chatbot to better understand user queries by maintaining a reference to previous interactions, improving the relevance of retrieved information.

## Embeddings

There are two options for generating embeddings: OpenAI or HuggingFace (the default is OpenAI).

To configure the HuggingFace embedding model, set the HUGGINGFACE_EMBED_MODEL environment variable with your desired model. For example:

```bash
HUGGINGFACE_EMBED_MODEL=sentence-transformers/all-mpnet-base-v2
```

To switch to OpenAI embeddings, update the RAG instance in the src/chainlit_start.py file as follows:

```python
rag = ChainlitRag.rag = Rag(
    ...
    chat_settings=chat_settings,
    embedding=EMBEDDINGS.openai,  # Use OpenAI embeddings
    output_formatter=JsonOutputParser(pydantic_object=ResultWithFollowup)
)
```

Make sure to set your OpenAI API key in your .env file if you choose OpenAI embeddings.

## More Info

- [Chainlit Documentation](https://docs.chainlit.io/get-started/overview) - Learn more about Chainlit and how to customize it.
- [LangChain Documentation](https://www.langchain.com/) - Understand how LangChain can be used for chaining AI models with various tools and services.
- [Faiss Documentation](https://faiss.ai) – Explore how Faiss performs vector similarity search.
- [FastAPI Documentation](https://fastapi.tiangolo.com) – Learn more about FastAPI and how to use it to build high-performance APIs.

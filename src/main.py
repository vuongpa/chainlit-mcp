import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from chainlit.utils import mount_chainlit
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from lib.database import DatabaseManager

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting application...")
    if DatabaseManager.test_connection():
        print("✅ Database connection established")
    else:
        print("❌ Warning: Database connection failed")
    yield
    print("🔄 Shutting down application...")
    DatabaseManager.close_connections()
    print("✅ Database connections closed")

def run_application():
    uvicorn.run(app="main:create_app",
            factory=True,
            reload=True)

def create_app() -> FastAPI:
    app = FastAPI(
        title="Chatbot with RAG",
        description="RAG (Retrieval-Augmented Generation) ChatBot app built using Chainlit, LangChain, Faiss, and FastAPI",
        version="0.1.0",
        lifespan=lifespan
    )
    
    mount_chainlit(app=app, target="src/start.py", path="/chat")
    
    @app.get("/")
    def read_root():
        return RedirectResponse("/chat")
    
    @app.get("/health")
    def health_check():
        """Health check endpoint"""
        db_status = DatabaseManager.test_connection()
        return {
            "status": "healthy" if db_status else "unhealthy",
            "database": "connected" if db_status else "disconnected"
        }
    
    return app


if __name__ == "__main__":
    run_application()
import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from pathlib import Path

import chainlit as cl
from pydantic import BaseModel, Field

from lib.mcp_client import MCPClient, UserProfile, get_mcp_client, close_mcp_client


class UserSession(BaseModel):
    """Enhanced user session with MCP integration"""
    user_id: str
    session_id: str
    profile: Optional[UserProfile] = None
    preferences: Dict[str, Any] = Field(default_factory=dict)
    context_history: List[Dict[str, Any]] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.now)
    active_topics: Set[str] = Field(default_factory=set)


class UserProfileManager:
    """Manages user profiles and sessions with MCP integration"""
    
    def __init__(self, cache_dir: str = "user_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self._session_cache = {}
        self._mcp_client: Optional[MCPClient] = None
        self._mcp_loop: Optional[asyncio.AbstractEventLoop] = None
    
    async def initialize(self):
        """Initialize MCP client"""
        await self._get_mcp_client()

    async def _get_mcp_client(self) -> Optional[MCPClient]:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return None

        if self._mcp_client and self._mcp_loop is loop:
            return self._mcp_client

        try:
            client = await get_mcp_client()
            self._mcp_client = client
            self._mcp_loop = loop
            return client
        except Exception as e:
            print(f"Warning: Could not initialize MCP client: {e}")
            self._mcp_client = None
            self._mcp_loop = None
            return None
    
    async def get_or_create_session(self, user_identifier: str, session_id: str) -> UserSession:
        """Get or create user session with MCP profile data"""
        session_key = f"{user_identifier}:{session_id}"
        
        # Check memory cache first
        if session_key in self._session_cache:
            return self._session_cache[session_key]
        
        # Try to load from disk cache
        session = await self._load_session_from_cache(user_identifier, session_id)
        if session:
            self._session_cache[session_key] = session
            return session
        
        # Create new session
        session = UserSession(
            user_id=user_identifier,
            session_id=session_id
        )
        
        # Try to enrich with MCP data
        mcp_client = await self._get_mcp_client()
        if mcp_client:
            try:
                profile = await mcp_client.get_user_profile(user_identifier)
                if profile:
                    session.profile = profile
                    session.preferences = profile.preferences
                    session.context_history = profile.history[-20:]  # Last 20 interactions
            except Exception as e:
                print(f"Could not fetch MCP profile for {user_identifier}: {e}")
        
        self._session_cache[session_key] = session
        await self._save_session_to_cache(session)
        return session
    
    async def update_session_context(self, user_identifier: str, session_id: str, 
                                   message: str, response: str, topic: str = None):
        """Update session with new interaction context"""
        session = await self.get_or_create_session(user_identifier, session_id)
        
        # Add to context history
        context_item = {
            "timestamp": datetime.now().isoformat(),
            "user_message": message,
            "bot_response": response,
            "topic": topic
        }
        
        session.context_history.append(context_item)
        # Keep only last 50 interactions
        session.context_history = session.context_history[-50:]
        
        if topic:
            session.active_topics.add(topic)
        
        session.last_updated = datetime.now()
        
        # Update cache
        session_key = f"{user_identifier}:{session_id}"
        self._session_cache[session_key] = session
        await self._save_session_to_cache(session)
    
    async def get_user_preferences(self, user_identifier: str, keys: List[str] = None) -> Dict[str, Any]:
        """Get user preferences, trying MCP first, then local cache"""
        preferences = {}
        
        # Try MCP first
        mcp_client = await self._get_mcp_client()
        if mcp_client:
            try:
                mcp_preferences = await mcp_client.get_user_preferences(user_identifier, keys)
                preferences.update(mcp_preferences)
            except Exception as e:
                print(f"Could not fetch MCP preferences: {e}")
        
        # Fallback to session cache
        if user_identifier in [s.split(':')[0] for s in self._session_cache.keys()]:
            for session in self._session_cache.values():
                if session.user_id == user_identifier:
                    if keys:
                        session_prefs = {k: session.preferences.get(k) for k in keys if k in session.preferences}
                    else:
                        session_prefs = session.preferences
                    
                    # Merge with MCP data (session data takes precedence for conflicts)
                    preferences = {**preferences, **session_prefs}
                    break
        
        return preferences
    
    async def get_user_context_for_rag(self, user_identifier: str, session_id: str, 
                                     context_type: str = "relevant") -> str:
        """Get formatted user context for RAG prompt enhancement"""
        session = await self.get_or_create_session(user_identifier, session_id)
        
        context_parts = []
        
        # Add profile information
        if session.profile:
            if session.profile.name:
                context_parts.append(f"User's name: {session.profile.name}")
            
            # Add relevant preferences
            relevant_prefs = {}
            for key, value in session.preferences.items():
                if any(keyword in key.lower() for keyword in ['language', 'communication', 'style', 'format']):
                    relevant_prefs[key] = value
            
            if relevant_prefs:
                prefs_str = ', '.join([f"{k}: {v}" for k, v in relevant_prefs.items()])
                context_parts.append(f"User preferences: {prefs_str}")
            
            # Add balance information for authenticated users
            mcp_client = await self._get_mcp_client()
            if user_identifier != "anonymous" and mcp_client:
                try:
                    balance_result = await mcp_client.query_user_data(
                        user_identifier, 
                        "balance điểm 02 information"
                    )
                    if balance_result and 'result' in balance_result:
                        balance_info = balance_result['result']
                        if 'balance' in balance_info and balance_info['balance']:
                            balance_data = balance_info['balance']
                            context_parts.append(
                                f"User's balance: {balance_data['formatted']} VNĐ, "
                                f"{balance_data['points_formatted']} điểm O2"
                            )
                except Exception as e:
                    print(f"Could not fetch balance info: {e}")
        
        # Add recent conversation topics
        if session.active_topics:
            topics_str = ', '.join(list(session.active_topics)[-5:])  # Last 5 topics
            context_parts.append(f"Recent conversation topics: {topics_str}")
        
        # Add recent interaction context
        recent_interactions = session.context_history[-3:]  # Last 3 interactions
        if recent_interactions:
            context_parts.append("Recent conversation context:")
            for interaction in recent_interactions:
                context_parts.append(f"- User: {interaction['user_message'][:100]}...")
                context_parts.append(f"- Assistant: {interaction['bot_response'][:100]}...")
        
        return "\n".join(context_parts) if context_parts else ""
    
    async def query_user_data(self, user_identifier: str, query: str) -> Optional[Dict[str, Any]]:
        """Query user data using natural language via MCP"""
        mcp_client = await self._get_mcp_client()
        if not mcp_client:
            return None
        
        try:
            return await mcp_client.query_user_data(user_identifier, query)
        except Exception as e:
            print(f"Error querying user data: {e}")
            return None
    
    async def _load_session_from_cache(self, user_identifier: str, session_id: str) -> Optional[UserSession]:
        safe_user_id = user_identifier.replace("@", "_at_").replace("/", "_").replace("\\", "_")
        safe_session_id = session_id.replace("/", "_").replace("\\", "_").replace(":", "_")
        
        cache_file = self.cache_dir / f"{safe_user_id}_{safe_session_id}.json"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
                data['last_updated'] = datetime.fromisoformat(data['last_updated'])
                data['active_topics'] = set(data.get('active_topics', []))
                return UserSession(**data)
        except Exception as e:
            print(f"Error loading session cache: {e}")
            return None
    
    async def _save_session_to_cache(self, session: UserSession):
        safe_user_id = session.user_id.replace("@", "_at_").replace("/", "_").replace("\\", "_")
        safe_session_id = session.session_id.replace("/", "_").replace("\\", "_").replace(":", "_")
        
        cache_file = self.cache_dir / f"{safe_user_id}_{safe_session_id}.json"
        
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            data = session.dict()
            data['last_updated'] = data['last_updated'].isoformat()
            data['active_topics'] = list(data['active_topics'])
            
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving session cache: {e}")
    
    async def cleanup_old_sessions(self, max_age_days: int = 30):
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        to_remove = []
        for key, session in self._session_cache.items():
            if session.last_updated < cutoff_date:
                to_remove.append(key)
        
        for key in to_remove:
            del self._session_cache[key]
        
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                if cache_file.stat().st_mtime < cutoff_date.timestamp():
                    cache_file.unlink()
            except Exception as e:
                print(f"Error cleaning cache file {cache_file}: {e}")
    
    async def close(self):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if self._mcp_client and self._mcp_loop is loop:
            try:
                await close_mcp_client()
            except Exception as e:
                print(f"Error closing MCP client: {e}")
            finally:
                self._mcp_client = None
                self._mcp_loop = None


_user_profile_manager: Optional[UserProfileManager] = None
async def get_user_profile_manager() -> UserProfileManager:
    global _user_profile_manager
    if _user_profile_manager is None:
        _user_profile_manager = UserProfileManager()
        await _user_profile_manager.initialize()
    return _user_profile_manager


def get_current_user_id() -> str:
    user = cl.user_session.get("user")
    if user and hasattr(user, 'identifier'):
        user_id = user.identifier
        # Return the actual user identifier (email/username)
        return user_id
    return "anonymous"


def get_current_session_id() -> str:
    return cl.user_session.get("session_id", "default")
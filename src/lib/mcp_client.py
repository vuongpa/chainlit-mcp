import asyncio
import json
import os
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager

import httpx
from pydantic import BaseModel, Field


class MCPServerConfig(BaseModel):
    """Configuration for MCP server connection"""
    name: str
    command: str
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    url: Optional[str] = None  # For HTTP-based MCP servers


class UserProfile(BaseModel):
    """User profile data from MCP"""
    user_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    preferences: Dict[str, Any] = Field(default_factory=dict)
    history: List[Dict[str, Any]] = Field(default_factory=list)
    custom_data: Dict[str, Any] = Field(default_factory=dict)


class MCPClient:
    """Client for connecting to MCP servers and retrieving user information"""
    
    def __init__(self, servers: List[MCPServerConfig] = None):
        self.servers = servers or []
        self.active_connections = {}
        self._user_cache = {}
        
    async def initialize(self):
        """Initialize connections to MCP servers"""
        for server in self.servers:
            try:
                await self._connect_to_server(server)
            except Exception as e:
                print(f"Failed to connect to MCP server {server.name}: {e}")
    
    async def _connect_to_server(self, server: MCPServerConfig):
        """Connect to a specific MCP server"""
        if server.url:
            # HTTP-based MCP server
            self.active_connections[server.name] = {
                "type": "http",
                "url": server.url,
                "client": httpx.AsyncClient()
            }
        else:
            # Process-based MCP server (stdio)
            process = await asyncio.create_subprocess_exec(
                server.command,
                *server.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, **server.env}
            )
            self.active_connections[server.name] = {
                "type": "process",
                "process": process
            }
    
    async def get_user_profile(self, user_id: str, server_name: str = None) -> Optional[UserProfile]:
        """Retrieve user profile from MCP server"""
        # Check cache first
        cache_key = f"{server_name}:{user_id}" if server_name else user_id
        if cache_key in self._user_cache:
            return self._user_cache[cache_key]
        
        # Try to get from specified server or all servers
        servers_to_try = [server_name] if server_name else list(self.active_connections.keys())
        
        for srv_name in servers_to_try:
            if srv_name not in self.active_connections:
                continue
                
            try:
                profile_data = await self._query_server(srv_name, "get_user_profile", {"user_id": user_id})
                if profile_data:
                    profile = UserProfile(**profile_data)
                    self._user_cache[cache_key] = profile
                    return profile
            except Exception as e:
                print(f"Error querying server {srv_name} for user {user_id}: {e}")
        
        return None
    
    async def get_user_preferences(self, user_id: str, keys: List[str] = None) -> Dict[str, Any]:
        """Get specific user preferences"""
        profile = await self.get_user_profile(user_id)
        if not profile:
            return {}
        
        if keys:
            return {k: profile.preferences.get(k) for k in keys if k in profile.preferences}
        return profile.preferences
    
    async def get_user_context(self, user_id: str, context_type: str = "chat") -> List[Dict[str, Any]]:
        """Get user context/history for better responses"""
        profile = await self.get_user_profile(user_id)
        if not profile:
            return []
        
        # Filter history by context type
        relevant_history = [
            item for item in profile.history 
            if item.get("type") == context_type
        ]
        
        # Return last 10 items for context
        return relevant_history[-10:]
    
    async def query_user_data(self, user_id: str, query: str, server_name: str = None) -> Optional[Dict[str, Any]]:
        """Query specific user data with natural language"""
        servers_to_try = [server_name] if server_name else list(self.active_connections.keys())
        
        for srv_name in servers_to_try:
            if srv_name not in self.active_connections:
                continue
                
            try:
                result = await self._query_server(
                    srv_name, 
                    "query_user_data", 
                    {"user_id": user_id, "query": query}
                )
                if result:
                    return result
            except Exception as e:
                print(f"Error querying server {srv_name}: {e}")
        
        return None
    
    async def _query_server(self, server_name: str, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send query to MCP server"""
        if server_name not in self.active_connections:
            return None
        
        connection = self.active_connections[server_name]
        
        if connection["type"] == "http":
            # HTTP-based query
            client = connection["client"]
            try:
                response = await client.post(
                    f"{connection['url']}/mcp/call",
                    json={
                        "method": method,
                        "params": params
                    }
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                print(f"HTTP error querying {server_name}: {e}")
                return None
        
        elif connection["type"] == "process":
            # Process-based query (stdio)
            process = connection["process"]
            try:
                request = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": method,
                    "params": params
                }
                
                request_data = json.dumps(request) + "\n"
                process.stdin.write(request_data.encode())
                await process.stdin.drain()
                
                # Read response
                response_data = await process.stdout.readline()
                response = json.loads(response_data.decode().strip())
                
                if "result" in response:
                    return response["result"]
                elif "error" in response:
                    print(f"MCP server error: {response['error']}")
                    return None
                    
            except Exception as e:
                print(f"Error communicating with process-based MCP server: {e}")
                return None
        
        return None
    
    async def close(self):
        """Close all MCP connections"""
        for server_name, connection in self.active_connections.items():
            try:
                if connection["type"] == "http":
                    await connection["client"].aclose()
                elif connection["type"] == "process":
                    process = connection["process"]
                    process.terminate()
                    await process.wait()
            except Exception as e:
                print(f"Error closing connection to {server_name}: {e}")
        
        self.active_connections.clear()
    
    @classmethod
    def from_config(cls, config_path: str = None) -> 'MCPClient':
        """Create MCPClient from configuration file or environment"""
        servers = []
        
        # Try to load from config file
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                    for server_config in config_data.get("mcp_servers", []):
                        servers.append(MCPServerConfig(**server_config))
            except Exception as e:
                print(f"Error loading MCP config from {config_path}: {e}")
        
        # Load from environment variables
        mcp_servers_env = os.getenv("MCP_SERVERS")
        if mcp_servers_env:
            try:
                server_configs = json.loads(mcp_servers_env)
                for server_config in server_configs:
                    servers.append(MCPServerConfig(**server_config))
            except Exception as e:
                print(f"Error parsing MCP_SERVERS environment variable: {e}")
        
        return cls(servers)


# Global MCP client instance
_mcp_client: Optional[MCPClient] = None

async def get_mcp_client() -> MCPClient:
    """Get or create global MCP client instance"""
    global _mcp_client
    if _mcp_client is None:
        # Try to load from config file in the project root
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "mcp_config.json")
        _mcp_client = MCPClient.from_config(config_path)
        await _mcp_client.initialize()
    return _mcp_client

@asynccontextmanager
async def mcp_client_context():
    """Context manager for MCP client lifecycle"""
    client = await get_mcp_client()
    try:
        yield client
    finally:
        # Don't close here as it's a global instance
        pass
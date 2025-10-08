import asyncio
import json
import os
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager
from weakref import WeakKeyDictionary

import httpx
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class MCPServerConfig(BaseModel):
    name: str
    command: str
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    url: Optional[str] = None


class UserProfile(BaseModel):
    user_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    preferences: Dict[str, Any] = Field(default_factory=dict)
    history: List[Dict[str, Any]] = Field(default_factory=list)
    custom_data: Dict[str, Any] = Field(default_factory=dict)


class MCPClient:
    def __init__(self, servers: List[MCPServerConfig] = None):
        self.servers = servers or []
        self.active_connections = {}
        self._user_cache = {}
        
    async def initialize(self):
        for server in self.servers:
            try:
                await self._connect_to_server(server)
            except Exception as e:
                print(f"Failed to connect to MCP server {server.name}: {e}")
    
    async def _connect_to_server(self, server: MCPServerConfig):
        if server.url:
            self.active_connections[server.name] = {
                "type": "http",
                "url": server.url,
                "client": httpx.AsyncClient()
            }
        else:
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
        cache_key = f"{server_name}:{user_id}" if server_name else user_id
        if cache_key in self._user_cache:
            return self._user_cache[cache_key]
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
        profile = await self.get_user_profile(user_id)
        if not profile:
            return {}
        
        if keys:
            return {k: profile.preferences.get(k) for k in keys if k in profile.preferences}
        return profile.preferences
    
    async def get_user_context(self, user_id: str, context_type: str = "chat") -> List[Dict[str, Any]]:
        profile = await self.get_user_profile(user_id)
        if not profile:
            return []
        
        relevant_history = [
            item for item in profile.history 
            if item.get("type") == context_type
        ]
        
        return relevant_history[-10:]
    
    async def query_user_data(self, user_id: str, query: str, server_name: str = None) -> Optional[Dict[str, Any]]:
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
    
    DEFAULT_ORDER_SERVER = "user_order_server"

    async def get_pending_orders_count(self, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Lấy số lượng đơn hàng đang chờ giao"""
        try:
            params = {}
            if user_id:
                params["user_id"] = user_id
            
            result = await self._query_server("user_order_server", "get_pending_orders_count", params)
            return result
        except Exception as e:
            print(f"Error getting pending orders count: {e}")
            return None
    
    async def get_pending_payment_amount(self, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Lấy tổng số tiền phải thanh toán"""
        try:
            params = {}
            if user_id:
                params["user_id"] = user_id
            
            result = await self._query_server("user_order_server", "get_pending_payment_amount", params)
            return result
        except Exception as e:
            print(f"Error getting pending payment amount: {e}")
            return None
    
    async def get_delivery_estimates(self, user_id: str = None, days_ahead: int = 30) -> Optional[Dict[str, Any]]:
        """Lấy dự kiến ngày giao hàng"""
        try:
            params = {"days_ahead": days_ahead}
            if user_id:
                params["user_id"] = user_id
            
            result = await self._query_server("user_order_server", "get_delivery_estimates", params)
            return result
        except Exception as e:
            print(f"Error getting delivery estimates: {e}")
            return None
    
    async def get_order_summary(self, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Lấy tổng quan về đơn hàng"""
        try:
            params = {}
            if user_id:
                params["user_id"] = user_id
            
            result = await self._query_server("user_order_server", "get_order_summary", params)
            return result
        except Exception as e:
            print(f"Error getting order summary: {e}")
            return None
    
    async def get_recent_orders(self, user_id: str = None, limit: int = 10) -> Optional[Dict[str, Any]]:
        """Lấy danh sách đơn hàng gần đây"""
        try:
            params = {"limit": limit}
            if user_id:
                params["user_id"] = user_id
            
            result = await self._query_server("user_order_server", "get_recent_orders", params)
            return result
        except Exception as e:
            print(f"Error getting recent orders: {e}")
            return None

    async def get_completed_orders_summary(self, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Lấy thống kê đơn đã hoàn thành"""
        try:
            params = {}
            if user_id:
                params["user_id"] = user_id

            result = await self._query_server("user_order_server", "get_completed_orders_summary", params)
            return result
        except Exception as e:
            print(f"Error getting completed orders summary: {e}")
            return None

    async def get_latest_order(self, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Lấy thông tin đơn mới nhất"""
        try:
            params = {}
            if user_id:
                params["user_id"] = user_id

            result = await self._query_server("user_order_server", "get_latest_order", params)
            return result
        except Exception as e:
            print(f"Error getting latest order: {e}")
            return None

    async def get_next_delivery_order(self, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Lấy thông tin đơn sắp giao"""
        try:
            params = {}
            if user_id:
                params["user_id"] = user_id

            result = await self._query_server("user_order_server", "get_next_delivery_order", params)
            return result
        except Exception as e:
            print(f"Error getting next delivery order: {e}")
            return None

    async def get_highest_value_order(self, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Lấy đơn hàng giá trị cao nhất"""
        try:
            params = {}
            if user_id:
                params["user_id"] = user_id

            result = await self._query_server("user_order_server", "get_highest_value_order", params)
            return result
        except Exception as e:
            print(f"Error getting highest value order: {e}")
            return None

    async def get_lowest_value_order(self, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Lấy đơn hàng giá trị thấp nhất"""
        try:
            params = {}
            if user_id:
                params["user_id"] = user_id

            result = await self._query_server("user_order_server", "get_lowest_value_order", params)
            return result
        except Exception as e:
            print(f"Error getting lowest value order: {e}")
            return None

    async def get_average_order_value(self, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Lấy giá trị trung bình của đơn hàng"""
        try:
            params = {}
            if user_id:
                params["user_id"] = user_id

            result = await self._query_server("user_order_server", "get_average_order_value", params)
            return result
        except Exception as e:
            print(f"Error getting average order value: {e}")
            return None
    
    async def get_user_order_dashboard(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Lấy dashboard tổng hợp thông tin đơn hàng"""
        try:
            result = await self._query_server("user_order_server", "get_user_order_dashboard", {"user_id": user_id})
            return result
        except Exception as e:
            print(f"Error getting order dashboard: {e}")
            return None
    
    async def query_order_data(self, user_id: str, query: str) -> Optional[Dict[str, Any]]:
        """Trả lời câu hỏi về đơn hàng"""
        try:
            result = await self._query_server("user_order_server", "query_order_data", {"user_id": user_id, "query": query})
            return result
        except Exception as e:
            print(f"Error querying order data: {e}")
            return None
    
    async def _query_server(self, server_name: str, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if server_name not in self.active_connections:
            return None
        
        connection = self.active_connections[server_name]
        
        if connection["type"] == "http":
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
        servers = []
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                    for server_config in config_data.get("mcp_servers", []):
                        servers.append(MCPServerConfig(**server_config))
            except Exception as e:
                print(f"Error loading MCP config from {config_path}: {e}")
        
        mcp_servers_env = os.getenv("MCP_SERVERS")
        if mcp_servers_env:
            try:
                server_configs = json.loads(mcp_servers_env)
                for server_config in server_configs:
                    servers.append(MCPServerConfig(**server_config))
            except Exception as e:
                print(f"Error parsing MCP_SERVERS environment variable: {e}")
        
        return cls(servers)


_mcp_clients: "WeakKeyDictionary[asyncio.AbstractEventLoop, MCPClient]" = WeakKeyDictionary()
_mcp_client_locks: "WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Lock]" = WeakKeyDictionary()


def _get_client_lock(loop: asyncio.AbstractEventLoop) -> asyncio.Lock:
    lock = _mcp_client_locks.get(loop)
    if lock is None:
        lock = asyncio.Lock()
        _mcp_client_locks[loop] = lock
    return lock

async def get_mcp_client() -> MCPClient:
    loop = asyncio.get_running_loop()

    client = _mcp_clients.get(loop)
    if client is not None:
        return client

    lock = _get_client_lock(loop)
    async with lock:
        client = _mcp_clients.get(loop)
        if client is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "mcp_config.json",
            )
            client = MCPClient.from_config(config_path)
            await client.initialize()
            _mcp_clients[loop] = client
    return client


async def close_mcp_client() -> None:
    loop = asyncio.get_running_loop()
    client = _mcp_clients.pop(loop, None)
    if client is not None:
        await client.close()
    _mcp_client_locks.pop(loop, None)

@asynccontextmanager
async def mcp_client_context():
    client = await get_mcp_client()
    try:
        yield client
    finally:
        pass
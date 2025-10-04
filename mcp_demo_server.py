#!/usr/bin/env python3
"""
Demo MCP server for user profile management
This server provides user profile information to the RAG chatbot
"""

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional


class DemoUserProfileServer:
    """Demo MCP server that provides user profile information"""
    
    def __init__(self):
        # Demo user data - in a real implementation, this would connect to a database
        self.demo_users = {
            "admin": {
                "user_id": "admin",
                "name": "Admin User",
                "email": "admin@example.com",
                "preferences": {
                    "communication_style": "professional",
                    "response_length": "detailed", 
                    "language": "vietnamese",
                    "contact_preference": "email",
                    "interests": ["order tracking", "subscription management"]
                },
                "history": [
                    {
                        "type": "chat",
                        "timestamp": "2024-10-01T10:00:00Z",
                        "user_message": "Tôi cần kiểm tra trạng thái đơn hàng #OR12345.",
                        "bot_response": "Đơn hàng #OR12345 đang ở trạng thái 'Đang vận chuyển' và dự kiến giao ngày 05/10.",
                        "topic": "order_tracking"
                    }
                ],
                "custom_data": {
                    "last_orders": [
                        {
                            "order_id": "OR12345",
                            "status": "shipping",
                            "expected_delivery": "2024-10-05"
                        }
                    ]
                }
            },
            "user123": {
                "user_id": "user123", 
                "name": "John Doe",
                "email": "john@example.com",
                "preferences": {
                    "communication_style": "casual",
                    "response_length": "concise",
                    "language": "english", 
                    "interests": ["billing", "device setup"]
                },
                "history": [],
                "custom_data": {}
            }
        }
    
    async def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle incoming MCP requests"""
        method = request.get("method")
        params = request.get("params", {})
        
        if method == "get_user_profile":
            return await self.get_user_profile(params.get("user_id"))
        elif method == "query_user_data":
            return await self.query_user_data(params.get("user_id"), params.get("query"))
        else:
            return {"error": f"Unknown method: {method}"}
    
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get complete user profile"""
        user_data = self.demo_users.get(user_id)
        if user_data:
            return user_data
        else:
            return {"error": f"User {user_id} not found"}
    
    async def query_user_data(self, user_id: str, query: str) -> Dict[str, Any]:
        """Query specific user data with natural language"""
        user_data = self.demo_users.get(user_id)
        if not user_data:
            return {"error": f"User {user_id} not found"}
        
        query_lower = query.lower()
        
        # Simple query matching - in a real implementation, this would be more sophisticated
        if "preference" in query_lower or "style" in query_lower:
            return {"result": user_data.get("preferences", {})}
        elif "history" in query_lower or "previous" in query_lower:
            return {"result": user_data.get("history", [])}
        elif "order" in query_lower:
            return {"result": user_data.get("custom_data", {}).get("last_orders", [])}
        elif "name" in query_lower:
            return {"result": {"name": user_data.get("name", "")}}
        elif "email" in query_lower:
            return {"result": {"email": user_data.get("email", "")}}
        else:
            # Return summary for general queries
            return {
                "result": {
                    "summary": f"User {user_data.get('name', user_id)} with preferences for {user_data.get('preferences', {}).get('communication_style', 'standard')} communication",
                    "available_data": list(user_data.keys())
                }
            }


async def main():
    """Main MCP server loop"""
    server = DemoUserProfileServer()
    
    print("Demo MCP User Profile Server started", file=sys.stderr)
    
    try:
        while True:
            # Read JSON-RPC request from stdin
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            
            try:
                request = json.loads(line.strip())
                response_data = await server.handle_request(request)
                
                # Format JSON-RPC response
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id", 1),
                    "result": response_data
                }
                
                # Send response to stdout
                print(json.dumps(response), flush=True)
                
            except json.JSONDecodeError as e:
                # Send error response
                error_response = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "error": {"code": -32700, "message": "Parse error", "data": str(e)}
                }
                print(json.dumps(error_response), flush=True)
            except Exception as e:
                # Send internal error response
                error_response = {
                    "jsonrpc": "2.0", 
                    "id": request.get("id", 1) if 'request' in locals() else 1,
                    "error": {"code": -32603, "message": "Internal error", "data": str(e)}
                }
                print(json.dumps(error_response), flush=True)
                
    except KeyboardInterrupt:
        print("Server shutting down...", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
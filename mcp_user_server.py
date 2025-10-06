import asyncio
import json
import sys
import os
from typing import Any, Dict, Optional

# Add src to path to import our modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from lib.order_services import BalanceService
from lib.db_services import UserService


class UserProfileAndBalanceServer:
    """MCP Server for user profile and balance operations"""
    
    def __init__(self):
        # Initialize database connections
        pass
    
    async def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle incoming MCP requests"""
        method = request.get("method")
        params = request.get("params", {})
        
        try:
            # User Profile Methods
            if method == "get_user_profile":
                return await self.get_user_profile(params.get("user_id"))
            elif method == "query_user_data":
                return await self.query_user_data(params.get("user_id"), params.get("query"))
            elif method == "get_user_by_email":
                return await self.get_user_by_email(params.get("email"))
            elif method == "get_user_by_username":
                return await self.get_user_by_username(params.get("username"))
            
            # Balance Methods
            elif method == "get_user_balance":
                return await self.get_user_balance(params.get("user_id"))
            elif method == "get_user_points":
                return await self.get_user_points(params.get("user_id"))
            elif method == "get_balance_info":
                return await self.get_balance_info(params.get("user_id"))
            elif method == "get_top_balances":
                limit = params.get("limit", 10)
                return await self.get_top_balances(limit)
            elif method == "get_balance_stats":
                return await self.get_balance_statistics()
            elif method == "search_user_balances":
                user_ids = params.get("user_ids", [])
                return await self.search_user_balances(user_ids)
            else:
                return {"error": f"Unknown method: {method}"}
        except Exception as e:
            return {"error": f"Error processing {method}: {str(e)}"}
    
    async def get_user_balance(self, user_id: str) -> Dict[str, Any]:
        """Get user balance (điểm 02)"""
        if not user_id:
            return {"error": "user_id is required"}
        
        try:
            balance_data = BalanceService.get_user_balance(user_id)
            if balance_data:
                return {
                    "user_id": str(balance_data.userId),
                    "balance": balance_data.balance,
                    "balance_formatted": balance_data.balance_formatted,
                    "last_updated": balance_data.updatedAt.isoformat(),
                    "created_at": balance_data.createdAt.isoformat()
                }
            else:
                return {"error": f"Balance not found for user {user_id}"}
        except Exception as e:
            return {"error": f"Failed to get balance: {str(e)}"}
    
    async def get_user_points(self, user_id: str) -> Dict[str, Any]:
        """Get user points"""
        if not user_id:
            return {"error": "user_id is required"}
        
        try:
            balance_data = BalanceService.get_user_balance(user_id)
            if balance_data:
                return {
                    "user_id": str(balance_data.userId),
                    "points": balance_data.point,
                    "points_formatted": balance_data.point_formatted,
                    "last_updated": balance_data.updatedAt.isoformat()
                }
            else:
                return {"error": f"Points not found for user {user_id}"}
        except Exception as e:
            return {"error": f"Failed to get points: {str(e)}"}
    
    async def get_balance_info(self, user_id: str) -> Dict[str, Any]:
        """Get complete balance information (balance + points)"""
        if not user_id:
            return {"error": "user_id is required"}
        
        try:
            balance_data = BalanceService.get_user_balance(user_id)
            if balance_data:
                return {
                    "user_id": str(balance_data.userId),
                    "balance": {
                        "amount": balance_data.balance,
                        "formatted": balance_data.balance_formatted
                    },
                    "points": {
                        "amount": balance_data.point,
                        "formatted": balance_data.point_formatted
                    },
                    "timestamps": {
                        "created_at": balance_data.createdAt.isoformat(),
                        "last_updated": balance_data.updatedAt.isoformat()
                    }
                }
            else:
                return {"error": f"Balance information not found for user {user_id}"}
        except Exception as e:
            return {"error": f"Failed to get balance info: {str(e)}"}
    
    async def get_top_balances(self, limit: int = 10) -> Dict[str, Any]:
        """Get top users by balance"""
        try:
            top_balances = BalanceService.get_top_balances(limit)
            
            result = []
            for balance in top_balances:
                result.append({
                    "user_id": str(balance.userId),
                    "balance": balance.balance,
                    "balance_formatted": balance.balance_formatted,
                    "points": balance.point,
                    "points_formatted": balance.point_formatted,
                    "last_updated": balance.updatedAt.isoformat()
                })
            
            return {
                "top_balances": result,
                "count": len(result),
                "limit": limit
            }
        except Exception as e:
            return {"error": f"Failed to get top balances: {str(e)}"}
    
    async def get_balance_statistics(self) -> Dict[str, Any]:
        """Get balance statistics"""
        try:
            stats = BalanceService.get_balance_statistics()
            return {"statistics": stats}
        except Exception as e:
            return {"error": f"Failed to get statistics: {str(e)}"}
    
    async def search_user_balances(self, user_ids: list) -> Dict[str, Any]:
        """Search balances for multiple users"""
        if not user_ids:
            return {"error": "user_ids list is required"}
        
        try:
            balances = BalanceService.search_balances_by_user_ids(user_ids)
            
            result = []
            for balance in balances:
                result.append({
                    "user_id": str(balance.userId),
                    "balance": balance.balance,
                    "balance_formatted": balance.balance_formatted,
                    "points": balance.point,
                    "points_formatted": balance.point_formatted,
                    "last_updated": balance.updatedAt.isoformat()
                })
            
            return {
                "balances": result,
                "count": len(result),
                "searched_count": len(user_ids)
            }
        except Exception as e:
            return {"error": f"Failed to search balances: {str(e)}"}
    
    # User Profile Methods
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile information by UUID or email"""
        if not user_id:
            return {"error": "user_id is required"}
        
        try:
            user_profile = None
            
            # Try to get by UUID first
            try:
                user_profile = UserService.get_user_profile(user_id)
            except:
                # If not UUID, try to find by email
                user = UserService.get_user_by_email(user_id)
                if user:
                    user_profile = UserService.get_user_profile(str(user.id))
            
            if user_profile:
                return {
                    "user_id": str(user_profile.id),
                    "name": user_profile.full_name,
                    "email": user_profile.email,
                    "username": user_profile.username,
                    "full_name": user_profile.full_name,
                    "nickname": user_profile.nickname,
                    "role": user_profile.role,
                    "firstName": user_profile.firstName,
                    "lastName": user_profile.lastName,
                    "phone": user_profile.phone,
                    "language": user_profile.language,
                    "isActive": user_profile.isActive,
                    "verified": user_profile.verified,
                    "storeId": str(user_profile.storeId) if user_profile.storeId else None,
                    "level": user_profile.level,
                    "created_at": user_profile.createdAt.isoformat() if user_profile.createdAt else None,
                    "updated_at": user_profile.updatedAt.isoformat() if user_profile.updatedAt else None,
                    "preferences": {
                        "communication_style": "professional",
                        "language": user_profile.language or "vi",
                        "response_length": "detailed"
                    },
                    "history": [],
                    "custom_data": {}
                }
            elif user_id == "anonymous":
                # Return default anonymous user profile
                return {
                    "user_id": "anonymous",
                    "name": "Khách hàng",
                    "email": None,
                    "username": "anonymous",
                    "full_name": "Khách hàng",
                    "nickname": None,
                    "role": "guest",
                    "firstName": "Khách",
                    "lastName": "hàng",
                    "phone": None,
                    "language": "vi",
                    "isActive": True,
                    "verified": False,
                    "storeId": None,
                    "level": None,
                    "created_at": None,
                    "updated_at": None,
                    "preferences": {
                        "communication_style": "friendly",
                        "language": "vi",
                        "response_length": "concise"
                    },
                    "history": [],
                    "custom_data": {}
                }
            else:
                return {"error": f"User profile not found for user {user_id}"}
        except Exception as e:
            return {"error": f"Failed to get user profile: {str(e)}"}
    
    async def get_user_by_email(self, email: str) -> Dict[str, Any]:
        """Get user by email"""
        if not email:
            return {"error": "email is required"}
        
        try:
            user = UserService.get_user_by_email(email)
            if user:
                return {
                    "user_id": str(user.id),
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "nickname": user.nickname,
                    "role": user.role,
                    "isActive": user.isActive,
                    "verified": user.verified
                }
            else:
                return {"error": f"User not found with email {email}"}
        except Exception as e:
            return {"error": f"Failed to get user by email: {str(e)}"}
    
    async def get_user_by_username(self, username: str) -> Dict[str, Any]:
        """Get user by username"""
        if not username:
            return {"error": "username is required"}
        
        try:
            user = UserService.get_user_by_username(username)
            if user:
                return {
                    "user_id": str(user.id),
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "nickname": user.nickname,
                    "role": user.role,
                    "isActive": user.isActive,
                    "verified": user.verified
                }
            else:
                return {"error": f"User not found with username {username}"}
        except Exception as e:
            return {"error": f"Failed to get user by username: {str(e)}"}
    
    async def query_user_data(self, user_id: str, query: str) -> Dict[str, Any]:
        """Query user data based on query string"""
        if not user_id:
            return {"error": "user_id is required"}
        if not query:
            return {"error": "query is required"}
        
        try:
            query_lower = query.lower()
            user_profile = None
            
            # Try to get by UUID first, then by email
            try:
                user_profile = UserService.get_user_profile(user_id)
            except:
                user = UserService.get_user_by_email(user_id)
                if user:
                    user_profile = UserService.get_user_profile(str(user.id))
            
            if not user_profile and user_id == "anonymous":
                # Handle anonymous user queries
                if "name" in query_lower:
                    return {
                        "result": {
                            "full_name": "Khách hàng",
                            "firstName": "Khách",
                            "lastName": "hàng",
                            "nickname": None
                        }
                    }
                elif "who" in query_lower or "ai" in query_lower:
                    return {
                        "result": {
                            "summary": "Bạn là khách hàng đang sử dụng dịch vụ hỗ trợ của Oreka",
                            "basic_info": {
                                "role": "guest",
                                "status": "anonymous user"
                            }
                        }
                    }
                else:
                    return {
                        "result": {
                            "summary": "Khách hàng ẩn danh",
                            "role": "guest"
                        }
                    }
            elif not user_profile:
                return {"error": f"User {user_id} not found"}
            
            if "name" in query_lower:
                return {
                    "result": {
                        "full_name": user_profile.full_name,
                        "firstName": user_profile.firstName,
                        "lastName": user_profile.lastName,
                        "nickname": user_profile.nickname
                    }
                }
            elif "contact" in query_lower or "email" in query_lower or "phone" in query_lower:
                return {
                    "result": {
                        "email": user_profile.email,
                        "phone": user_profile.phone
                    }
                }
            elif "role" in query_lower or "permission" in query_lower:
                return {
                    "result": {
                        "role": user_profile.role,
                        "level": user_profile.level,
                        "isActive": user_profile.isActive,
                        "verified": user_profile.verified
                    }
                }
            elif "store" in query_lower:
                return {
                    "result": {
                        "storeId": str(user_profile.storeId) if user_profile.storeId else None
                    }
                }
            elif "balance" in query_lower or "điểm" in query_lower or "point" in query_lower:
                # Get balance information
                try:
                    balance_data = BalanceService.get_user_balance(str(user_profile.id))
                    if balance_data:
                        return {
                            "result": {
                                "balance": {
                                    "amount": balance_data.balance,
                                    "formatted": balance_data.balance_formatted,
                                    "points": balance_data.point,
                                    "points_formatted": balance_data.point_formatted,
                                    "last_updated": balance_data.updatedAt.isoformat()
                                },
                                "summary": f"Điểm 02 của bạn: {balance_data.balance_formatted}, Points: {balance_data.point_formatted}"
                            }
                        }
                    else:
                        return {
                            "result": {
                                "balance": None,
                                "summary": "Không tìm thấy thông tin điểm 02 cho tài khoản này"
                            }
                        }
                except Exception as e:
                    return {
                        "result": {
                            "balance": None,
                            "summary": f"Lỗi khi lấy thông tin điểm 02: {str(e)}"
                        }
                    }
            else:
                # Return summary for general queries
                return {
                    "result": {
                        "summary": f"User {user_profile.full_name or user_profile.username} ({user_profile.role})",
                        "basic_info": {
                            "username": user_profile.username,
                            "email": user_profile.email,
                            "full_name": user_profile.full_name,
                            "role": user_profile.role,
                            "isActive": user_profile.isActive
                        }
                    }
                }
        except Exception as e:
            return {"error": f"Failed to query user data: {str(e)}"}


async def main():
    """Main MCP server loop"""
    server = UserProfileAndBalanceServer()
    
    # MCP server is running
    
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
        pass


if __name__ == "__main__":
    asyncio.run(main())
import asyncio
import json
import sys
import os
from typing import Any, Dict, Optional

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from lib.order_management_service import OrderManagementService


class OrderManagementServer:
    """MCP Server for order management operations"""
    def __init__(self):
        pass
    
    async def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle incoming MCP requests"""
        method = request.get("method")
        params = request.get("params", {})
        
        try:
            # Order Statistics Methods
            if method == "get_pending_orders_count":
                return await self.get_pending_orders_count(params.get("user_id"))
            elif method == "get_pending_payment_amount":
                return await self.get_pending_payment_amount(params.get("user_id"))
            elif method == "get_delivery_estimates":
                return await self.get_delivery_estimates(
                    params.get("user_id"), 
                    params.get("days_ahead", 30)
                )
            elif method == "get_order_summary":
                return await self.get_order_summary(params.get("user_id"))
            elif method == "get_recent_orders":
                return await self.get_recent_orders(
                    params.get("user_id"), 
                    params.get("limit", 10)
                )
            elif method == "get_completed_orders_summary":
                return await self.get_completed_orders_summary(params.get("user_id"))
            elif method == "get_latest_order":
                return await self.get_latest_order(params.get("user_id"))
            elif method == "get_next_delivery_order":
                return await self.get_next_delivery_order(params.get("user_id"))
            elif method == "get_highest_value_order":
                return await self.get_highest_value_order(params.get("user_id"))
            elif method == "get_lowest_value_order":
                return await self.get_lowest_value_order(params.get("user_id"))
            elif method == "get_average_order_value":
                return await self.get_average_order_value(params.get("user_id"))
            
            # Combined Methods
            elif method == "get_user_order_dashboard":
                return await self.get_user_order_dashboard(params.get("user_id"))
            elif method == "query_order_data":
                return await self.query_order_data(
                    params.get("user_id"),
                    params.get("query")
                )
            else:
                return {"error": f"Unknown method: {method}"}
        except Exception as e:
            return {"error": f"Error processing {method}: {str(e)}"}
    
    async def get_pending_orders_count(self, user_id: str) -> Dict[str, Any]:
        """Lấy số lượng đơn hàng đang chờ giao"""
        try:
            result = OrderManagementService.get_pending_orders_count(user_id)
            return result
        except Exception as e:
            return {"error": f"Failed to get pending orders count: {str(e)}"}
    
    async def get_pending_payment_amount(self, user_id: str) -> Dict[str, Any]:
        """Lấy tổng số tiền phải thanh toán"""
        try:
            result = OrderManagementService.get_pending_payment_amount(user_id)
            return result
        except Exception as e:
            return {"error": f"Failed to get pending payment amount: {str(e)}"}
    
    async def get_delivery_estimates(self, user_id: str, days_ahead: int = 30) -> Dict[str, Any]:
        """Lấy dự kiến ngày giao hàng"""
        try:
            result = OrderManagementService.get_delivery_estimates(user_id, days_ahead)
            return result
        except Exception as e:
            return {"error": f"Failed to get delivery estimates: {str(e)}"}
    
    async def get_order_summary(self, user_id: str) -> Dict[str, Any]:
        """Lấy tổng quan về đơn hàng"""
        try:
            result = OrderManagementService.get_order_summary(user_id)
            return result
        except Exception as e:
            return {"error": f"Failed to get order summary: {str(e)}"}
    
    async def get_recent_orders(self, user_id: str, limit: int = 10) -> Dict[str, Any]:
        """Lấy danh sách đơn hàng gần đây"""
        try:
            result = OrderManagementService.get_recent_orders(user_id, limit)
            return result
        except Exception as e:
            return {"error": f"Failed to get recent orders: {str(e)}"}

    async def get_completed_orders_summary(self, user_id: str) -> Dict[str, Any]:
        try:
            result = OrderManagementService.get_completed_orders_summary(user_id)
            return result
        except Exception as e:
            return {"error": f"Failed to get completed orders summary: {str(e)}"}

    async def get_latest_order(self, user_id: str) -> Dict[str, Any]:
        try:
            result = OrderManagementService.get_latest_order(user_id)
            return result
        except Exception as e:
            return {"error": f"Failed to get latest order: {str(e)}"}

    async def get_next_delivery_order(self, user_id: str) -> Dict[str, Any]:
        try:
            result = OrderManagementService.get_next_delivery_order(user_id)
            return result
        except Exception as e:
            return {"error": f"Failed to get next delivery order: {str(e)}"}

    async def get_highest_value_order(self, user_id: str) -> Dict[str, Any]:
        try:
            result = OrderManagementService.get_highest_value_order(user_id)
            return result
        except Exception as e:
            return {"error": f"Failed to get highest value order: {str(e)}"}

    async def get_lowest_value_order(self, user_id: str) -> Dict[str, Any]:
        try:
            result = OrderManagementService.get_lowest_value_order(user_id)
            return result
        except Exception as e:
            return {"error": f"Failed to get lowest value order: {str(e)}"}

    async def get_average_order_value(self, user_id: str) -> Dict[str, Any]:
        try:
            result = OrderManagementService.get_average_order_value(user_id)
            return result
        except Exception as e:
            return {"error": f"Failed to get average order value: {str(e)}"}
    
    async def get_user_order_dashboard(self, user_id: str) -> Dict[str, Any]:
        """Lấy tổng hợp thông tin đơn hàng cho dashboard của user"""
        if not user_id:
            return {"error": "user_id is required"}
        
        try:
            # Lấy tất cả thông tin cần thiết
            pending_count = OrderManagementService.get_pending_orders_count(user_id)
            pending_payment = OrderManagementService.get_pending_payment_amount(user_id)
            delivery_estimates = OrderManagementService.get_delivery_estimates(user_id, 7)  # 7 ngày tới
            order_summary = OrderManagementService.get_order_summary(user_id)
            recent_orders = OrderManagementService.get_recent_orders(user_id, 5)
            
            return {
                "dashboard": {
                    "user_id": user_id,
                    "pending_orders": {
                        "count": pending_count.get("pending_orders_count", 0),
                        "items": pending_count.get("pending_items_count", 0)
                    },
                    "financial": {
                        "total_pending_amount": pending_payment.get("total_pending_amount", 0),
                        "unpaid_amount": pending_payment.get("unpaid_amount", 0),
                        "unpaid_orders": pending_payment.get("unpaid_orders", 0)
                    },
                    "deliveries": {
                        "upcoming_7_days": delivery_estimates.get("upcoming_deliveries", 0),
                        "total_shipped": delivery_estimates.get("total_shipped_pending", 0),
                        "estimates": delivery_estimates.get("delivery_estimates", [])[:3]  # Top 3
                    },
                    "summary": order_summary.get("summary", {}),
                    "recent_orders": recent_orders.get("recent_orders", [])[:5]
                },
                "generated_at": pending_count.get("query_time")
            }
        except Exception as e:
            return {"error": f"Failed to get order dashboard: {str(e)}"}
    
    async def query_order_data(self, user_id: str, query: str) -> Dict[str, Any]:
        """Trả lời câu hỏi về đơn hàng dựa trên query"""
        if not user_id:
            return {"error": "user_id is required"}
        if not query:
            return {"error": "query is required"}
        
        try:
            query_lower = query.lower()
            
            # Phân tích query và trả về thông tin phù hợp
            if any(word in query_lower for word in ['chờ giao', 'pending', 'đang chờ', 'chưa giao']):
                result = OrderManagementService.get_pending_orders_count(user_id)
                return {
                    "answer": f"Bạn hiện có {result.get('pending_orders_count', 0)} đơn hàng đang chờ giao với tổng {result.get('pending_items_count', 0)} sản phẩm.",
                    "data": result
                }
            
            elif any(word in query_lower for word in ['tiền', 'thanh toán', 'phải trả', 'payment', 'money']):
                result = OrderManagementService.get_pending_payment_amount(user_id)
                unpaid = result.get('unpaid_amount', 0)
                total_pending = result.get('total_pending_amount', 0)
                return {
                    "answer": f"Bạn cần thanh toán {unpaid:,} VND từ {result.get('unpaid_orders', 0)} đơn hàng chưa thanh toán. Tổng giá trị các đơn hàng đang xử lý là {total_pending:,} VND.",
                    "data": result
                }
            
            elif any(word in query_lower for word in ['giao hàng', 'delivery', 'dự kiến', 'khi nào đến']):
                result = OrderManagementService.get_delivery_estimates(user_id, 7)
                upcoming = result.get('upcoming_deliveries', 0)
                estimates = result.get('delivery_estimates', [])
                answer = f"Bạn có {upcoming} đơn hàng dự kiến giao trong 7 ngày tới."
                if estimates:
                    next_delivery = estimates[0]
                    answer += f" Đơn hàng gần nhất ({next_delivery['order_id']}) dự kiến giao từ {next_delivery['estimated_delivery_min'][:10]} đến {next_delivery['estimated_delivery_max'][:10]}."
                return {
                    "answer": answer,
                    "data": result
                }
            
            elif any(word in query_lower for word in ['tổng quan', 'summary', 'thống kê', 'overview']):
                result = OrderManagementService.get_order_summary(user_id)
                summary = result.get('summary', {})
                return {
                    "answer": f"Tổng quan đơn hàng: {summary.get('total_orders', 0)} đơn hàng, {summary.get('total_items', 0)} sản phẩm, tổng giá trị {summary.get('total_value', 0):,} VND. Trong đó: {summary.get('delivered_items', 0)} đã giao, {summary.get('shipping_items', 0)} đang giao, {summary.get('pending_items', 0)} chờ xử lý.",
                    "data": result
                }
            
            elif any(word in query_lower for word in ['gần đây', 'recent', 'mới nhất', 'latest']):
                result = OrderManagementService.get_recent_orders(user_id, 5)
                orders = result.get('recent_orders', [])
                answer = f"Bạn có {len(orders)} đơn hàng gần đây."
                if orders:
                    answer += f" Đơn mới nhất: {orders[0]['order_id']} ({orders[0]['status']}) - {orders[0]['total_value']:,} VND."
                return {
                    "answer": answer,
                    "data": result
                }
            
            else:
                # Trả về dashboard tổng hợp
                result = await self.get_user_order_dashboard(user_id)
                dashboard = result.get('dashboard', {})
                return {
                    "answer": f"Thông tin đơn hàng của bạn: {dashboard.get('pending_orders', {}).get('count', 0)} đơn chờ giao, cần thanh toán {dashboard.get('financial', {}).get('unpaid_amount', 0):,} VND, {dashboard.get('deliveries', {}).get('upcoming_7_days', 0)} đơn sẽ giao trong 7 ngày tới.",
                    "data": result
                }
        except Exception as e:
            return {"error": f"Failed to query order data: {str(e)}"}


async def main():
    """Main MCP server loop"""
    server = OrderManagementServer()
    
    print("Order Management MCP Server started", file=sys.stderr)
    print("Available methods:", file=sys.stderr)
    print("  Order Statistics:", file=sys.stderr)
    print("    - get_pending_orders_count(user_id): Số đơn hàng chờ giao", file=sys.stderr)
    print("    - get_pending_payment_amount(user_id): Số tiền phải thanh toán", file=sys.stderr)
    print("    - get_delivery_estimates(user_id, days_ahead): Dự kiến giao hàng", file=sys.stderr)
    print("    - get_order_summary(user_id): Tổng quan đơn hàng", file=sys.stderr)
    print("    - get_recent_orders(user_id, limit): Đơn hàng gần đây", file=sys.stderr)
    print("    - get_completed_orders_summary(user_id): Thống kê đơn hoàn thành", file=sys.stderr)
    print("    - get_latest_order(user_id): Đơn mới đặt gần nhất", file=sys.stderr)
    print("    - get_next_delivery_order(user_id): Đơn sắp giao nhất", file=sys.stderr)
    print("    - get_highest_value_order(user_id): Đơn giá trị cao nhất", file=sys.stderr)
    print("    - get_lowest_value_order(user_id): Đơn giá trị thấp nhất", file=sys.stderr)
    print("    - get_average_order_value(user_id): Giá trị đơn trung bình", file=sys.stderr)
    print("  Combined Methods:", file=sys.stderr)
    print("    - get_user_order_dashboard(user_id): Dashboard tổng hợp", file=sys.stderr)
    print("    - query_order_data(user_id, query): Trả lời câu hỏi về đơn hàng", file=sys.stderr)
    
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
        print("Order Management Server shutting down...", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
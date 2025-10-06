from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import text
from .database import get_order_session_context

class OrderManagementService:
    """Service để quản lý thông tin đơn hàng từ database ORDER"""
    
    @staticmethod
    def get_pending_orders_count(user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Lấy số lượng đơn hàng đang chờ giao
        
        Args:
            user_id: ID của user (optional). Nếu không có thì lấy tất cả
        
        Returns:
            Dict chứa thông tin số đơn hàng chờ giao
        """
        try:
            with get_order_session_context() as session:
                # Query đơn hàng đang chờ giao (chưa delivered, chưa cancelled, chưa completed)
                base_query = """
                    SELECT COUNT(DISTINCT oi.id) as pending_count,
                           COUNT(DISTINCT o.id) as pending_orders
                    FROM v2_orders o
                    JOIN v2_order_items oi ON o.id = oi."orderId"
                    WHERE oi."deliveredAt" IS NULL 
                      AND oi."cancelledAt" IS NULL
                      AND oi."completedAt" IS NULL
                """
                
                if user_id:
                    base_query += f' AND o."userId" = \'{user_id}\''
                
                result = session.exec(text(base_query))
                data = result.fetchone()
                
                return {
                    "pending_items_count": data[0] if data else 0,
                    "pending_orders_count": data[1] if data else 0,
                    "user_id": user_id,
                    "query_time": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {"error": f"Lỗi khi lấy số đơn hàng chờ giao: {str(e)}"}
    
    @staticmethod
    def get_pending_payment_amount(user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Lấy tổng số tiền phải thanh toán từ các đơn hàng chưa hoàn thành
        
        Args:
            user_id: ID của user (optional)
        
        Returns:
            Dict chứa thông tin tổng tiền phải thanh toán
        """
        try:
            with get_order_session_context() as session:
                # Query tổng tiền của các đơn hàng chưa thanh toán hoặc chưa hoàn thành
                base_query = """
                    SELECT 
                        SUM(oi."itemPrice" * oi.quantity) as total_amount,
                        COUNT(DISTINCT oi.id) as total_items,
                        COUNT(DISTINCT o.id) as total_orders,
                        SUM(CASE WHEN o.deposited = false THEN oi."itemPrice" * oi.quantity ELSE 0 END) as unpaid_amount,
                        COUNT(DISTINCT CASE WHEN o.deposited = false THEN o.id END) as unpaid_orders
                    FROM v2_orders o
                    JOIN v2_order_items oi ON o.id = oi."orderId"
                    WHERE (oi."deliveredAt" IS NULL OR oi."completedAt" IS NULL)
                      AND oi."cancelledAt" IS NULL
                """
                
                if user_id:
                    base_query += f' AND o."userId" = \'{user_id}\''
                
                result = session.exec(text(base_query))
                data = result.fetchone()
                
                return {
                    "total_pending_amount": data[0] if data[0] else 0,
                    "total_pending_items": data[1] if data else 0,
                    "total_pending_orders": data[2] if data else 0,
                    "unpaid_amount": data[3] if data[3] else 0,
                    "unpaid_orders": data[4] if data else 0,
                    "user_id": user_id,
                    "query_time": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {"error": f"Lỗi khi lấy tổng tiền phải thanh toán: {str(e)}"}
    
    @staticmethod
    def get_delivery_estimates(user_id: Optional[str] = None, days_ahead: int = 30) -> Dict[str, Any]:
        """
        Lấy dự kiến ngày giao hàng của các đơn hàng
        
        Args:
            user_id: ID của user (optional)
            days_ahead: Số ngày tới để dự kiến (default 30 ngày)
        
        Returns:
            Dict chứa thông tin dự kiến giao hàng
        """
        try:
            with get_order_session_context() as session:
                # Query các đơn hàng đã shipped nhưng chưa delivered
                base_query = """
                    SELECT 
                        o."shortId",
                        o.name,
                        o.address,
                        oi."shippedAt",
                        oi."itemPrice" * oi.quantity as total_value,
                        oi.quantity,
                        o.phone
                    FROM v2_orders o
                    JOIN v2_order_items oi ON o.id = oi."orderId"
                    WHERE oi."shippedAt" IS NOT NULL 
                      AND oi."deliveredAt" IS NULL
                      AND oi."cancelledAt" IS NULL
                """
                
                if user_id:
                    base_query += f' AND o."userId" = \'{user_id}\''
                
                base_query += ' ORDER BY oi."shippedAt" DESC'
                
                result = session.exec(text(base_query))
                shipped_orders = result.fetchall()
                
                # Tính toán dự kiến giao hàng (giả sử 3-5 ngày từ khi ship)
                delivery_estimates = []
                for order in shipped_orders:
                    shipped_date = order[3]
                    if shipped_date:
                        # Dự kiến giao hàng 3-5 ngày sau khi ship
                        estimated_delivery_min = shipped_date + timedelta(days=3)
                        estimated_delivery_max = shipped_date + timedelta(days=5)
                        
                        delivery_estimates.append({
                            "order_id": order[0],
                            "customer_name": order[1],
                            "address": order[2],
                            "shipped_at": shipped_date.isoformat(),
                            "estimated_delivery_min": estimated_delivery_min.isoformat(),
                            "estimated_delivery_max": estimated_delivery_max.isoformat(),
                            "total_value": order[4],
                            "quantity": order[5],
                            "phone": order[6]
                        })
                
                # Thống kê
                total_shipped = len(delivery_estimates)
                upcoming_deliveries = len([est for est in delivery_estimates 
                                         if datetime.fromisoformat(est['estimated_delivery_max'].replace('T', ' ')) 
                                         <= datetime.now() + timedelta(days=days_ahead)])
                
                return {
                    "delivery_estimates": delivery_estimates,
                    "total_shipped_pending": total_shipped,
                    "upcoming_deliveries": upcoming_deliveries,
                    "user_id": user_id,
                    "query_time": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {"error": f"Lỗi khi lấy dự kiến giao hàng: {str(e)}"}
    
    @staticmethod
    def get_order_summary(user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Lấy tổng quan về đơn hàng của user
        
        Args:
            user_id: ID của user (optional)
        
        Returns:
            Dict chứa tổng quan đơn hàng
        """
        try:
            with get_order_session_context() as session:
                base_query = """
                    SELECT 
                        COUNT(DISTINCT o.id) as total_orders,
                        COUNT(DISTINCT oi.id) as total_items,
                        SUM(oi."itemPrice" * oi.quantity) as total_value,
                        COUNT(DISTINCT CASE WHEN oi."deliveredAt" IS NOT NULL THEN oi.id END) as delivered_items,
                        COUNT(DISTINCT CASE WHEN oi."cancelledAt" IS NOT NULL THEN oi.id END) as cancelled_items,
                        COUNT(DISTINCT CASE WHEN oi."shippedAt" IS NOT NULL AND oi."deliveredAt" IS NULL THEN oi.id END) as shipping_items,
                        COUNT(DISTINCT CASE WHEN oi."deliveredAt" IS NULL AND oi."cancelledAt" IS NULL AND oi."shippedAt" IS NULL THEN oi.id END) as pending_items,
                        SUM(CASE WHEN o.deposited = false THEN oi."itemPrice" * oi.quantity ELSE 0 END) as unpaid_amount
                    FROM v2_orders o
                    JOIN v2_order_items oi ON o.id = oi."orderId"
                """
                
                if user_id:
                    base_query += f' WHERE o."userId" = \'{user_id}\''
                
                result = session.exec(text(base_query))
                data = result.fetchone()
                
                return {
                    "summary": {
                        "total_orders": data[0] if data else 0,
                        "total_items": data[1] if data else 0,
                        "total_value": data[2] if data[2] else 0,
                        "delivered_items": data[3] if data else 0,
                        "cancelled_items": data[4] if data else 0,
                        "shipping_items": data[5] if data else 0,
                        "pending_items": data[6] if data else 0,
                        "unpaid_amount": data[7] if data[7] else 0,
                    },
                    "user_id": user_id,
                    "query_time": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {"error": f"Lỗi khi lấy tổng quan đơn hàng: {str(e)}"}
    
    @staticmethod
    def get_recent_orders(user_id: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        """
        Lấy danh sách đơn hàng gần đây
        
        Args:
            user_id: ID của user (optional)
            limit: Số lượng đơn hàng tối đa (default 10)
        
        Returns:
            Dict chứa danh sách đơn hàng gần đây
        """
        try:
            with get_order_session_context() as session:
                base_query = """
                    SELECT DISTINCT
                        o."shortId",
                        o.name,
                        o.address,
                        o."createdAt",
                        o.deposited,
                        o."paymentMethod",
                        COUNT(oi.id) as item_count,
                        SUM(oi."itemPrice" * oi.quantity) as total_value,
                        CASE 
                            WHEN COUNT(oi.id) = COUNT(CASE WHEN oi."deliveredAt" IS NOT NULL THEN 1 END) THEN 'delivered'
                            WHEN COUNT(CASE WHEN oi."cancelledAt" IS NOT NULL THEN 1 END) > 0 THEN 'cancelled'
                            WHEN COUNT(CASE WHEN oi."shippedAt" IS NOT NULL THEN 1 END) > 0 THEN 'shipping'
                            ELSE 'pending'
                        END as status
                    FROM v2_orders o
                    LEFT JOIN v2_order_items oi ON o.id = oi."orderId"
                """
                
                if user_id:
                    base_query += f' WHERE o."userId" = \'{user_id}\''
                
                base_query += f'''
                    GROUP BY o.id, o."shortId", o.name, o.address, o."createdAt", o.deposited, o."paymentMethod"
                    ORDER BY o."createdAt" DESC
                    LIMIT {limit}
                '''
                
                result = session.exec(text(base_query))
                orders = result.fetchall()
                
                order_list = []
                for order in orders:
                    order_list.append({
                        "order_id": order[0],
                        "customer_name": order[1],
                        "address": order[2],
                        "created_at": order[3].isoformat() if order[3] else None,
                        "deposited": order[4],
                        "payment_method": order[5],
                        "item_count": order[6],
                        "total_value": order[7],
                        "status": order[8]
                    })
                
                return {
                    "recent_orders": order_list,
                    "count": len(order_list),
                    "user_id": user_id,
                    "query_time": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {"error": f"Lỗi khi lấy đơn hàng gần đây: {str(e)}"}
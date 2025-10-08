from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import uuid
from sqlalchemy import text
from .database import get_order_session_context
from .db_services import UserService
from decimal import Decimal


def _safe_decimal(value: Any) -> Any:
    """Convert Decimal values to float for JSON serialization."""
    if isinstance(value, Decimal):
        return float(value)
    return value


def _sanitize_data(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sanitize_data(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_sanitize_data(item) for item in value]
    return _safe_decimal(value)

class OrderManagementService:
    """Service để quản lý thông tin đơn hàng từ database ORDER"""

    @staticmethod
    def _resolve_user_identifier(user_id: Optional[str]) -> Optional[str]:
        """Convert user identifier (UUID, email, or username) to UUID string."""
        if not user_id:
            return None
        try:
            return str(uuid.UUID(str(user_id)))
        except (ValueError, TypeError):
            pass
        if "@" in str(user_id):
            user = UserService.get_user_by_email(str(user_id))
            if user:
                return str(user.id)
        user = UserService.get_user_by_username(str(user_id))
        if user:
            return str(user.id)
        return None
    
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
                base_query = """
                    SELECT COUNT(DISTINCT oi.id) as pending_count,
                           COUNT(DISTINCT o.id) as pending_orders
                    FROM v2_orders o
                    JOIN v2_order_items oi ON o.id = oi."orderId"
                    WHERE oi."deliveredAt" IS NULL 
                      AND oi."cancelledAt" IS NULL
                      AND oi."completedAt" IS NULL
                """

                params = {}
                if user_id:
                    resolved_user_id = OrderManagementService._resolve_user_identifier(user_id)
                    if not resolved_user_id:
                        return {"error": f"Không tìm thấy user id tương ứng với {user_id}"}
                    base_query += ' AND o."userId" = :user_id'
                    params["user_id"] = resolved_user_id

                stmt = text(base_query)
                if params:
                    stmt = stmt.bindparams(**params)

                result = session.exec(stmt)
                data = result.fetchone()
                
                return _sanitize_data({
                    "pending_items_count": data[0] if data else 0,
                    "pending_orders_count": data[1] if data else 0,
                    "user_id": user_id,
                    "query_time": datetime.now().isoformat()
                })
                
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

                params = {}
                if user_id:
                    resolved_user_id = OrderManagementService._resolve_user_identifier(user_id)
                    if not resolved_user_id:
                        return {"error": f"Không tìm thấy user id tương ứng với {user_id}"}
                    base_query += ' AND o."userId" = :user_id'
                    params["user_id"] = resolved_user_id

                stmt = text(base_query)
                if params:
                    stmt = stmt.bindparams(**params)

                result = session.exec(stmt)
                data = result.fetchone()

                if not data:
                    total_amount = total_items = total_orders = unpaid_amount = unpaid_orders = 0
                else:
                    total_amount = data[0] or 0
                    total_items = data[1] or 0
                    total_orders = data[2] or 0
                    unpaid_amount = data[3] or 0
                    unpaid_orders = data[4] or 0

                return _sanitize_data({
                    "total_pending_amount": _safe_decimal(total_amount),
                    "total_pending_items": total_items,
                    "total_pending_orders": total_orders,
                    "unpaid_amount": _safe_decimal(unpaid_amount),
                    "unpaid_orders": unpaid_orders,
                    "user_id": user_id,
                    "query_time": datetime.now().isoformat()
                })
                
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
            try:
                days_ahead_int = max(int(days_ahead), 0)
            except (TypeError, ValueError):
                days_ahead_int = 30

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

                params = {}
                if user_id:
                    resolved_user_id = OrderManagementService._resolve_user_identifier(user_id)
                    if not resolved_user_id:
                        return {"error": f"Không tìm thấy user id tương ứng với {user_id}"}
                    base_query += ' AND o."userId" = :user_id'
                    params["user_id"] = resolved_user_id

                base_query += ' ORDER BY oi."shippedAt" DESC'

                stmt = text(base_query)
                if params:
                    stmt = stmt.bindparams(**params)

                result = session.exec(stmt)
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
                upcoming_deliveries = len([
                    est for est in delivery_estimates
                    if datetime.fromisoformat(est['estimated_delivery_max'].replace('T', ' '))
                    <= datetime.now() + timedelta(days=days_ahead_int)
                ])
                
                sanitized_estimates = [
                    {
                        **estimate,
                        "total_value": _safe_decimal(estimate.get("total_value"))
                    }
                    for estimate in delivery_estimates
                ]

                return _sanitize_data({
                    "delivery_estimates": sanitized_estimates,
                    "total_shipped_pending": total_shipped,
                    "upcoming_deliveries": upcoming_deliveries,
                    "user_id": user_id,
                    "query_time": datetime.now().isoformat()
                })
                
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

                params = {}
                if user_id:
                    resolved_user_id = OrderManagementService._resolve_user_identifier(user_id)
                    if not resolved_user_id:
                        return {"error": f"Không tìm thấy user id tương ứng với {user_id}"}
                    base_query += ' WHERE o."userId" = :user_id'
                    params["user_id"] = resolved_user_id

                stmt = text(base_query)
                if params:
                    stmt = stmt.bindparams(**params)

                result = session.exec(stmt)
                data = result.fetchone()

                if not data:
                    totals = [0] * 8
                else:
                    totals = [value or 0 for value in data]

                return _sanitize_data({
                    "summary": {
                        "total_orders": totals[0],
                        "total_items": totals[1],
                        "total_value": _safe_decimal(totals[2]),
                        "delivered_items": totals[3],
                        "cancelled_items": totals[4],
                        "shipping_items": totals[5],
                        "pending_items": totals[6],
                        "unpaid_amount": _safe_decimal(totals[7]),
                    },
                    "user_id": user_id,
                    "query_time": datetime.now().isoformat()
                })
                
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
            try:
                limit_int = max(int(limit), 1)
            except (TypeError, ValueError):
                limit_int = 10

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

                params = {"limit": limit_int}
                if user_id:
                    resolved_user_id = OrderManagementService._resolve_user_identifier(user_id)
                    if not resolved_user_id:
                        return {"error": f"Không tìm thấy user id tương ứng với {user_id}"}
                    base_query += ' WHERE o."userId" = :user_id'
                    params["user_id"] = resolved_user_id

                base_query += '''
                    GROUP BY o.id, o."shortId", o.name, o.address, o."createdAt", o.deposited, o."paymentMethod"
                    ORDER BY o."createdAt" DESC
                    LIMIT :limit
                '''

                stmt = text(base_query)
                if params:
                    stmt = stmt.bindparams(**params)

                result = session.exec(stmt)
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
                        "total_value": _safe_decimal(order[7]),
                        "status": order[8]
                    })
                
                return _sanitize_data({
                    "recent_orders": order_list,
                    "count": len(order_list),
                    "user_id": user_id,
                    "query_time": datetime.now().isoformat()
                })
                
        except Exception as e:
            return {"error": f"Lỗi khi lấy đơn hàng gần đây: {str(e)}"}

    @staticmethod
    def get_completed_orders_summary(user_id: Optional[str] = None) -> Dict[str, Any]:
        """Tổng hợp số đơn đã hoàn thành"""
        try:
            with get_order_session_context() as session:
                base_query = """
                    SELECT 
                        COUNT(DISTINCT o.id) as completed_orders,
                        COUNT(DISTINCT oi.id) as completed_items,
                        SUM(oi."itemPrice" * oi.quantity) as completed_value
                    FROM v2_orders o
                    JOIN v2_order_items oi ON o.id = oi."orderId"
                    WHERE oi."deliveredAt" IS NOT NULL
                      AND oi."cancelledAt" IS NULL
                """

                params = {}
                if user_id:
                    resolved_user_id = OrderManagementService._resolve_user_identifier(user_id)
                    if not resolved_user_id:
                        return {"error": f"Không tìm thấy user id tương ứng với {user_id}"}
                    base_query += ' AND o."userId" = :user_id'
                    params["user_id"] = resolved_user_id

                stmt = text(base_query)
                if params:
                    stmt = stmt.bindparams(**params)

                result = session.exec(stmt)
                data = result.fetchone()

                completed_orders = data[0] if data else 0
                completed_items = data[1] if data else 0
                completed_value = _safe_decimal(data[2] if data else 0)

                return _sanitize_data({
                    "completed_orders": completed_orders,
                    "completed_items": completed_items,
                    "completed_value": completed_value,
                    "user_id": user_id,
                    "query_time": datetime.now().isoformat()
                })

        except Exception as e:
            return {"error": f"Lỗi khi lấy thống kê đơn hoàn thành: {str(e)}"}

    @staticmethod
    def get_latest_order(user_id: Optional[str] = None) -> Dict[str, Any]:
        """Thông tin đơn hàng mới đặt gần nhất"""
        try:
            with get_order_session_context() as session:
                base_query = """
                    SELECT 
                        o."shortId",
                        o.name,
                        o.address,
                        o."createdAt",
                        o.deposited,
                        o."paymentMethod",
                        SUM(oi."itemPrice" * oi.quantity) as total_value,
                        COUNT(oi.id) as item_count,
                        MAX(oi."deliveredAt") IS NOT NULL AS is_completed
                    FROM v2_orders o
                    LEFT JOIN v2_order_items oi ON o.id = oi."orderId"
                """

                params = {}
                if user_id:
                    resolved_user_id = OrderManagementService._resolve_user_identifier(user_id)
                    if not resolved_user_id:
                        return {"error": f"Không tìm thấy user id tương ứng với {user_id}"}
                    base_query += ' WHERE o."userId" = :user_id'
                    params["user_id"] = resolved_user_id

                base_query += ' GROUP BY o.id, o."shortId", o.name, o.address, o."createdAt", o.deposited, o."paymentMethod"'
                base_query += ' ORDER BY o."createdAt" DESC LIMIT 1'

                stmt = text(base_query)
                if params:
                    stmt = stmt.bindparams(**params)

                result = session.exec(stmt)
                order = result.fetchone()

                if not order:
                    return {"latest_order": None, "user_id": user_id, "query_time": datetime.now().isoformat()}

                latest = {
                    "order_id": order[0],
                    "customer_name": order[1],
                    "address": order[2],
                    "created_at": order[3].isoformat() if order[3] else None,
                    "deposited": order[4],
                    "payment_method": order[5],
                    "total_value": _safe_decimal(order[6]),
                    "item_count": order[7],
                    "is_completed": bool(order[8])
                }

                return _sanitize_data({
                    "latest_order": latest,
                    "user_id": user_id,
                    "query_time": datetime.now().isoformat()
                })

        except Exception as e:
            return {"error": f"Lỗi khi lấy đơn mới nhất: {str(e)}"}

    @staticmethod
    def get_next_delivery_order(user_id: Optional[str] = None) -> Dict[str, Any]:
        """Tìm đơn hàng sắp giao gần nhất dựa trên ước tính"""
        try:
            with get_order_session_context() as session:
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

                params = {}
                if user_id:
                    resolved_user_id = OrderManagementService._resolve_user_identifier(user_id)
                    if not resolved_user_id:
                        return {"error": f"Không tìm thấy user id tương ứng với {user_id}"}
                    base_query += ' AND o."userId" = :user_id'
                    params["user_id"] = resolved_user_id

                stmt = text(base_query)
                if params:
                    stmt = stmt.bindparams(**params)

                result = session.exec(stmt)
                shipped_orders = result.fetchall()

                upcoming_orders: List[Dict[str, Any]] = []
                for order in shipped_orders:
                    shipped_date = order[3]
                    if not shipped_date:
                        continue
                    estimated_delivery_min = shipped_date + timedelta(days=3)
                    estimated_delivery_max = shipped_date + timedelta(days=5)
                    upcoming_orders.append({
                        "order_id": order[0],
                        "customer_name": order[1],
                        "address": order[2],
                        "shipped_at": shipped_date.isoformat(),
                        "estimated_delivery_min": estimated_delivery_min.isoformat(),
                        "estimated_delivery_max": estimated_delivery_max.isoformat(),
                        "total_value": _safe_decimal(order[4]),
                        "quantity": order[5],
                        "phone": order[6]
                    })

                if not upcoming_orders:
                    return {
                        "next_delivery_order": None,
                        "user_id": user_id,
                        "query_time": datetime.now().isoformat()
                    }

                next_order = min(
                    upcoming_orders,
                    key=lambda x: x["estimated_delivery_min"]
                )

                return _sanitize_data({
                    "next_delivery_order": next_order,
                    "user_id": user_id,
                    "query_time": datetime.now().isoformat()
                })

        except Exception as e:
            return {"error": f"Lỗi khi lấy đơn sắp giao: {str(e)}"}

    @staticmethod
    def get_highest_value_order(user_id: Optional[str] = None) -> Dict[str, Any]:
        """Đơn hàng có giá trị cao nhất"""
        try:
            with get_order_session_context() as session:
                base_query = """
                    SELECT 
                        o."shortId" as order_id,
                        o.name,
                        o.address,
                        o."createdAt",
                        SUM(oi."itemPrice" * oi.quantity) as total_value,
                        COUNT(oi.id) as item_count,
                        o."paymentMethod"
                    FROM v2_orders o
                    JOIN v2_order_items oi ON o.id = oi."orderId"
                    WHERE oi."cancelledAt" IS NULL
                """

                params = {}
                if user_id:
                    resolved_user_id = OrderManagementService._resolve_user_identifier(user_id)
                    if not resolved_user_id:
                        return {"error": f"Không tìm thấy user id tương ứng với {user_id}"}
                    base_query += ' AND o."userId" = :user_id'
                    params["user_id"] = resolved_user_id

                base_query += ' GROUP BY o.id, o."shortId", o.name, o.address, o."createdAt", o."paymentMethod"'
                base_query += ' ORDER BY total_value DESC NULLS LAST LIMIT 1'

                stmt = text(base_query)
                if params:
                    stmt = stmt.bindparams(**params)

                result = session.exec(stmt)
                order = result.fetchone()

                if not order:
                    return {
                        "highest_value_order": None,
                        "user_id": user_id,
                        "query_time": datetime.now().isoformat()
                    }

                formatted = {
                    "order_id": order[0],
                    "customer_name": order[1],
                    "address": order[2],
                    "created_at": order[3].isoformat() if order[3] else None,
                    "total_value": _safe_decimal(order[4]),
                    "item_count": order[5],
                    "payment_method": order[6]
                }

                return _sanitize_data({
                    "highest_value_order": formatted,
                    "user_id": user_id,
                    "query_time": datetime.now().isoformat()
                })

        except Exception as e:
            return {"error": f"Lỗi khi tìm đơn giá trị cao nhất: {str(e)}"}

    @staticmethod
    def get_lowest_value_order(user_id: Optional[str] = None) -> Dict[str, Any]:
        """Đơn hàng có giá trị thấp nhất"""
        try:
            with get_order_session_context() as session:
                base_query = """
                    SELECT 
                        o."shortId" as order_id,
                        o.name,
                        o.address,
                        o."createdAt",
                        SUM(oi."itemPrice" * oi.quantity) as total_value,
                        COUNT(oi.id) as item_count,
                        o."paymentMethod"
                    FROM v2_orders o
                    JOIN v2_order_items oi ON o.id = oi."orderId"
                    WHERE oi."cancelledAt" IS NULL
                """

                params = {}
                if user_id:
                    resolved_user_id = OrderManagementService._resolve_user_identifier(user_id)
                    if not resolved_user_id:
                        return {"error": f"Không tìm thấy user id tương ứng với {user_id}"}
                    base_query += ' AND o."userId" = :user_id'
                    params["user_id"] = resolved_user_id

                base_query += ' GROUP BY o.id, o."shortId", o.name, o.address, o."createdAt", o."paymentMethod"'
                base_query += ' ORDER BY total_value ASC NULLS LAST LIMIT 1'

                stmt = text(base_query)
                if params:
                    stmt = stmt.bindparams(**params)

                result = session.exec(stmt)
                order = result.fetchone()

                if not order:
                    return {
                        "lowest_value_order": None,
                        "user_id": user_id,
                        "query_time": datetime.now().isoformat()
                    }

                formatted = {
                    "order_id": order[0],
                    "customer_name": order[1],
                    "address": order[2],
                    "created_at": order[3].isoformat() if order[3] else None,
                    "total_value": _safe_decimal(order[4]),
                    "item_count": order[5],
                    "payment_method": order[6]
                }

                return _sanitize_data({
                    "lowest_value_order": formatted,
                    "user_id": user_id,
                    "query_time": datetime.now().isoformat()
                })

        except Exception as e:
            return {"error": f"Lỗi khi tìm đơn giá trị thấp nhất: {str(e)}"}

    @staticmethod
    def get_average_order_value(user_id: Optional[str] = None) -> Dict[str, Any]:
        """Số tiền trung bình đã chi cho một đơn hàng"""
        try:
            with get_order_session_context() as session:
                base_query = """
                    SELECT AVG(order_totals.total_value) as average_value
                    FROM (
                        SELECT 
                            SUM(oi."itemPrice" * oi.quantity) as total_value
                        FROM v2_orders o
                        JOIN v2_order_items oi ON o.id = oi."orderId"
                        WHERE oi."cancelledAt" IS NULL
                """

                params = {}
                if user_id:
                    resolved_user_id = OrderManagementService._resolve_user_identifier(user_id)
                    if not resolved_user_id:
                        return {"error": f"Không tìm thấy user id tương ứng với {user_id}"}
                    base_query += ' AND o."userId" = :user_id'
                    params["user_id"] = resolved_user_id

                base_query += """
                        GROUP BY o.id
                    ) as order_totals
                """

                stmt = text(base_query)
                if params:
                    stmt = stmt.bindparams(**params)

                result = session.exec(stmt)
                data = result.fetchone()

                average_value = _safe_decimal(data[0]) if data and data[0] is not None else 0

                return _sanitize_data({
                    "average_order_value": average_value,
                    "user_id": user_id,
                    "query_time": datetime.now().isoformat()
                })

        except Exception as e:
            return {"error": f"Lỗi khi tính giá trị trung bình đơn hàng: {str(e)}"}
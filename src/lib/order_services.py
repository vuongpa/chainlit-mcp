from typing import Optional, List, Union, Dict, Any
from sqlmodel import select, func, text
from sqlalchemy import desc
import uuid
from datetime import datetime, timedelta

from .order_models import Balance, BalanceRead
from .database import get_order_session_context


class BalanceService:
    """Service class for Balance operations in order database"""
    
    @staticmethod
    def get_user_balance(user_id: Union[str, uuid.UUID]) -> Optional[BalanceRead]:
        """Get user balance by user ID"""
        try:
            with get_order_session_context() as session:
                # Convert string to UUID if needed
                if isinstance(user_id, str):
                    user_id = uuid.UUID(user_id)
                
                balance = session.get(Balance, user_id)
                if balance:
                    return BalanceRead(
                        userId=balance.userId,
                        balance=balance.balance,
                        point=balance.point,
                        createdAt=balance.createdAt,
                        updatedAt=balance.updatedAt
                    )
                return None
        except Exception as e:
            print(f"Error getting user balance: {e}")
            return None
    
    @staticmethod
    def get_all_balances(limit: int = 100, offset: int = 0) -> List[BalanceRead]:
        """Get all balances with pagination"""
        try:
            with get_order_session_context() as session:
                statement = select(Balance).offset(offset).limit(limit)
                balances = session.exec(statement).all()
                
                return [
                    BalanceRead(
                        userId=balance.userId,
                        balance=balance.balance,
                        point=balance.point,
                        createdAt=balance.createdAt,
                        updatedAt=balance.updatedAt
                    )
                    for balance in balances
                ]
        except Exception as e:
            print(f"Error getting all balances: {e}")
            return []
    
    @staticmethod
    def get_balances_by_amount_range(min_balance: int = 0, max_balance: Optional[int] = None, 
                                   limit: int = 100) -> List[BalanceRead]:
        """Get balances within a specific amount range"""
        try:
            with get_order_session_context() as session:
                statement = select(Balance).where(Balance.balance >= min_balance)
                
                if max_balance is not None:
                    statement = statement.where(Balance.balance <= max_balance)
                
                statement = statement.order_by(desc(Balance.balance)).limit(limit)
                balances = session.exec(statement).all()
                
                return [
                    BalanceRead(
                        userId=balance.userId,
                        balance=balance.balance,
                        point=balance.point,
                        createdAt=balance.createdAt,
                        updatedAt=balance.updatedAt
                    )
                    for balance in balances
                ]
        except Exception as e:
            print(f"Error getting balances by amount range: {e}")
            return []
    
    @staticmethod
    def get_top_balances(limit: int = 10) -> List[BalanceRead]:
        """Get top balances by amount"""
        try:
            with get_order_session_context() as session:
                statement = select(Balance).order_by(desc(Balance.balance)).limit(limit)
                balances = session.exec(statement).all()
                
                return [
                    BalanceRead(
                        userId=balance.userId,
                        balance=balance.balance,
                        point=balance.point,
                        createdAt=balance.createdAt,
                        updatedAt=balance.updatedAt
                    )
                    for balance in balances
                ]
        except Exception as e:
            print(f"Error getting top balances: {e}")
            return []
    
    @staticmethod
    def get_balance_statistics() -> Dict[str, Any]:
        """Get balance statistics"""
        try:
            with get_order_session_context() as session:
                # Count total users with balance
                total_users_result = session.exec(select(func.count(Balance.userId)))
                total_users = total_users_result.first()
                
                # Get total balance and points
                total_balance_result = session.exec(select(func.sum(Balance.balance)))
                total_balance = total_balance_result.first() or 0
                
                total_points_result = session.exec(select(func.sum(Balance.point)))
                total_points = total_points_result.first() or 0
                
                # Get average balance and points
                avg_balance_result = session.exec(select(func.avg(Balance.balance)))
                avg_balance_raw = avg_balance_result.first()
                avg_balance = float(avg_balance_raw) if avg_balance_raw is not None else 0.0
                
                avg_points_result = session.exec(select(func.avg(Balance.point)))
                avg_points_raw = avg_points_result.first()
                avg_points = float(avg_points_raw) if avg_points_raw is not None else 0.0
                
                # Get max and min balances
                max_balance_result = session.exec(select(func.max(Balance.balance)))
                max_balance = max_balance_result.first() or 0
                
                min_balance_result = session.exec(select(func.min(Balance.balance)))
                min_balance = min_balance_result.first() or 0
                
                return {
                    "total_users": total_users,
                    "total_balance": total_balance,
                    "total_points": total_points,
                    "average_balance": avg_balance,
                    "average_points": avg_points,
                    "max_balance": max_balance,
                    "min_balance": min_balance,
                    "total_balance_formatted": f"{total_balance:,}",
                    "total_points_formatted": f"{total_points:,}",
                    "average_balance_formatted": f"{avg_balance:,.2f}",
                    "average_points_formatted": f"{avg_points:,.2f}",
                    "max_balance_formatted": f"{max_balance:,}",
                    "min_balance_formatted": f"{min_balance:,}"
                }
        except Exception as e:
            print(f"Error getting balance statistics: {e}")
            return {}
    
    @staticmethod
    def search_balances_by_user_ids(user_ids: List[Union[str, uuid.UUID]]) -> List[BalanceRead]:
        """Search balances for multiple user IDs"""
        try:
            with get_order_session_context() as session:
                # Convert all to UUID
                uuid_list = []
                for user_id in user_ids:
                    if isinstance(user_id, str):
                        uuid_list.append(uuid.UUID(user_id))
                    else:
                        uuid_list.append(user_id)
                
                statement = select(Balance).where(Balance.userId.in_(uuid_list))
                balances = session.exec(statement).all()
                
                return [
                    BalanceRead(
                        userId=balance.userId,
                        balance=balance.balance,
                        point=balance.point,
                        createdAt=balance.createdAt,
                        updatedAt=balance.updatedAt
                    )
                    for balance in balances
                ]
        except Exception as e:
            print(f"Error searching balances by user IDs: {e}")
            return []
    
    @staticmethod
    def get_recent_balance_updates(days: int = 7, limit: int = 100) -> List[BalanceRead]:
        """Get recently updated balances"""
        try:
            with get_order_session_context() as session:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                
                statement = (
                    select(Balance)
                    .where(Balance.updatedAt >= cutoff_date)
                    .order_by(desc(Balance.updatedAt))
                    .limit(limit)
                )
                
                balances = session.exec(statement).all()
                
                return [
                    BalanceRead(
                        userId=balance.userId,
                        balance=balance.balance,
                        point=balance.point,
                        createdAt=balance.createdAt,
                        updatedAt=balance.updatedAt
                    )
                    for balance in balances
                ]
        except Exception as e:
            print(f"Error getting recent balance updates: {e}")
            return []
    
    @staticmethod
    def execute_custom_balance_query(query: str) -> List[Dict[str, Any]]:
        """Execute custom SQL query on balance-related tables"""
        try:
            with get_order_session_context() as session:
                result = session.exec(text(query))
                
                # Convert result to list of dictionaries
                columns = result.keys()
                rows = result.fetchall()
                
                return [
                    dict(zip(columns, row)) for row in rows
                ]
        except Exception as e:
            print(f"Error executing custom query: {e}")
            return []


class OrderDatabaseService:
    """General service for order database operations"""
    
    @staticmethod
    def get_table_info(table_name: str) -> Dict[str, Any]:
        """Get detailed information about a table"""
        try:
            with get_order_session_context() as session:
                # Get column information
                result = session.exec(text(f"""
                    SELECT 
                        column_name,
                        data_type,
                        character_maximum_length,
                        is_nullable,
                        column_default,
                        ordinal_position
                    FROM information_schema.columns 
                    WHERE table_name = '{table_name}' 
                    AND table_schema = 'public'
                    ORDER BY ordinal_position;
                """))
                
                columns = []
                for row in result.fetchall():
                    col_name, data_type, max_length, is_nullable, col_default, position = row
                    columns.append({
                        'name': col_name,
                        'type': data_type,
                        'max_length': max_length,
                        'nullable': is_nullable == 'YES',
                        'default': col_default,
                        'position': position
                    })
                
                # Get row count
                count_result = session.exec(text(f"SELECT COUNT(*) FROM public.{table_name}"))
                row_count = count_result.first()
                
                return {
                    'table_name': table_name,
                    'columns': columns,
                    'row_count': row_count
                }
        except Exception as e:
            print(f"Error getting table info: {e}")
            return {}
    
    @staticmethod
    def get_all_tables() -> List[str]:
        """Get list of all tables in the order database"""
        try:
            with get_order_session_context() as session:
                result = session.exec(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name;
                """))
                
                return [row[0] for row in result.fetchall()]
        except Exception as e:
            print(f"Error getting all tables: {e}")
            return []
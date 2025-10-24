"""
SQL Builder utility for Georgia Dashboard v9.18
Helper for building complex SQL queries programmatically
"""
from typing import List, Dict, Any, Optional


class SQLBuilder:
    """Simple SQL query builder for common patterns"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset the builder state"""
        self._select_fields = []
        self._from_table = ""
        self._joins = []
        self._where_conditions = []
        self._group_by = []
        self._having_conditions = []
        self._order_by = []
        self._limit_count = None
        self._params = []
    
    def select(self, *fields: str):
        """Add SELECT fields"""
        self._select_fields.extend(fields)
        return self
    
    def from_table(self, table: str):
        """Set FROM table"""
        self._from_table = table
        return self
    
    def join(self, table: str, condition: str, join_type: str = "INNER"):
        """Add JOIN clause"""
        self._joins.append(f"{join_type} JOIN {table} ON {condition}")
        return self
    
    def where(self, condition: str, *params):
        """Add WHERE condition"""
        self._where_conditions.append(condition)
        self._params.extend(params)
        return self
    
    def group_by(self, *fields: str):
        """Add GROUP BY fields"""
        self._group_by.extend(fields)
        return self
    
    def having(self, condition: str, *params):
        """Add HAVING condition"""
        self._having_conditions.append(condition)
        self._params.extend(params)
        return self
    
    def order_by(self, field: str, direction: str = "ASC"):
        """Add ORDER BY clause"""
        self._order_by.append(f"{field} {direction}")
        return self
    
    def limit(self, count: int):
        """Add LIMIT clause"""
        self._limit_count = count
        return self
    
    def build(self) -> tuple[str, tuple]:
        """Build the final SQL query and parameters"""
        if not self._select_fields:
            raise ValueError("SELECT fields are required")
        if not self._from_table:
            raise ValueError("FROM table is required")
        
        # Build query parts
        query_parts = []
        
        # SELECT
        select_clause = "SELECT " + ", ".join(self._select_fields)
        query_parts.append(select_clause)
        
        # FROM
        query_parts.append(f"FROM {self._from_table}")
        
        # JOINs
        for join in self._joins:
            query_parts.append(join)
        
        # WHERE
        if self._where_conditions:
            where_clause = "WHERE " + " AND ".join(f"({cond})" for cond in self._where_conditions)
            query_parts.append(where_clause)
        
        # GROUP BY
        if self._group_by:
            group_clause = "GROUP BY " + ", ".join(self._group_by)
            query_parts.append(group_clause)
        
        # HAVING
        if self._having_conditions:
            having_clause = "HAVING " + " AND ".join(f"({cond})" for cond in self._having_conditions)
            query_parts.append(having_clause)
        
        # ORDER BY
        if self._order_by:
            order_clause = "ORDER BY " + ", ".join(self._order_by)
            query_parts.append(order_clause)
        
        # LIMIT (SQL Server uses TOP, but this is a generic builder)
        if self._limit_count:
            query_parts.append(f"LIMIT {self._limit_count}")
        
        query = "\n".join(query_parts)
        return query, tuple(self._params)
    
    @staticmethod
    def quick_select(table: str, fields: List[str] = None, where: Dict[str, Any] = None) -> tuple[str, tuple]:
        """Quick helper for simple SELECT queries"""
        builder = SQLBuilder()
        
        if fields:
            builder.select(*fields)
        else:
            builder.select("*")
        
        builder.from_table(table)
        
        params = []
        if where:
            for field, value in where.items():
                builder.where(f"{field} = %s")
                params.append(value)
        
        query, query_params = builder.build()
        return query, tuple(params) + query_params

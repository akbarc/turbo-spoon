import json
import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime

import pandas as pd

from database_pymssql import SQLServerConnection

logger = logging.getLogger(__name__)


def fetch_dataframe(db: SQLServerConnection, query: str, params=None, description: str = "") -> pd.DataFrame:
    return db.execute_query(query, params=params, description=description or "Query")


def discover_tables_and_columns(db: SQLServerConnection) -> pd.DataFrame:
    q = """
    SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE,
           ISNULL(CHARACTER_MAXIMUM_LENGTH, 0) AS CHARACTER_MAXIMUM_LENGTH,
           IS_NULLABLE,
           COLUMN_DEFAULT
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA='dbo'
    ORDER BY TABLE_NAME, ORDINAL_POSITION
    """
    return fetch_dataframe(db, q, description="Discover tables/columns")


def discover_primary_keys(db: SQLServerConnection) -> pd.DataFrame:
    q = """
    SELECT
      tc.TABLE_NAME,
      kcu.COLUMN_NAME
    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
    JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
      ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
    WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
      AND tc.TABLE_SCHEMA = 'dbo'
    ORDER BY tc.TABLE_NAME, kcu.ORDINAL_POSITION
    """
    return fetch_dataframe(db, q, description="Discover primary keys")


def discover_foreign_keys(db: SQLServerConnection) -> pd.DataFrame:
    q = """
    SELECT
      fk.name AS FK_Name,
      tp.name AS FK_Table,
      cp.name AS FK_Column,
      tr.name AS PK_Table,
      cr.name AS PK_Column
    FROM sys.foreign_key_columns fkc
    INNER JOIN sys.objects fk ON fkc.constraint_object_id = fk.object_id
    INNER JOIN sys.tables tp ON fkc.parent_object_id = tp.object_id
    INNER JOIN sys.columns cp ON fkc.parent_object_id = cp.object_id AND fkc.parent_column_id = cp.column_id
    INNER JOIN sys.tables tr ON fkc.referenced_object_id = tr.object_id
    INNER JOIN sys.columns cr ON fkc.referenced_object_id = cr.object_id AND fkc.referenced_column_id = cr.column_id
    ORDER BY tp.name, cp.name
    """
    return fetch_dataframe(db, q, description="Discover foreign keys")


def discover_indexes(db: SQLServerConnection) -> pd.DataFrame:
    q = """
    SELECT t.name AS TableName,
           ind.name AS IndexName,
           ind.is_unique AS IsUnique,
           ind.is_primary_key AS IsPrimaryKey,
           STUFF((
               SELECT ',' + c.name
               FROM sys.index_columns ic2
               JOIN sys.columns c ON c.object_id = ic2.object_id AND c.column_id = ic2.column_id
               WHERE ic2.object_id = ind.object_id AND ic2.index_id = ind.index_id
               ORDER BY ic2.key_ordinal
               FOR XML PATH(''), TYPE
           ).value('.', 'NVARCHAR(MAX)'), 1, 1, '') AS Columns
    FROM sys.indexes ind
    JOIN sys.tables t ON ind.object_id = t.object_id
    WHERE ind.is_hypothetical = 0 AND t.is_ms_shipped = 0
    ORDER BY t.name, ind.name
    """
    return fetch_dataframe(db, q, description="Discover indexes")


def discover_views(db: SQLServerConnection) -> pd.DataFrame:
    q = """
    SELECT TABLE_SCHEMA, TABLE_NAME
    FROM INFORMATION_SCHEMA.VIEWS
    ORDER BY TABLE_NAME
    """
    return fetch_dataframe(db, q, description="Discover views")


def count_rows(db: SQLServerConnection, table: str) -> int:
    try:
        q = f"SELECT COUNT(*) AS cnt FROM [dbo].[{table}]"
        df = fetch_dataframe(db, q, description=f"Row count {table}")
        return int(df.iloc[0]["cnt"]) if not df.empty else 0
    except Exception as e:
        logger.warning(f"Row count failed for {table}: {e}")
        return -1


def min_max_date(db: SQLServerConnection, table: str, column: str) -> Dict[str, Any]:
    try:
        q = f"SELECT MIN([{column}]) AS min_dt, MAX([{column}]) AS max_dt FROM [dbo].[{table}]"
        df = fetch_dataframe(db, q, description=f"Date range {table}.{column}")
        if not df.empty:
            return {"min": str(df.iloc[0]["min_dt"]) if pd.notnull(df.iloc[0]["min_dt"]) else None,
                    "max": str(df.iloc[0]["max_dt"]) if pd.notnull(df.iloc[0]["max_dt"]) else None}
    except Exception as e:
        logger.warning(f"Date range failed for {table}.{column}: {e}")
    return {"min": None, "max": None}


def sample_rows(db: SQLServerConnection, table: str, top_n: int = 5) -> List[Dict[str, Any]]:
    try:
        q = f"SELECT TOP {top_n} * FROM [dbo].[{table}] ORDER BY 1 DESC"
        df = fetch_dataframe(db, q, description=f"Sample {table}")
        return df.to_dict('records') if not df.empty else []
    except Exception as e:
        logger.warning(f"Sample rows failed for {table}: {e}")
        return []


def is_numeric_type(sql_type: str) -> bool:
    return sql_type.lower() in {"int", "bigint", "smallint", "tinyint", "numeric", "decimal", "float", "real", "money", "smallmoney"}


def is_text_type(sql_type: str) -> bool:
    return sql_type.lower() in {"varchar", "nvarchar", "nchar", "char", "text", "ntext"}


def is_date_type(sql_type: str) -> bool:
    return sql_type.lower() in {"date", "datetime", "smalldatetime", "datetime2"}


def compute_numeric_stats(db: SQLServerConnection, table: str, column: str) -> Dict[str, Any]:
    try:
        q = f"SELECT COUNT([{column}]) AS n, MIN([{column}]) AS mn, MAX([{column}]) AS mx, AVG(CAST([{column}] AS FLOAT)) AS avg, SUM(CAST([{column}] AS FLOAT)) AS sm FROM [dbo].[{table}]"
        df = fetch_dataframe(db, q, description=f"Numeric stats {table}.{column}")
        if not df.empty:
            r = df.iloc[0]
            return {"count": int(r["n"]) if pd.notnull(r["n"]) else 0,
                    "min": r["mn"], "max": r["mx"], "avg": r["avg"], "sum": r["sm"]}
    except Exception as e:
        logger.warning(f"Numeric stats failed for {table}.{column}: {e}")
    return {"count": 0, "min": None, "max": None, "avg": None, "sum": None}


def compute_text_stats(db: SQLServerConnection, table: str, column: str) -> Dict[str, Any]:
    try:
        q = f"SELECT COUNT([{column}]) AS n, MIN(LEN([{column}])) AS min_len, MAX(LEN([{column}])) AS max_len FROM [dbo].[{table}]"
        df = fetch_dataframe(db, q, description=f"Text stats {table}.{column}")
        if not df.empty:
            r = df.iloc[0]
            return {"count": int(r["n"]) if pd.notnull(r["n"]) else 0,
                    "min_len": int(r["min_len"]) if pd.notnull(r["min_len"]) else None,
                    "max_len": int(r["max_len"]) if pd.notnull(r["max_len"]) else None}
    except Exception as e:
        logger.warning(f"Text stats failed for {table}.{column}: {e}")
    return {"count": 0, "min_len": None, "max_len": None}


def top_frequencies(db: SQLServerConnection, table: str, column: str, limit: int = 20) -> List[Tuple[Any, int]]:
    try:
        q = f"SELECT TOP {limit} [{column}] AS val, COUNT(*) AS cnt FROM [dbo].[{table}] GROUP BY [{column}] ORDER BY COUNT(*) DESC"
        df = fetch_dataframe(db, q, description=f"Value frequencies {table}.{column}")
        return [(row["val"], int(row["cnt"])) for _, row in df.iterrows()] if not df.empty else []
    except Exception as e:
        logger.warning(f"Frequencies failed for {table}.{column}: {e}")
    return []


def suggest_likely_joins(table: str, columns_meta: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    suggestions: List[Dict[str, str]] = []
    for col in columns_meta:
        name = col["name"]
        if name.lower().endswith("id") and name.lower() != "id":
            base = name[:-2]
            # Heuristic common mappings
            mapped_table = {
                "customer": "Customer",
                "item": "Item",
                "category": "Category",
                "transaction": "Transaction",
                "accountreceivable": "AccountReceivable",
            }.get(base.lower(), base.capitalize())
            suggestions.append({
                "from_table": table, "from_column": name, "to_table": mapped_table, "to_column": "ID"
            })
    return suggestions


def run_discovery() -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "tables": {},
        "primary_keys": {},
        "foreign_keys": [],
        "indexes": [],
        "views": [],
        "verified_rules": {
            "date_columns": {},
            "currency_columns": {},
        },
    }
    priority_tables = {"Payment", "Transaction", "TransactionEntry", "AccountReceivable", "AccountReceivableHistory", "Item", "Category", "Customer"}
    with SQLServerConnection() as db:
        cols_df = discover_tables_and_columns(db)
        pk_df = discover_primary_keys(db)
        fk_df = discover_foreign_keys(db)
        idx_df = discover_indexes(db)
        views_df = discover_views(db)

        # Fill PKs
        for _, row in pk_df.iterrows():
            tbl = str(row["TABLE_NAME"])
            col = str(row["COLUMN_NAME"])
            report["primary_keys"].setdefault(tbl, []).append(col)

        # FKs
        for _, row in fk_df.iterrows():
            report["foreign_keys"].append({
                "fk_table": str(row["FK_Table"]),
                "fk_column": str(row["FK_Column"]),
                "pk_table": str(row["PK_Table"]),
                "pk_column": str(row["PK_Column"]),
            })

        # Indexes
        for _, row in idx_df.iterrows():
            report["indexes"].append({
                "table": str(row["TableName"]),
                "index": str(row["IndexName"]),
                "is_unique": bool(row["IsUnique"]),
                "is_primary": bool(row["IsPrimaryKey"]),
                "columns": str(row["Columns"]).split(',') if pd.notnull(row["Columns"]) else [],
            })

        # Views
        for _, row in views_df.iterrows():
            report["views"].append({"schema": str(row["TABLE_SCHEMA"]), "name": str(row["TABLE_NAME"])})

        # Per-table details
        tables = sorted(set(cols_df["TABLE_NAME"]))
        for tbl in tables:
            tcols_df = cols_df[cols_df["TABLE_NAME"] == tbl]
            columns_meta = [{
                "name": str(r["COLUMN_NAME"]),
                "type": str(r["DATA_TYPE"]),
                "max_length": int(r["CHARACTER_MAXIMUM_LENGTH"]) if pd.notnull(r["CHARACTER_MAXIMUM_LENGTH"]) else None,
                "nullable": str(r["IS_NULLABLE"]).upper() == 'YES',
                "default": (str(r["COLUMN_DEFAULT"]) if pd.notnull(r["COLUMN_DEFAULT"]) else None),
            } for _, r in tcols_df.iterrows()]

            # Date columns
            date_cols = [c["name"] for c in columns_meta if is_date_type(c["type"]) or c["name"].lower() in ("time", "date", "transactiontime")]
            date_ranges = {dc: min_max_date(db, tbl, dc) for dc in set(date_cols)}

            rc = count_rows(db, tbl)
            sample = sample_rows(db, tbl)

            # Column stats for priority tables only (to avoid heavy scans)
            column_stats: Dict[str, Any] = {}
            currency_cols: List[str] = []
            if tbl in priority_tables and rc >= 0:
                for col in columns_meta:
                    cname = col["name"]
                    ctype = col["type"]
                    # Currency-ish by name hint
                    if any(k in cname.lower() for k in ["amount", "total", "revenue", "cost", "price", "profit", "balance", "paid"]):
                        currency_cols.append(cname)
                    if is_numeric_type(ctype):
                        column_stats[cname] = {"numeric": compute_numeric_stats(db, tbl, cname)}
                    elif is_text_type(ctype) and col["max_length"] and col["max_length"] <= 200:
                        stats = compute_text_stats(db, tbl, cname)
                        # Only compute frequencies if distinct set likely small (<50)
                        # Use a cheap estimate by sampling frequencies directly but cap result length
                        freqs = top_frequencies(db, tbl, cname, limit=20)
                        column_stats[cname] = {"text": stats, "top_values": freqs}

            # Likely joins by heuristic if no FK declared
            likely_joins = suggest_likely_joins(tbl, columns_meta)

            report["tables"][tbl] = {
                "columns": columns_meta,
                "row_count": rc,
                "date_ranges": date_ranges,
                "sample_rows": sample,
                "column_stats": column_stats,
                "likely_joins": likely_joins,
            }

            if currency_cols:
                report["verified_rules"]["currency_columns"][tbl] = currency_cols

        # Verify canonical date columns (if present)
        for tbl, canonical in {
            "Payment": "Time",
            "Transaction": "Time",
            "TransactionEntry": "TransactionTime",
            "AccountReceivable": "Date",
            "AccountReceivableHistory": "Date",
        }.items():
            cols = [c["name"] for c in report["tables"].get(tbl, {}).get("columns", [])]
            if canonical in cols:
                report["verified_rules"]["date_columns"][tbl] = canonical

    return report


def save_report(report: Dict[str, Any], path: str) -> None:
    with open(path, 'w') as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    out_path = "archive/data_exports/focused_database_report.json"
    try:
        rep = run_discovery()
        save_report(rep, out_path)
        print(f"Saved discovery report to {out_path}")
    except Exception as e:
        logger.error(f"Discovery failed: {e}")
        raise 
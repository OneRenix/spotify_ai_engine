"""
src/schemas.py
Pydantic contracts and SQL validation guardrails.
"""

from typing import Literal
from pydantic import BaseModel, Field, field_validator
import sqlparse

FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", 
    "CREATE", "REPLACE", "COPY", "EXPORT", "IMPORT", "ATTACH", 
    "DETACH", "PRAGMA", "CALL", "LOAD", "INSTALL"
}

class SQLQueryResponse(BaseModel):
    thought_process: str = Field(
        description="One-sentence summary of the SQL choices."
    )
    sql_query: str = Field(
        description="A read-only DuckDB SELECT or WITH query for the Spotify tables."
    )
    chart_recommendation: Literal["bar", "line", "scatter", "table"] = Field(
        description="Recommended visualization: bar, line, scatter, or table."
    )

    @field_validator("sql_query")
    @classmethod
    def validate_and_sanitize_sql(cls, v: str) -> str:
        clean = v.strip().rstrip(";")
        
        # 1. Parse statement into an AST using sqlparse
        parsed = sqlparse.parse(clean)
        
        # Block multi-statement execution (e.g. "SELECT 1; DROP TABLE tracks;")
        if len(parsed) != 1:
            raise ValueError("SQL Injection Guard: Multiple SQL statements detected. Only a single query is allowed.")
            
        statement = parsed[0]
        
        # Ensure it is purely a SELECT or WITH statement
        stmt_type = statement.get_type()
        if stmt_type not in ("SELECT", "UNKNOWN"):  # "UNKNOWN" can happen for statements starting with CTE (WITH ...)
            raise ValueError(f"SQL Injection Guard: Disallowed statement type '{stmt_type}'. Only SELECT statements are permitted.")
            
        # Check starting token for CTEs or SELECT
        first_token = next((tok for tok in statement.tokens if not tok.is_whitespace), None)
        if not first_token or first_token.value.upper() not in ("SELECT", "WITH"):
            raise ValueError("SQL Injection Guard: Queries must begin with SELECT or WITH.")

        # 2. Token-level keyword blocklist inspection
        flattened_tokens = [tok.value.upper() for tok in statement.flatten() if not tok.is_whitespace]
        detected_forbidden = FORBIDDEN_KEYWORDS.intersection(flattened_tokens)
        if detected_forbidden:
            raise ValueError(f"SQL Injection Guard: Prohibited DDL/DML keywords found: {', '.join(detected_forbidden)}")

        # 3. Disallow SQL comment tokens (often used to truncate queries in injection attacks)
        for token in statement.flatten():
            if token.ttype in (sqlparse.tokens.Comment, sqlparse.tokens.Comment.Single, sqlparse.tokens.Comment.Multiline):
                raise ValueError("SQL Injection Guard: Comments (-- or /* */) are not permitted in queries.")

        return clean
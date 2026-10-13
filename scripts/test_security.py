"""
scripts/test_security.py
Validates that SQL injection attempts are caught before execution.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.schemas import SQLQueryResponse

attacks = [
    # Multiple statements
    ("SELECT * FROM tracks; DROP TABLE tracks;", "Multiple statements"),
    # DDL statement
    ("DROP TABLE tracks", "Direct DROP"),
    # Comment truncation
    ("SELECT * FROM tracks WHERE track_id = '1' -- AND popularity > 50", "SQL comment bypass"),
    # Write statement
    ("INSERT INTO tracks VALUES ('1', 'bad', 'bad', 'bad', 0, 'pop')", "Direct INSERT"),
]

print("🛡️ Testing SQL Injection Defenses:\n")
for bad_sql, test_name in attacks:
    try:
        SQLQueryResponse(
            thought_process="testing injection",
            sql_query=bad_sql,
            chart_recommendation="table"
        )
        print(f"❌ FAILED: {test_name} was NOT caught!")
    except Exception as e:
        print(f"✅ PASSED: {test_name} was blocked -> {e.errors()[0]['msg']}")
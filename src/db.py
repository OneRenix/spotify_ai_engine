"""
src/db.py
DuckDB in-memory OLAP session with Parquet table views.
"""

from pathlib import Path
import duckdb
import pandas as pd

TRACKS_PATH = Path("data/tracks.parquet")
AUDIO_PATH = Path("data/audio_features.parquet")

def get_db_connection() -> duckdb.DuckDBPyConnection:
    """
    Initializes an in-memory DuckDB connection and registers Parquet tables as views.
    """
    if not TRACKS_PATH.exists() or not AUDIO_PATH.exists():
        raise FileNotFoundError(
            "Parquet files not found in data/. Run `uv run python scripts/prepare_data.py` first."
        )

    con = duckdb.connect(database=":memory:")
    con.execute(f"CREATE VIEW tracks AS SELECT * FROM read_parquet('{TRACKS_PATH}')")
    con.execute(f"CREATE VIEW audio_features AS SELECT * FROM read_parquet('{AUDIO_PATH}')")
    return con

def execute_query(con: duckdb.DuckDBPyConnection, sql: str) -> pd.DataFrame:
    """
    Executes a validated read-only SQL query against DuckDB.
    """
    return con.execute(sql).df()
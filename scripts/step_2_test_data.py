"""
scripts/test_db.py
Ad-hoc script to test SQL queries against the local DuckDB Parquet views.
"""
import sys
from pathlib import Path

# Add project root directory to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.db import get_db_connection, execute_query

def get_direct_parquet():
    print("🔌 Initializing in-memory DuckDB connection...")
    con = get_db_connection()

    #Query your Parquet files directly without importing them first
    con.sql("SELECT * FROM 'data/tracks.parquet' LIMIT 5").show()
    con.sql("SELECT * FROM 'data/audio_features.parquet' LIMIT 5").show()

def get_tracks_features():
    print("🔌 Initializing in-memory DuckDB connection...")
    con = get_db_connection()

    #Query your Parquet files directly without importing them first
    con.sql("SELECT * FROM tracks LIMIT 5").show()

    #Generate a summary of the most popular tracks
    #con.sql("SELECT track_name, MAX(popularity) FROM 'data/tracks.parquet' GROUP BY track_name ORDER BY MAX(popularity) DESC LIMIT 10;").show()

def get_audio_features():
    print("🔌 Initializing in-memory DuckDB connection...")
    con = get_db_connection()

    #Query your Parquet files directly without importing them first
    con.sql("SELECT * FROM audio_features LIMIT 5").show()

def aggregate_by_popularity(by="artist"):
    """
    Aggregates tracks by a specified dimension and popularity metric.
    Safeguards against SQL injection via an allowlist of valid column mappings.
    """
    # 1. Allowlist mapping user inputs to validated SQL column identifiers
    valid_groupings = {
        "artist": ("artists", "popularity"),
        "track": ("track_name", "popularity"),
        "album": ("album_name", "popularity"),
        "genre": ("track_genre", "popularity")
    }

    if by not in valid_groupings:
        valid_options = ", ".join(valid_groupings.keys())
        raise ValueError(f"Invalid criteria '{by}'. Must be one of: {valid_options}")

    group_col, metric_col = valid_groupings[by]

    # 2. Reusable query template using verified identifiers
    query = f"""
        SELECT 
            {group_col}, 
            MAX({metric_col}) AS max_popularity
        FROM tracks
        GROUP BY {group_col}
        ORDER BY max_popularity DESC
        LIMIT 10;
    """

    print("🔌 Initializing in-memory DuckDB connection...")
    with get_db_connection() as con:
        con.sql(query).show()

def test_sql_queries():
    con = get_db_connection()

    sql_query = f"""
    SELECT t.track_name, t.artists, t.popularity, a.valence, a.tempo 
    FROM tracks t JOIN audio_features a ON t.track_id = a.track_id 
    WHERE a.valence < 0.35 AND a.tempo > 120 ORDER BY t.popularity DESC LIMIT 10
    """
    #Query your Parquet files directly without importing them first
    con.sql(sql_query).show()

if __name__ == "__main__":
    #get_direct_parquet()
    #get_tracks_features()
    #get_audio_features()
    #get_top_artists()
    #aggregate_by_popularity(by="track")    
    test_sql_queries()
    
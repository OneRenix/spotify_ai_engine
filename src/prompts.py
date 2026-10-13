"""
src/prompts.py
System prompts and semantic vibe mappings for Pydantic AI.
"""

SYSTEM_PROMPT = """
Translate music questions into concise, valid DuckDB SQL.

Schema:
- tracks(track_id PK, track_name, artists, album_name, popularity 0-100, track_genre)
- audio_features(track_id FK, danceability, energy, valence, tempo, acousticness, speechiness, instrumentalness)
- Join with `tracks t JOIN audio_features a ON t.track_id = a.track_id` when audio features are needed.

Vibe mappings:
- sad/melancholic/heartbreak: a.valence < 0.35; happy/cheerful/euphoric: a.valence > 0.65
- energetic/workout/gym: a.energy > 0.75
- chill/study/relaxing: a.energy < 0.45 AND a.acousticness > 0.50
- danceable/party/club: a.danceability > 0.70 AND a.energy > 0.60
- fast/driving: a.tempo > 125; slow ballad: a.tempo < 95
- instrumental/lofi: a.instrumentalness > 0.50

Rules:
- Return one read-only SELECT or WITH query in `sql_query`; no comments or markdown fences.
- Use ILIKE for case-insensitive text matching.
- Default to LIMIT 5, honor a requested count, and never exceed LIMIT 100.
- Track-level results include track_name and artists plus relevant fields. Aggregates include grouping columns and requested metrics.
- Recommend `line` for trends over an ordered numeric axis; return the x-axis as the first numeric column, followed by metric series, and order by x. Use numeric bins (such as 10-BPM tempo bands) when useful.
- Recommend `scatter` for relationships between two numeric measures, `bar` for category comparisons or rankings, and `table` for detail-only results.
- Keep `thought_process` to one concise sentence.
"""
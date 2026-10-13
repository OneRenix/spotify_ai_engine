"""
scripts/prepare_data.py
Downloads the Spotify dataset and normalizes it into two relational Parquet files:
  1. data/tracks.parquet         -> Metadata (track_id, track_name, artists, popularity, genre)
  2. data/audio_features.parquet -> Acoustics (track_id, danceability, energy, valence, tempo, etc.)
"""
from pathlib import Path
import pandas as pd

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True, parents=True)

HF_DATASET_URL = (
    "https://huggingface.co/datasets/maharshipandya/spotify-tracks-dataset"
    "/resolve/main/dataset.csv"
)

def run():
    print("📥 Fetching raw dataset from Hugging Face...")
    df = pd.read_csv(HF_DATASET_URL).dropna()

    # Deduplicate on track_id so it functions as a clean Primary Key
    df = df.drop_duplicates(subset=["track_id"]).reset_index(drop=True)
    print(f"📊 Processed {len(df):,} unique tracks.")

    # Table 1: Track Metadata
    tracks_df = df[[
        "track_id",
        "track_name",
        "artists",
        "album_name",
        "popularity",
        "track_genre"
    ]].copy()

    # Table 2: Audio Features (The "Vibes" Table)
    audio_df = df[[
        "track_id",
        "danceability",
        "energy",
        "valence",
        "tempo",
        "acousticness",
        "speechiness",
        "instrumentalness"
    ]].copy()

    tracks_path = DATA_DIR / "tracks.parquet"
    audio_path = DATA_DIR / "audio_features.parquet"

    # Export to compressed Parquet
    tracks_df.to_parquet(tracks_path, index=False)
    audio_df.to_parquet(audio_path, index=False)

    print(f"Generated: {tracks_path} ({tracks_path.stat().st_size / 1024:.1f} KB)")
    print(f"Generated: {audio_path} ({audio_path.stat().st_size / 1024:.1f} KB)")

if __name__ == "__main__":
    run()
"""Migrate Mental Library data from SQLite to PostgreSQL.

Reads from the local SQLite file and inserts into the warroom PostgreSQL
database's ml_videos and ml_chunks tables.

Usage:
  python scripts/migrate_mental_library.py

Environment:
  DATABASE_URL — PostgreSQL connection string (falls back to docker-compose default)
  SQLITE_PATH  — path to mental_library.db (defaults to skill data dir)
"""

import os
import sys
import sqlite3
import asyncio

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import asyncpg
from datetime import datetime

SQLITE_PATH = os.getenv(
    "SQLITE_PATH",
    os.path.expanduser("~/.openclaw/workspace/skills/mental-library/backend/data/mental_library.db")
)

# Parse DATABASE_URL for asyncpg (strip +asyncpg if present)
_raw_url = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://friday:friday-brain2-2026@10.0.0.11:5433/knowledge"
)
# asyncpg doesn't understand +asyncpg scheme
DATABASE_URL = _raw_url.replace("postgresql+asyncpg://", "postgresql://").replace("postgresql+psycopg2://", "postgresql://")


async def migrate():
    print(f"SQLite source: {SQLITE_PATH}")
    print(f"PostgreSQL target: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")

    # Read from SQLite
    if not os.path.exists(SQLITE_PATH):
        print(f"ERROR: SQLite file not found at {SQLITE_PATH}")
        sys.exit(1)

    sdb = sqlite3.connect(SQLITE_PATH)
    sdb.row_factory = sqlite3.Row

    videos = sdb.execute("SELECT * FROM videos ORDER BY id").fetchall()
    chunks = sdb.execute("SELECT * FROM chunks ORDER BY id").fetchall()
    print(f"Found {len(videos)} videos, {len(chunks)} chunks in SQLite")

    # Connect to PostgreSQL
    conn = await asyncpg.connect(DATABASE_URL)

    # Create tables
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS ml_videos (
            id SERIAL PRIMARY KEY,
            url TEXT NOT NULL,
            title TEXT DEFAULT '',
            author TEXT DEFAULT '',
            description TEXT DEFAULT '',
            duration INTEGER DEFAULT 0,
            thumbnail_url TEXT DEFAULT '',
            processed_at TIMESTAMPTZ DEFAULT NOW(),
            transcript_path TEXT DEFAULT '',
            audio_path TEXT DEFAULT '',
            topic_tags TEXT DEFAULT '',
            language TEXT DEFAULT 'en',
            chunk_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            error_message TEXT DEFAULT '',
            document_text TEXT DEFAULT ''
        );
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS ml_chunks (
            id SERIAL PRIMARY KEY,
            video_id INTEGER NOT NULL REFERENCES ml_videos(id) ON DELETE CASCADE,
            chunk_index INTEGER DEFAULT 0,
            text TEXT DEFAULT '',
            start_time REAL DEFAULT 0,
            end_time REAL DEFAULT 0,
            embedding_vector_id TEXT DEFAULT '',
            token_count INTEGER DEFAULT 0,
            topic_tags TEXT DEFAULT '',
            confidence_score REAL DEFAULT 0
        );
    """)

    # Check if already migrated
    existing = await conn.fetchval("SELECT count(*) FROM ml_videos")
    if existing > 0:
        print(f"WARNING: ml_videos already has {existing} rows. Skipping migration.")
        print("To re-migrate, run: DELETE FROM ml_chunks; DELETE FROM ml_videos;")
        await conn.close()
        sdb.close()
        return

    # Migrate videos (preserve IDs for foreign key integrity)
    print("Migrating videos...")
    video_count = 0
    for v in videos:
        await conn.execute("""
            INSERT INTO ml_videos (id, url, title, author, description, duration, thumbnail_url,
                processed_at, transcript_path, audio_path, topic_tags, language,
                chunk_count, status, error_message, document_text)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
        """,
            v["id"], v["url"] or "", v["title"] or "", v["author"] or "",
            v["description"] or "", v["duration"] or 0, v["thumbnail_url"] or "",
            datetime.fromisoformat(v["processed_at"]) if v["processed_at"] else datetime.now(),
            v["transcript_path"] or "", v["audio_path"] or "",
            v["topic_tags"] or "", v["language"] or "en",
            v["chunk_count"] or 0, v["status"] or "pending",
            v["error_message"] or "", v["document_text"] or "",
        )
        video_count += 1

    # Update sequence to max id
    if videos:
        max_vid = max(v["id"] for v in videos)
        await conn.execute(f"SELECT setval('ml_videos_id_seq', {max_vid})")

    # Migrate chunks
    print("Migrating chunks...")
    chunk_count = 0
    for c in chunks:
        await conn.execute("""
            INSERT INTO ml_chunks (id, video_id, chunk_index, text, start_time, end_time,
                embedding_vector_id, token_count, topic_tags, confidence_score)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """,
            c["id"], c["video_id"], c["chunk_index"] or 0,
            c["text"] or "", c["start_time"] or 0, c["end_time"] or 0,
            c["embedding_vector_id"] or "", c["token_count"] or 0,
            c["topic_tags"] or "", c["confidence_score"] or 0,
        )
        chunk_count += 1

    # Update sequence to max id
    if chunks:
        max_cid = max(c["id"] for c in chunks)
        await conn.execute(f"SELECT setval('ml_chunks_id_seq', {max_cid})")

    print(f"✅ Migrated {video_count} videos, {chunk_count} chunks to PostgreSQL")

    await conn.close()
    sdb.close()


if __name__ == "__main__":
    asyncio.run(migrate())

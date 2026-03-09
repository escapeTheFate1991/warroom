"""Video transcription pipeline for competitor intelligence.

Downloads competitor video/reel posts, transcribes via Whisper,
stores transcript chunks, deletes the video.

No videos kept on disk — only transcripts with timestamps.
"""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

WHISPER_SOCKET = "/tmp/whisper-transcribe.sock"
WHISPER_TCP_HOST = os.getenv("WHISPER_HOST", "10.0.0.1")
WHISPER_TCP_PORT = int(os.getenv("WHISPER_PORT", "18796"))
COOKIE_PATH = Path(os.getenv("INSTAGRAM_COOKIE_PATH", "/data/instagram_cookies.json"))
# Shared dir with host — Whisper server runs on host and needs to read the files
TEMP_DIR = Path("/tmp/warroom-transcribe")


async def _download_video(shortcode: str, media_url: str = "") -> Optional[Path]:
    """Download an Instagram video/reel to a temp file.
    
    Strategy:
    1. Try yt-dlp with Instagram cookies (handles login walls)
    2. Fallback: direct HTTP download of media_url (CDN URL, may expire)
    
    Returns path to downloaded file or None on failure.
    """
    output_path = TEMP_DIR / f"ig_{shortcode}.mp4"
    
    # Clean up any stale file
    if output_path.exists():
        output_path.unlink()
    
    # Strategy 1: yt-dlp (preferred — handles auth, redirects, formats)
    try:
        cmd = [
            "yt-dlp",
            "--no-warnings",
            "--quiet",
            "-o", str(output_path),
            "--max-filesize", "100M",  # Skip huge files
        ]
        
        # Use cookies if available
        if COOKIE_PATH.exists():
            # Convert JSON cookies to Netscape format for yt-dlp
            netscape_path = TEMP_DIR / f"ig_cookies_{shortcode}.txt"
            _convert_cookies_to_netscape(COOKIE_PATH, netscape_path)
            cmd.extend(["--cookies", str(netscape_path)])
        
        # Try reel URL first, then post URL
        reel_url = f"https://www.instagram.com/reel/{shortcode}/"
        post_url = f"https://www.instagram.com/p/{shortcode}/"
        
        for url in [reel_url, post_url]:
            result = await asyncio.to_thread(
                subprocess.run,
                cmd + [url],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if output_path.exists() and output_path.stat().st_size > 0:
                logger.info("Downloaded %s via yt-dlp (%d KB)", shortcode, output_path.stat().st_size // 1024)
                # Clean up netscape cookies
                netscape_path = TEMP_DIR / f"ig_cookies_{shortcode}.txt"
                if netscape_path.exists():
                    netscape_path.unlink()
                return output_path
        
        logger.debug("yt-dlp failed for %s: %s", shortcode, result.stderr[:200] if result.stderr else "no output")
    except FileNotFoundError:
        logger.debug("yt-dlp not installed — trying direct download")
    except subprocess.TimeoutExpired:
        logger.warning("yt-dlp timed out for %s", shortcode)
    except Exception as e:
        logger.debug("yt-dlp error for %s: %s", shortcode, e)
    
    # Strategy 2: Direct HTTP download (CDN URL may be expired)
    if media_url:
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
                resp = await client.get(media_url)
                if resp.status_code == 200 and len(resp.content) > 1000:
                    output_path.write_bytes(resp.content)
                    logger.info("Downloaded %s via direct URL (%d KB)", shortcode, len(resp.content) // 1024)
                    return output_path
                else:
                    logger.debug("Direct download failed for %s: status=%d size=%d", shortcode, resp.status_code, len(resp.content))
        except Exception as e:
            logger.debug("Direct download error for %s: %s", shortcode, e)
    
    return None


def _convert_cookies_to_netscape(json_path: Path, out_path: Path):
    """Convert Playwright JSON cookies to Netscape format for yt-dlp."""
    try:
        cookies = json.loads(json_path.read_text())
        lines = ["# Netscape HTTP Cookie File"]
        for c in cookies:
            domain = c.get("domain", "")
            if not domain:
                continue
            flag = "TRUE" if domain.startswith(".") else "FALSE"
            path = c.get("path", "/")
            secure = "TRUE" if c.get("secure", False) else "FALSE"
            expires = str(int(c.get("expires", 0)))
            name = c.get("name", "")
            value = c.get("value", "")
            lines.append(f"{domain}\t{flag}\t{path}\t{secure}\t{expires}\t{name}\t{value}")
        out_path.write_text("\n".join(lines))
    except Exception as e:
        logger.warning("Cookie conversion failed: %s", e)


async def _transcribe_audio(file_path: Path) -> Optional[List[Dict]]:
    """Transcribe audio/video file using Whisper server.
    
    Tries TCP connection to Whisper server first.
    Returns list of segments: [{start: float, end: float, text: str}]
    """
    if not file_path.exists():
        return None
    
    # Try TCP Whisper server (runs on host, reads files from shared /tmp/warroom-transcribe)
    try:
        # Send plain file path — Whisper server expects raw path string, not JSON
        payload = str(file_path).encode()
        
        def _tcp_transcribe():
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(120)  # Videos can take a while
            sock.connect((WHISPER_TCP_HOST, WHISPER_TCP_PORT))
            sock.sendall(payload + b"\n")
            
            chunks = []
            while True:
                data = sock.recv(65536)
                if not data:
                    break
                chunks.append(data)
            sock.close()
            return b"".join(chunks)
        
        raw = await asyncio.to_thread(_tcp_transcribe)
        result = json.loads(raw)
        
        if "segments" in result:
            segments = [
                {
                    "start": round(s["start"], 1),
                    "end": round(s["end"], 1),
                    "text": s["text"].strip(),
                }
                for s in result["segments"]
                if s.get("text", "").strip()
            ]
            logger.info("Transcribed %s: %d segments", file_path.name, len(segments))
            return segments
        elif "text" in result:
            # Flat text response — create single segment
            return [{"start": 0.0, "end": 0.0, "text": result["text"].strip()}]
        else:
            logger.warning("Unexpected Whisper response: %s", str(result)[:200])
            return None
            
    except ConnectionRefusedError:
        logger.warning("Whisper server not running on %s:%d", WHISPER_TCP_HOST, WHISPER_TCP_PORT)
        return None
    except Exception as e:
        logger.error("Transcription error for %s: %s", file_path.name, e)
        return None


async def transcribe_competitor_videos(
    db: AsyncSession,
    competitor_id: int,
    limit: int = 10,
) -> Dict:
    """Find video/reel posts without transcripts, download, transcribe, delete.
    
    Returns summary: {processed: int, transcribed: int, failed: int, errors: [str]}
    """
    result = await db.execute(
        text("""
            SELECT id, shortcode, media_url, media_type
            FROM crm.competitor_posts
            WHERE competitor_id = :cid
              AND media_type IN ('video', 'reel')
              AND transcript IS NULL
              AND shortcode IS NOT NULL
            ORDER BY engagement_score DESC
            LIMIT :lim
        """),
        {"cid": competitor_id, "lim": limit},
    )
    posts = result.fetchall()
    
    if not posts:
        return {"processed": 0, "transcribed": 0, "failed": 0, "errors": []}
    
    stats = {"processed": 0, "transcribed": 0, "failed": 0, "errors": []}
    
    for post in posts:
        post_id, shortcode, media_url, media_type = post
        stats["processed"] += 1
        
        logger.info("Transcribing %s (%s)...", shortcode, media_type)
        
        # Download
        video_path = await _download_video(shortcode, media_url or "")
        if not video_path:
            stats["failed"] += 1
            stats["errors"].append(f"{shortcode}: download failed")
            continue
        
        try:
            # Transcribe
            segments = await _transcribe_audio(video_path)
            
            if segments:
                # Store transcript
                await db.execute(
                    text("UPDATE crm.competitor_posts SET transcript = :t WHERE id = :id"),
                    {"t": json.dumps(segments), "id": post_id},
                )
                await db.commit()
                stats["transcribed"] += 1
                logger.info("✅ %s: %d segments stored", shortcode, len(segments))
            else:
                stats["failed"] += 1
                stats["errors"].append(f"{shortcode}: transcription failed")
        finally:
            # Always delete the video
            if video_path.exists():
                video_path.unlink()
                logger.debug("Deleted temp video: %s", video_path)
    
    return stats


async def transcribe_competitor_videos_batch(
    db: AsyncSession,
    competitor_ids: List[int],
    limit_per_competitor: int = 5,
) -> Dict:
    """Batch transcribe videos across multiple competitors.
    
    Returns: {transcribed: int, failed: int, total_processed: int}
    """
    totals = {"transcribed": 0, "failed": 0, "total_processed": 0}
    
    for cid in competitor_ids:
        try:
            result = await transcribe_competitor_videos(db, cid, limit=limit_per_competitor)
            totals["transcribed"] += result.get("transcribed", 0)
            totals["failed"] += result.get("failed", 0)
            totals["total_processed"] += result.get("processed", 0)
        except Exception as e:
            logger.warning("Transcription batch failed for competitor %s: %s", cid, e)
    
    return totals

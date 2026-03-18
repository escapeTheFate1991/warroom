"""Download Instagram CDN media to Garage S3 for top competitor posts."""
import asyncio
import os
import sys
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DB_URL = os.environ.get(
    "LEADGEN_DB_URL",
    "postgresql+asyncpg://friday:friday-brain2-2026@10.0.0.11:5433/knowledge",
)

engine = create_async_engine(DB_URL)

LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 50


async def download_media_background(posts, dl_thumbnails, dl_videos):
    """Download media from Instagram CDN and store in Garage S3."""
    import httpx
    import boto3

    s3 = boto3.client(
        "s3",
        endpoint_url=os.environ.get("GARAGE_ENDPOINT", "http://10.0.0.11:3900"),
        aws_access_key_id=os.environ.get("GARAGE_ACCESS_KEY", "GK6d3eb1c7bc06e00d77b8f89c"),
        aws_secret_access_key=os.environ.get("GARAGE_SECRET_KEY", "370b99ef00dbfee300e3d73b69b217a7f5633935b02b86ee37f5691aacdf602b"),
        region_name=os.environ.get("GARAGE_REGION", "ai-local"),
    )
    bucket = "digital-copies"
    s3_base = os.environ.get("GARAGE_ENDPOINT", "http://10.0.0.11:3900")

    success = 0
    failed = 0

    for i, post in enumerate(posts):
        post_id = post["id"]
        updates = {}

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            if dl_thumbnails and post.get("thumbnail_url") and "instagram" in (post["thumbnail_url"] or ""):
                try:
                    resp = await client.get(post["thumbnail_url"])
                    if resp.status_code == 200 and len(resp.content) > 500:
                        ct = resp.headers.get("content-type", "image/jpeg")
                        ext = "jpg"
                        if "png" in ct: ext = "png"
                        elif "webp" in ct: ext = "webp"
                        s3_key = f"competitor-media/{post_id}/thumb.{ext}"
                        s3.put_object(Bucket=bucket, Key=s3_key, Body=resp.content, ContentType=ct)
                        updates["thumbnail_url"] = f"{s3_base}/{bucket}/{s3_key}"
                        logging.info(f"[{i+1}/{len(posts)}] Thumb OK post={post_id} ({len(resp.content)//1024}KB)")
                    else:
                        logging.warning(f"[{i+1}/{len(posts)}] Thumb SKIP post={post_id} status={resp.status_code} size={len(resp.content)}")
                except Exception as e:
                    logging.warning(f"[{i+1}/{len(posts)}] Thumb FAIL post={post_id}: {e}")

            if dl_videos and post.get("media_url") and "instagram" in (post["media_url"] or ""):
                try:
                    resp = await client.get(post["media_url"])
                    if resp.status_code == 200 and len(resp.content) > 10000:
                        s3_key = f"competitor-media/{post_id}/video.mp4"
                        s3.put_object(Bucket=bucket, Key=s3_key, Body=resp.content, ContentType="video/mp4")
                        updates["media_url"] = f"{s3_base}/{bucket}/{s3_key}"
                        logging.info(f"[{i+1}/{len(posts)}] Video OK post={post_id} ({len(resp.content)//1024}KB)")
                    else:
                        logging.warning(f"[{i+1}/{len(posts)}] Video SKIP post={post_id} status={resp.status_code}")
                except Exception as e:
                    logging.warning(f"[{i+1}/{len(posts)}] Video FAIL post={post_id}: {e}")

        if updates:
            try:
                set_parts = []
                params = {"pid": post_id}
                if "thumbnail_url" in updates:
                    set_parts.append("thumbnail_url = :thumb")
                    params["thumb"] = updates["thumbnail_url"]
                if "media_url" in updates:
                    set_parts.append("media_url = :media")
                    params["media"] = updates["media_url"]
                if set_parts:
                    async with engine.begin() as conn:
                        await conn.execute(
                            text(f"UPDATE crm.competitor_posts SET {', '.join(set_parts)} WHERE id = :pid"),
                            params,
                        )
                    success += 1
            except Exception as e:
                logging.error(f"DB update failed for post {post_id}: {e}")
                failed += 1

        await asyncio.sleep(0.3)

    logging.info(f"DONE: {success} updated, {failed} failed out of {len(posts)}")


async def main():
    async with engine.connect() as conn:
        r = await conn.execute(
            text("""
                SELECT cp.id, cp.thumbnail_url, cp.media_url, cp.shortcode, c.handle
                FROM crm.competitor_posts cp
                JOIN crm.competitors c ON c.id = cp.competitor_id
                WHERE cp.media_type IN ('video', 'reel', 'clip')
                  AND (cp.thumbnail_url LIKE '%instagram%' OR cp.media_url LIKE '%instagram%')
                ORDER BY cp.engagement_score DESC
                LIMIT :lim
            """),
            {"lim": LIMIT},
        )
        posts = [dict(row._mapping) for row in r]
        logging.info(f"Found {len(posts)} posts to download (limit={LIMIT})")

    await download_media_background(posts, True, True)


if __name__ == "__main__":
    asyncio.run(main())

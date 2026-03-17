"""Rendering Worker - Background worker for processing video projects.

Processes video_projects queue with mixed scene types:
- remotion: Template-based renders (ffmpeg placeholders for Phase 1)
- ai_generated: AI video generation via Veo/Nano Banana APIs
- image: Static image frames with ffmpeg
- stock: Stock footage processing

Flow:
1. Poll crm.video_projects for status = 'queued'
2. Process scenes in order
3. Stitch final video with ffmpeg
4. Mix audio if provided
5. Update project status: queued → rendering → stitching → complete
"""

import os
import asyncio
import logging
import uuid
import json
import subprocess
import tempfile
import shutil
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crm_db import get_crm_db

logger = logging.getLogger(__name__)

# Configuration
UPLOADS_DIR = "/app/uploads"
SCENES_DIR = f"{UPLOADS_DIR}/scenes"
VIDEOS_DIR = f"{UPLOADS_DIR}/videos"
VOICEOVERS_DIR = f"{UPLOADS_DIR}/voiceovers"

# Ensure directories exist
for dir_path in [UPLOADS_DIR, SCENES_DIR, VIDEOS_DIR, VOICEOVERS_DIR]:
    Path(dir_path).mkdir(parents=True, exist_ok=True)


class RenderWorker:
    """Background worker for processing video projects."""

    def __init__(self):
        self.running = False

    async def start(self):
        """Start the worker loop."""
        self.running = True
        logger.info("Render worker started")
        
        while self.running:
            try:
                await self.process_queued_projects()
                await asyncio.sleep(5)  # Check every 5 seconds
            except Exception as e:
                logger.error(f"Worker error: {e}")
                await asyncio.sleep(10)  # Wait longer on error

    async def stop(self):
        """Stop the worker loop."""
        self.running = False
        logger.info("Render worker stopped")

    async def process_queued_projects(self):
        """Check for queued projects and process them."""
        async with get_crm_db() as db:
            # Get next queued project
            result = await db.execute(text("""
                SELECT id, org_id, user_id, title, scenes, audio, output_config
                FROM crm.video_projects 
                WHERE status = 'queued'
                ORDER BY created_at ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            """))
            
            project = result.mappings().first()
            if not project:
                return  # No queued projects
            
            project_id = project["id"]
            logger.info(f"Processing project {project_id}: {project['title']}")
            
            try:
                # Update status to rendering
                await self.update_project_status(db, project_id, "rendering")
                
                # Process all scenes
                scene_paths = await self.process_scenes(dict(project))
                
                # Update status to stitching
                await self.update_project_status(db, project_id, "stitching")
                
                # Stitch scenes together
                final_video_path = await self.stitch_scenes(
                    scene_paths, 
                    project_id,
                    project.get("audio")
                )
                
                # Update status to complete with output URL
                await db.execute(text("""
                    UPDATE crm.video_projects 
                    SET status = 'complete', output_url = :url, completed_at = NOW()
                    WHERE id = :id
                """), {"id": project_id, "url": final_video_path})
                await db.commit()
                
                logger.info(f"Project {project_id} completed: {final_video_path}")
                
            except Exception as e:
                logger.error(f"Project {project_id} failed: {e}")
                await self.update_project_status(db, project_id, "error", str(e))

    async def update_project_status(self, db: AsyncSession, project_id: int, status: str, error: str = None):
        """Update project status in database."""
        params = {"id": project_id, "status": status}
        query = "UPDATE crm.video_projects SET status = :status"
        
        if error:
            query += ", error = :error"
            params["error"] = error
            
        await db.execute(text(query + " WHERE id = :id"), params)
        await db.commit()

    async def process_scenes(self, project: Dict[str, Any]) -> List[str]:
        """Process all scenes and return list of rendered video paths."""
        scenes = project["scenes"]
        if isinstance(scenes, str):
            scenes = json.loads(scenes)
        
        scene_paths = []
        
        for i, scene in enumerate(scenes):
            scene_id = f"scene_{project['id']}_{i}"
            scene_path = f"{SCENES_DIR}/{scene_id}.mp4"
            
            try:
                if scene["type"] == "remotion":
                    await self.render_remotion_scene(scene, scene_path)
                elif scene["type"] == "ai_generated":
                    await self.render_ai_scene(scene, scene_path)
                elif scene["type"] == "image":
                    await self.render_image_scene(scene, scene_path)
                else:
                    logger.warning(f"Unknown scene type: {scene['type']}")
                    continue
                    
                scene_paths.append(scene_path)
                logger.info(f"Rendered scene {i+1}/{len(scenes)}: {scene_path}")
                
            except Exception as e:
                logger.error(f"Failed to render scene {i}: {e}")
                # Create error placeholder scene
                await self.render_error_scene(scene_path, str(e))
                scene_paths.append(scene_path)
        
        return scene_paths

    async def render_remotion_scene(self, scene: Dict[str, Any], output_path: str):
        """Render a Remotion scene using ffmpeg placeholders.
        
        For Phase 1, we use ffmpeg to generate template-based scenes.
        Phase 2 will integrate with actual Remotion CLI rendering.
        """
        template = scene.get("template", "text_overlay")
        props = scene.get("props", {})
        duration = scene.get("duration_seconds", 3)
        
        if template == "text_overlay":
            text = props.get("text", "Sample Text")
            # Clean text for ffmpeg (escape quotes and special chars)
            clean_text = text.replace("'", "\\'").replace('"', '\\"')[:50]
            
            cmd = [
                "ffmpeg", "-y", 
                "-f", "lavfi", "-i", f"color=c=#06060a:s=1080x1920:d={duration}",
                "-vf", f"drawtext=text='{clean_text}':fontsize=64:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2:alpha='if(lt(t,0.5),t*2,1)'",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                output_path
            ]
            
        elif template == "cta":
            text = props.get("text", "Link in bio")
            clean_text = text.replace("'", "\\'").replace('"', '\\"')[:30]
            
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"color=c=#0d0d14:s=1080x1920:d={duration}",
                "-vf", f"drawtext=text='{clean_text}':fontsize=80:fontcolor=#7c3aed:x=(w-text_w)/2:y=(h-text_h)/2",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                output_path
            ]
            
        elif template == "diagram":
            bullets = props.get("bullets", ["Point 1", "Point 2", "Point 3"])
            text = "\\n".join([f"• {bullet}" for bullet in bullets[:3]])
            clean_text = text.replace("'", "\\'").replace('"', '\\"')
            
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"color=c=#1a1a2e:s=1080x1920:d={duration}",
                "-vf", f"drawtext=text='{clean_text}':fontsize=48:fontcolor=#e2e8f0:x=50:y=(h-text_h)/2",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                output_path
            ]
            
        elif template == "split_screen":
            left_text = props.get("left_text", "Before")
            right_text = props.get("right_text", "After")
            
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"color=c=#ef4444:s=540x1920:d={duration}",
                "-f", "lavfi", "-i", f"color=c=#22c55e:s=540x1920:d={duration}",
                "-filter_complex", 
                f"[0]drawtext=text='{left_text}':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2[left];"
                f"[1]drawtext=text='{right_text}':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2[right];"
                f"[left][right]hstack",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                output_path
            ]
        else:
            # Default text overlay
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"color=c=#374151:s=1080x1920:d={duration}",
                "-vf", f"drawtext=text='Template: {template}':fontsize=64:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                output_path
            ]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            raise Exception(f"FFmpeg render failed: {stderr.decode()}")

    async def render_ai_scene(self, scene: Dict[str, Any], output_path: str):
        """Render AI-generated scene.
        
        For Phase 1, creates placeholder with prompt text.
        Phase 2 will integrate with Veo 3.1 and Nano Banana APIs.
        """
        provider = scene.get("provider", "veo")
        prompt = scene.get("prompt", "AI generated scene")
        duration = scene.get("duration_seconds", 5)
        
        # Clean prompt for display
        display_prompt = prompt[:50] + "..." if len(prompt) > 50 else prompt
        clean_prompt = display_prompt.replace("'", "\\'").replace('"', '\\"')
        
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=#1a1a2e:s=1080x1920:d={duration}",
            "-vf", f"drawtext=text='[AI Scene: {provider}]\\n\\n{clean_prompt}':fontsize=36:fontcolor=#94a3b8:x=(w-text_w)/2:y=(h-text_h)/2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            output_path
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            raise Exception(f"AI scene render failed: {stderr.decode()}")

    async def render_image_scene(self, scene: Dict[str, Any], output_path: str):
        """Render static image as video frame."""
        image_url = scene.get("url", "")
        duration = scene.get("duration_seconds", 3)
        
        if not image_url:
            # Create placeholder if no image URL
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"color=c=#64748b:s=1080x1920:d={duration}",
                "-vf", "drawtext=text='[Image Scene]':fontsize=64:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                output_path
            ]
        else:
            # Download and process image (simplified for Phase 1)
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"color=c=#64748b:s=1080x1920:d={duration}",
                "-vf", f"drawtext=text='Image: {image_url[:30]}...':fontsize=36:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                output_path
            ]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            raise Exception(f"Image scene render failed: {stderr.decode()}")

    async def render_error_scene(self, output_path: str, error_msg: str):
        """Render error placeholder scene."""
        clean_error = error_msg.replace("'", "\\'").replace('"', '\\"')[:100]
        
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=#dc2626:s=1080x1920:d=3",
            "-vf", f"drawtext=text='Render Error\\n{clean_error}':fontsize=32:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            output_path
        ]
        
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()

    async def stitch_scenes(self, scene_paths: List[str], project_id: int, audio_config: Optional[Dict] = None) -> str:
        """Concatenate rendered scenes and optionally mix audio."""
        if not scene_paths:
            raise Exception("No scenes to stitch")
        
        # Create concat file
        concat_file = f"{SCENES_DIR}/concat_{project_id}.txt"
        with open(concat_file, "w") as f:
            for path in scene_paths:
                f.write(f"file '{path}'\n")
        
        # Output path
        output_path = f"{VIDEOS_DIR}/project_{project_id}.mp4"
        
        try:
            # Concatenate videos
            concat_cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0", "-i", concat_file,
                "-c", "copy",
                output_path
            ]
            
            proc = await asyncio.create_subprocess_exec(
                *concat_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                raise Exception(f"Video concat failed: {stderr.decode()}")
            
            # Mix audio if provided
            if audio_config and isinstance(audio_config, dict):
                voiceover_url = audio_config.get("voiceover_url")
                if voiceover_url:
                    final_output = f"{VIDEOS_DIR}/project_{project_id}_final.mp4"
                    await self.mix_audio(output_path, voiceover_url, final_output)
                    output_path = final_output
            
            return output_path
            
        finally:
            # Clean up concat file
            if os.path.exists(concat_file):
                os.remove(concat_file)

    async def mix_audio(self, video_path: str, audio_url: str, output_path: str):
        """Mix audio track with video."""
        # For Phase 1, assume audio_url is a local file path
        # Phase 2 will handle URL downloads
        
        if os.path.exists(audio_url):
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-i", audio_url,
                "-c:v", "copy",
                "-c:a", "aac",
                "-map", "0:v:0",
                "-map", "1:a:0",
                output_path
            ]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                logger.warning(f"Audio mixing failed: {stderr.decode()}")
                # Fall back to video without audio
                shutil.copy2(video_path, output_path)


# Global worker instance
worker = RenderWorker()


async def start_render_worker():
    """Start the background render worker."""
    await worker.start()


def stop_render_worker():
    """Stop the background render worker."""
    asyncio.create_task(worker.stop())


async def process_project(project_id: int):
    """Process a specific project (can be called directly)."""
    async with get_crm_db() as db:
        result = await db.execute(text("""
            SELECT id, org_id, user_id, title, scenes, audio, output_config
            FROM crm.video_projects 
            WHERE id = :id
        """), {"id": project_id})
        
        project = result.mappings().first()
        if not project:
            raise Exception(f"Project {project_id} not found")
        
        # Update status to rendering
        await worker.update_project_status(db, project_id, "rendering")
        
        # Process scenes
        scene_paths = await worker.process_scenes(dict(project))
        
        # Update status to stitching
        await worker.update_project_status(db, project_id, "stitching")
        
        # Stitch scenes
        final_video_path = await worker.stitch_scenes(
            scene_paths, 
            project_id,
            project.get("audio")
        )
        
        # Update status to complete
        await db.execute(text("""
            UPDATE crm.video_projects 
            SET status = 'complete', output_url = :url, completed_at = NOW()
            WHERE id = :id
        """), {"id": project_id, "url": final_video_path})
        await db.commit()
        
        return final_video_path
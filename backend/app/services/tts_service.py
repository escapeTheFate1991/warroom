"""TTS Service Integration - Chatterbox TTS client for voiceover generation."""

import os
import uuid
import logging
import httpx
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Configuration
CHATTERBOX_URL = os.getenv("CHATTERBOX_URL", "http://warroom-chatterbox:8400")
UPLOADS_DIR = "/app/uploads"
VOICEOVERS_DIR = f"{UPLOADS_DIR}/voiceovers"

# Ensure directory exists
os.makedirs(VOICEOVERS_DIR, exist_ok=True)


class TTSService:
    """Client for Chatterbox TTS service."""
    
    def __init__(self, base_url: str = CHATTERBOX_URL):
        self.base_url = base_url.rstrip('/')
    
    async def generate_voiceover(
        self, 
        text: str, 
        voice_id: str = None, 
        voice_reference_path: str = None,
        pace: float = 1.0,
        exaggeration: float = 0.5
    ) -> str:
        """Generate voiceover using Chatterbox TTS.
        
        Args:
            text: Text to convert to speech
            voice_id: ID of previously saved voice
            voice_reference_path: Path to audio file for voice cloning
            pace: Speech pace (0.5-2.0)
            exaggeration: Voice exaggeration level (0.0-1.0)
        
        Returns:
            Path to the generated audio file
        """
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                # Prepare form data
                data = {
                    "text": text,
                    "pace": pace,
                    "exaggeration": exaggeration
                }
                
                files = {}
                
                # Add voice reference or speaker ID
                if voice_reference_path and os.path.exists(voice_reference_path):
                    files["voice_reference"] = open(voice_reference_path, "rb")
                elif voice_id:
                    data["speaker_id"] = voice_id
                
                # Make request to TTS service
                response = await client.post(
                    f"{self.base_url}/tts/generate",
                    data=data,
                    files=files
                )
                
                # Clean up opened files
                for file_obj in files.values():
                    if hasattr(file_obj, 'close'):
                        file_obj.close()
                
                if response.status_code != 200:
                    raise Exception(f"TTS service error: {response.status_code} - {response.text}")
                
                # Save response audio
                output_filename = f"voiceover_{uuid.uuid4().hex[:12]}.wav"
                output_path = f"{VOICEOVERS_DIR}/{output_filename}"
                
                with open(output_path, "wb") as f:
                    f.write(response.content)
                
                logger.info(f"Generated voiceover: {output_path}")
                return output_path
                
        except httpx.TimeoutException:
            raise Exception("TTS service request timed out")
        except httpx.ConnectError:
            raise Exception("Could not connect to TTS service")
        except Exception as e:
            logger.error(f"TTS generation failed: {e}")
            raise
    
    async def clone_voice(self, name: str, audio_reference_path: str) -> str:
        """Clone a voice and save it for reuse.
        
        Args:
            name: Friendly name for the voice
            audio_reference_path: Path to audio file containing the voice to clone
        
        Returns:
            speaker_id for future use
        """
        if not os.path.exists(audio_reference_path):
            raise FileNotFoundError(f"Audio reference file not found: {audio_reference_path}")
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                data = {"name": name}
                files = {"audio_reference": open(audio_reference_path, "rb")}
                
                response = await client.post(
                    f"{self.base_url}/tts/clone-voice",
                    data=data,
                    files=files
                )
                
                # Clean up opened file
                files["audio_reference"].close()
                
                if response.status_code != 200:
                    raise Exception(f"Voice cloning error: {response.status_code} - {response.text}")
                
                result = response.json()
                speaker_id = result.get("speaker_id")
                
                logger.info(f"Voice cloned successfully: {speaker_id} ({name})")
                return speaker_id
                
        except httpx.TimeoutException:
            raise Exception("Voice cloning request timed out")
        except httpx.ConnectError:
            raise Exception("Could not connect to TTS service")
        except Exception as e:
            logger.error(f"Voice cloning failed: {e}")
            raise
    
    async def list_voices(self) -> Dict[str, Any]:
        """List available cloned voices."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(f"{self.base_url}/tts/voices")
                
                if response.status_code != 200:
                    raise Exception(f"Failed to list voices: {response.status_code}")
                
                return response.json()
                
        except httpx.TimeoutException:
            raise Exception("Request to list voices timed out")
        except httpx.ConnectError:
            raise Exception("Could not connect to TTS service")
        except Exception as e:
            logger.error(f"Failed to list voices: {e}")
            raise
    
    async def delete_voice(self, speaker_id: str) -> bool:
        """Delete a cloned voice.
        
        Args:
            speaker_id: ID of the voice to delete
        
        Returns:
            True if deletion was successful
        """
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.delete(f"{self.base_url}/tts/voices/{speaker_id}")
                
                if response.status_code == 404:
                    return False  # Voice not found
                elif response.status_code != 200:
                    raise Exception(f"Failed to delete voice: {response.status_code}")
                
                logger.info(f"Voice deleted: {speaker_id}")
                return True
                
        except httpx.TimeoutException:
            raise Exception("Request to delete voice timed out")
        except httpx.ConnectError:
            raise Exception("Could not connect to TTS service")
        except Exception as e:
            logger.error(f"Failed to delete voice {speaker_id}: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if TTS service is healthy."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.base_url}/health")
                
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"status": "error", "code": response.status_code}
                    
        except Exception as e:
            return {"status": "error", "message": str(e)}


# Global TTS service instance
tts_service = TTSService()


# Convenience functions for backward compatibility
async def generate_voiceover(
    text: str, 
    voice_id: str = None, 
    voice_reference_path: str = None
) -> str:
    """Generate voiceover using the global TTS service."""
    return await tts_service.generate_voiceover(text, voice_id, voice_reference_path)


async def clone_voice(name: str, audio_reference_path: str) -> str:
    """Clone voice using the global TTS service."""
    return await tts_service.clone_voice(name, audio_reference_path)
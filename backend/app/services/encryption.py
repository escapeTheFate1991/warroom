"""Encryption utilities for secure credential storage."""
import os
import base64
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""
    
    def __init__(self):
        self._fernet = None
        self._setup_encryption()
    
    def _setup_encryption(self):
        """Initialize Fernet encryption using a key derived from environment."""
        # Get encryption key from environment or generate one
        encryption_key = os.getenv("WARROOM_ENCRYPTION_KEY")
        if not encryption_key:
            # For development, generate a key from a default password
            # In production, this should be set via environment variable
            password = os.getenv("WARROOM_ENCRYPTION_PASSWORD", "default-dev-password").encode()
            salt = b"warroom-salt-2024"  # Fixed salt for consistency
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
        else:
            # Use provided key
            key = encryption_key.encode()
            if len(key) != 44:  # Fernet key length
                # Derive key from provided string
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=b"warroom-key-salt",
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(key))
        
        self._fernet = Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string and return base64-encoded result."""
        if not plaintext:
            return ""
        
        encrypted_bytes = self._fernet.encrypt(plaintext.encode('utf-8'))
        return base64.urlsafe_b64encode(encrypted_bytes).decode('utf-8')
    
    def decrypt(self, encrypted_text: str) -> Optional[str]:
        """Decrypt a base64-encoded encrypted string."""
        if not encrypted_text:
            return None
        
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_text.encode('utf-8'))
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            # Log the error in production
            print(f"Decryption error: {e}")
            return None
    
    def is_encrypted(self, text: str) -> bool:
        """Check if a text string appears to be encrypted."""
        if not text:
            return False
        
        # Simple heuristic: encrypted text should be base64 and longer than original
        try:
            base64.urlsafe_b64decode(text.encode('utf-8'))
            return len(text) > 20  # Minimum length for encrypted data
        except:
            return False


# Global encryption service instance
_encryption_service = None


def get_encryption_service() -> EncryptionService:
    """Get the global encryption service instance."""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


def encrypt_value(value: str) -> str:
    """Convenience function to encrypt a value."""
    return get_encryption_service().encrypt(value)


def decrypt_value(encrypted_value: str) -> Optional[str]:
    """Convenience function to decrypt a value."""
    return get_encryption_service().decrypt(encrypted_value)
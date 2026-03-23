"""
Garage S3 utilities for War Room
"""
import os
import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Garage S3 configuration
GARAGE_CONFIG = {
    "endpoint_url": "http://10.0.0.11:3900",
    "access_key_id": "GK891b44277c4af3277a8a3e93", 
    "secret_access_key": "d2c208430df9781a66562617379fa2d8470fb1aebcd011096475fa0a3b47c8b9",
    "region_name": "ai-local",
    "bucket": "media"
}

def create_s3_client():
    """Create S3 client for Garage."""
    return boto3.client(
        's3',
        endpoint_url=GARAGE_CONFIG["endpoint_url"],
        aws_access_key_id=GARAGE_CONFIG["access_key_id"],
        aws_secret_access_key=GARAGE_CONFIG["secret_access_key"],
        region_name=GARAGE_CONFIG["region_name"],
    )

def generate_signed_url(s3_key: str, expiration: int = 3600) -> str:
    """Generate a signed URL for accessing S3 objects.
    
    Args:
        s3_key: The S3 object key (path)
        expiration: URL expiration in seconds (default 1 hour)
        
    Returns:
        Signed URL string
    """
    try:
        s3_client = create_s3_client()
        
        response = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': GARAGE_CONFIG["bucket"],
                'Key': s3_key
            },
            ExpiresIn=expiration
        )
        
        return response
        
    except ClientError as e:
        logger.error(f"Error generating signed URL for {s3_key}: {e}")
        return None

def upload_file(file_path: str, s3_key: str, content_type: str = None) -> str:
    """Upload file to S3 and return public URL.
    
    Args:
        file_path: Local file path to upload
        s3_key: S3 object key (destination path)
        content_type: MIME type (optional)
        
    Returns:
        Public S3 URL
    """
    try:
        s3_client = create_s3_client()
        
        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type
        
        s3_client.upload_file(
            file_path, 
            GARAGE_CONFIG["bucket"], 
            s3_key,
            ExtraArgs=extra_args
        )
        
        # Return signed URL since public access isn't available
        return generate_signed_url(s3_key, expiration=86400)  # 24 hour expiration
        
    except ClientError as e:
        logger.error(f"Error uploading {file_path} to S3: {e}")
        raise

def get_public_url(s3_key: str) -> str:
    """Get public URL for S3 object (returns signed URL since public access disabled).
    
    Args:
        s3_key: S3 object key
        
    Returns:
        Signed URL with 24-hour expiration
    """
    return generate_signed_url(s3_key, expiration=86400)

def extract_s3_key_from_url(url: str) -> str:
    """Extract S3 key from a Garage S3 URL.
    
    Args:
        url: S3 URL like http://10.0.0.11:3900/media/path/to/file.jpg
        
    Returns:
        S3 key like path/to/file.jpg
    """
    if not url or GARAGE_CONFIG["endpoint_url"] not in url:
        return None
        
    # Remove endpoint and bucket from URL
    bucket_prefix = f"{GARAGE_CONFIG['endpoint_url']}/{GARAGE_CONFIG['bucket']}/"
    
    if url.startswith(bucket_prefix):
        return url[len(bucket_prefix):]
    
    return None
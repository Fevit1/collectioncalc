"""
R2 Storage Module for CollectionCalc
Handles image uploads to Cloudflare R2 (S3-compatible).

Supports:
- Whatnot sale images (single front image)
- B4Cert submissions (front, back, spine, centerfold)
"""

import os
import base64
import uuid
from datetime import datetime

# boto3 is the AWS SDK, works with R2's S3-compatible API
try:
    import boto3
    from botocore.config import Config
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False
    print("boto3 not installed - R2 uploads disabled")

# R2 Configuration from environment
R2_ACCESS_KEY_ID = os.environ.get('R2_ACCESS_KEY_ID')
R2_SECRET_ACCESS_KEY = os.environ.get('R2_SECRET_ACCESS_KEY')
R2_ACCOUNT_ID = os.environ.get('R2_ACCOUNT_ID')
R2_BUCKET_NAME = os.environ.get('R2_BUCKET_NAME', 'collectioncalc-images')
R2_ENDPOINT = os.environ.get('R2_ENDPOINT') or f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

# Public URL for serving images (we'll set up a custom domain or use R2.dev)
R2_PUBLIC_URL = os.environ.get('R2_PUBLIC_URL', f"https://pub-{R2_ACCOUNT_ID}.r2.dev")


def get_r2_client():
    """Get an S3 client configured for Cloudflare R2."""
    if not HAS_BOTO3:
        return None
    
    if not all([R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ACCOUNT_ID]):
        print("R2 credentials not configured")
        return None
    
    return boto3.client(
        's3',
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        config=Config(
            signature_version='s3v4',
            retries={'max_attempts': 3}
        )
    )


def upload_image(image_data: str, path: str, content_type: str = 'image/jpeg') -> dict:
    """
    Upload an image to R2.
    
    Args:
        image_data: Base64-encoded image data (with or without data URL prefix)
        path: Storage path (e.g., 'sales/123/front.jpg')
        content_type: MIME type of the image
    
    Returns:
        dict with 'success', 'url', 'path', or 'error'
    """
    client = get_r2_client()
    if not client:
        return {'success': False, 'error': 'R2 not configured'}
    
    try:
        # Strip data URL prefix if present
        if ',' in image_data:
            # Format: data:image/jpeg;base64,/9j/4AAQ...
            header, image_data = image_data.split(',', 1)
            # Extract content type from header if available
            if 'image/' in header:
                content_type = header.split(';')[0].replace('data:', '')
        
        # Decode base64
        image_bytes = base64.b64decode(image_data)
        
        # Upload to R2
        client.put_object(
            Bucket=R2_BUCKET_NAME,
            Key=path,
            Body=image_bytes,
            ContentType=content_type
        )
        
        # Generate public URL
        public_url = f"{R2_PUBLIC_URL}/{path}"
        
        return {
            'success': True,
            'url': public_url,
            'path': path,
            'size': len(image_bytes)
        }
    
    except Exception as e:
        print(f"R2 upload error: {e}")
        return {'success': False, 'error': str(e)}


def upload_sale_image(sale_id: int, image_data: str, image_type: str = 'front') -> dict:
    """
    Upload an image for a Whatnot sale.
    
    Args:
        sale_id: The market_sales ID
        image_data: Base64-encoded image
        image_type: 'front' (only option for sales currently)
    
    Returns:
        dict with 'success', 'url', or 'error'
    """
    # Path: sales/{sale_id}/{type}.jpg
    path = f"sales/{sale_id}/{image_type}.jpg"
    return upload_image(image_data, path)


def upload_submission_image(submission_id: str, image_data: str, image_type: str) -> dict:
    """
    Upload an image for a B4Cert submission.
    
    Args:
        submission_id: Unique submission identifier
        image_data: Base64-encoded image
        image_type: 'front', 'back', 'spine', or 'centerfold'
    
    Returns:
        dict with 'success', 'url', or 'error'
    """
    valid_types = ['front', 'back', 'spine', 'centerfold']
    if image_type not in valid_types:
        return {'success': False, 'error': f'Invalid image type. Must be one of: {valid_types}'}
    
    # Path: submissions/{submission_id}/{type}.jpg
    path = f"submissions/{submission_id}/{image_type}.jpg"
    return upload_image(image_data, path)


def upload_temp_image(image_data: str, prefix: str = 'temp') -> dict:
    """
    Upload a temporary image (e.g., during extraction before sale is recorded).
    
    Args:
        image_data: Base64-encoded image
        prefix: Path prefix
    
    Returns:
        dict with 'success', 'url', 'path', or 'error'
    """
    # Generate unique filename
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    unique_id = uuid.uuid4().hex[:8]
    path = f"{prefix}/{timestamp}_{unique_id}.jpg"
    
    return upload_image(image_data, path)


def delete_image(path: str) -> dict:
    """
    Delete an image from R2.
    
    Args:
        path: Storage path to delete
    
    Returns:
        dict with 'success' or 'error'
    """
    client = get_r2_client()
    if not client:
        return {'success': False, 'error': 'R2 not configured'}
    
    try:
        client.delete_object(Bucket=R2_BUCKET_NAME, Key=path)
        return {'success': True}
    except Exception as e:
        print(f"R2 delete error: {e}")
        return {'success': False, 'error': str(e)}


def get_image_url(path: str) -> str:
    """Get the public URL for an image path."""
    return f"{R2_PUBLIC_URL}/{path}"


def move_temp_to_sale(temp_path: str, sale_id: int, image_type: str = 'front') -> dict:
    """
    Move a temporary image to its permanent sale location.
    
    Args:
        temp_path: Current temporary path
        sale_id: The market_sales ID
        image_type: 'front' (only option for sales currently)
    
    Returns:
        dict with 'success', 'url', 'path', or 'error'
    """
    client = get_r2_client()
    if not client:
        return {'success': False, 'error': 'R2 not configured'}
    
    try:
        new_path = f"sales/{sale_id}/{image_type}.jpg"
        
        # Copy to new location
        client.copy_object(
            Bucket=R2_BUCKET_NAME,
            CopySource=f"{R2_BUCKET_NAME}/{temp_path}",
            Key=new_path
        )
        
        # Delete old file
        client.delete_object(Bucket=R2_BUCKET_NAME, Key=temp_path)
        
        return {
            'success': True,
            'url': f"{R2_PUBLIC_URL}/{new_path}",
            'path': new_path
        }
    
    except Exception as e:
        print(f"R2 move error: {e}")
        return {'success': False, 'error': str(e)}


def check_r2_connection() -> dict:
    """
    Test R2 connection and return status.
    
    Returns:
        dict with 'connected', 'bucket', 'error' (if any)
    """
    client = get_r2_client()
    if not client:
        return {
            'connected': False,
            'error': 'R2 client not configured'
        }
    
    try:
        # Try to list objects (limit 1) to verify connection
        response = client.list_objects_v2(Bucket=R2_BUCKET_NAME, MaxKeys=1)
        return {
            'connected': True,
            'bucket': R2_BUCKET_NAME,
            'endpoint': R2_ENDPOINT
        }
    except Exception as e:
        return {
            'connected': False,
            'error': str(e)
        }

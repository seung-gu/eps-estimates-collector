"""Cloudflare R2 storage utilities."""

import io
import os
from pathlib import Path
from dotenv import load_dotenv

import pandas as pd

try:
    import boto3  # type: ignore[import-untyped]
    from botocore.config import Config  # type: ignore[import-untyped]
except ImportError:
    boto3 = None  # type: ignore[assignment]
    Config = None  # type: ignore[assignment]

load_dotenv()

# R2 credentials
R2_BUCKET_NAME = os.getenv('R2_BUCKET_NAME', '')  # Private (PDF/PNG)
R2_PUBLIC_BUCKET_NAME = os.getenv('R2_PUBLIC_BUCKET_NAME', '')  # Public (CSV)
R2_ACCOUNT_ID = os.getenv('R2_ACCOUNT_ID', '')
R2_ACCESS_KEY_ID = os.getenv('R2_ACCESS_KEY_ID', '')
R2_SECRET_ACCESS_KEY = os.getenv('R2_SECRET_ACCESS_KEY', '')

# Public URL for CSV files (no auth needed)
R2_PUBLIC_URL = "https://pub-62707afd3ebb422aae744c63c49d36a0.r2.dev"

# Cloud storage flags
_has_creds = all([R2_BUCKET_NAME, R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY])
_is_ci = os.getenv('CI', '').lower() == 'true'
_enabled = os.getenv('CLOUD_STORAGE_ENABLED', '').lower() == 'true'
_disabled = os.getenv('CLOUD_STORAGE_ENABLED', '').lower() == 'false'

CLOUD_STORAGE_ENABLED = (_is_ci or _enabled) and _has_creds and not _disabled
PUBLIC_BUCKET_ENABLED = CLOUD_STORAGE_ENABLED and bool(R2_PUBLIC_BUCKET_NAME)


def _get_s3_client():
    """Get S3 client for R2."""
    if not CLOUD_STORAGE_ENABLED:
        print(f"CLOUD_STORAGE_ENABLED is False")
        return None
    if not boto3 or not Config:
        print(f"boto3 or Config not available: boto3={boto3}, Config={Config}")
        return None
    
    try:
        return boto3.client(
            's3',
            endpoint_url=f'https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com',
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            config=Config(signature_version='s3v4')
        )
    except Exception as e:
        print(f"Error creating S3 client: {e}")
        return None


def upload_to_cloud(file_path: Path, cloud_path: str | None = None) -> bool:
    """Upload file to Cloudflare R2.
    
    Args:
        file_path: Local file path
        cloud_path: Cloud storage path (if None, uses file_path.name)
        
    Returns:
        True if successful, False otherwise (never raises exceptions)
    """
    s3_client = _get_s3_client()
    if not s3_client:
        return False
    
    if not file_path.exists():
        return False
    
    cloud_path = cloud_path or file_path.name
    
    try:
        s3_client.upload_file(str(file_path), R2_BUCKET_NAME, cloud_path)
        return True
    except Exception:
        # Silently fail - don't interrupt local file saving
        return False


def download_from_cloud(cloud_path: str, local_path: Path) -> bool:
    """Download file from Cloudflare R2.
    
    Args:
        cloud_path: Cloud storage path
        local_path: Local file path to save to
        
    Returns:
        True if successful, False otherwise (never raises exceptions)
    """
    s3_client = _get_s3_client()
    if not s3_client:
        return False
    
    try:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        s3_client.download_file(R2_BUCKET_NAME, cloud_path, str(local_path))
        return True
    except Exception:
        return False


def read_csv_from_cloud(cloud_path: str) -> pd.DataFrame | None:
    """Read CSV from public URL (no auth needed)."""
    import urllib.request
    
    try:
        url = f"{R2_PUBLIC_URL}/{cloud_path}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            return pd.read_csv(io.BytesIO(response.read()))
    except Exception:
        return None


def write_csv_to_cloud(df: pd.DataFrame, cloud_path: str) -> bool:
    """Write CSV to public bucket (requires auth)."""
    if not PUBLIC_BUCKET_ENABLED or not boto3 or not Config:
        return False
    
    try:
        s3_client = boto3.client(
            's3',
            endpoint_url=f'https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com',
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            config=Config(signature_version='s3v4')
        )
        
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        s3_client.put_object(
            Bucket=R2_PUBLIC_BUCKET_NAME,
            Key=cloud_path,
            Body=csv_buffer.getvalue().encode('utf-8'),
            ContentType='text/csv'
        )
        return True
    except Exception:
        return False


def file_exists_in_cloud(cloud_path: str) -> bool:
    """Check if file exists in Cloudflare R2.
    
    Args:
        cloud_path: Cloud storage path
        
    Returns:
        True if file exists, False otherwise (never raises exceptions)
    """
    s3_client = _get_s3_client()
    if not s3_client:
        return False
    
    try:
        s3_client.head_object(Bucket=R2_BUCKET_NAME, Key=cloud_path)
        return True
    except Exception:
        return False


def list_cloud_files(prefix: str = '') -> list[str]:
    """List files in Cloudflare R2 bucket with given prefix.
    
    Args:
        prefix: Prefix to filter files (e.g., 'estimates/' for PNG files, 'reports/' for PDFs)
        
    Returns:
        List of file paths (keys) in cloud storage
    """
    s3_client = _get_s3_client()
    if not s3_client:
        return []
    
    try:
        files = []
        paginator = s3_client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=R2_BUCKET_NAME, Prefix=prefix):
            if 'Contents' in page:
                for obj in page['Contents']:
                    files.append(obj['Key'])
        return files
    except Exception as e:
        print(f"Error listing cloud files (bucket={R2_BUCKET_NAME}, prefix={prefix}): {e}")
        return []


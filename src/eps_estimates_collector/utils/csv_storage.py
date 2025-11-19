"""CSV storage: read/write CSV files from public cloud URL."""

from datetime import datetime
from pathlib import Path

import pandas as pd

from .cloudflare import read_csv_from_cloud, write_csv_to_cloud


def read_csv(cloud_path: str | None, local_path: Path) -> pd.DataFrame | None:
    """Read CSV from public URL.
    
    Args:
        cloud_path: Cloud file name (if None, uses local_path.name)
        local_path: Not used (kept for compatibility)
    """
    cloud_key = cloud_path or local_path.name
    return read_csv_from_cloud(cloud_key)


def write_csv(df: pd.DataFrame, cloud_path: str | None, local_path: Path) -> bool:
    """Write CSV to public bucket.
    
    Args:
        df: DataFrame to write
        cloud_path: Cloud file name (if None, uses local_path.name)
        local_path: Not used (kept for compatibility)
    """
    cloud_key = cloud_path or local_path.name
    return write_csv_to_cloud(df, cloud_key)


def get_last_date_from_csv(cloud_path: str | None, local_path: Path) -> datetime | None:
    """Get last report date from CSV."""
    df = read_csv(cloud_path, local_path)
    if df is None or df.empty or 'Report_Date' not in df.columns:
        return None
    
    try:
        df['Report_Date'] = pd.to_datetime(df['Report_Date'])
        last_date = df['Report_Date'].max()
        return last_date.to_pydatetime() if pd.notna(last_date) else None
    except Exception:
        return None


def csv_exists(cloud_path: str | None, local_path: Path) -> bool:
    """Check if CSV exists in public URL."""
    cloud_key = cloud_path or local_path.name
    return read_csv_from_cloud(cloud_key) is not None


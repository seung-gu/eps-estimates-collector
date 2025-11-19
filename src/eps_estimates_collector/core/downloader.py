"""PDF downloader for FactSet Earnings Insight reports."""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

# Base URL for FactSet PDFs
BASE_URL = "https://advantage.factset.com/hubfs/Website/Resources%20Section/Research%20Desk/Earnings%20Insight/"


def download_pdfs(
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    rate_limit: float = 0.05,
    skip_existing: set[str] | None = None
) -> list[dict]:
    """Download FactSet Earnings Insight PDFs.
    
    Downloads PDFs from FactSet's public repository. Available from 2016 to present.
    
    Args:
        start_date: Start date for download (default: 2016-01-01)
        end_date: End date for download (default: today)
        rate_limit: Wait time between requests in seconds (default: 0.05)
        skip_existing: Set of existing filenames to skip
        
    Returns:
        List of dictionaries containing download information:
        - 'date': Report date (YYYY-MM-DD)
        - 'format': Date format used (MMDDYY or MMDDYYYY)
        - 'url': Download URL
        - 'size_kb': File size in KB
        - 'filename': Filename (without path)
        - 'content': PDF file content (bytes)
        
    Note:
        PDFs are available from 2016 onwards. If start_date is before 2016,
        it will be automatically adjusted to 2016-01-01.
    """
    # Set default dates
    if start_date is None:
        start_date = datetime(2016, 1, 1)
    if end_date is None:
        end_date = datetime.now()
    
    # Ensure start_date is not before 2016
    min_date = datetime(2016, 1, 1)
    if start_date < min_date:
        print(f"⚠️  Warning: PDFs are only available from 2016 onwards. Adjusting start_date to 2016-01-01.")
        start_date = min_date
    
    found_pdfs: list[dict] = []
    current = end_date
    test_count = 0
    
    print("🔍 FactSet Earnings Insight PDF reverse search and download")
    print(f"Period: {end_date.date()} → {start_date.date()} (reverse)")
    print("=" * 80)
    
    while current >= start_date:
        # Date format conversion
        formats = [
            current.strftime("%m%d%y"),      # 121324
            current.strftime("%m%d%Y"),      # 12132024
        ]
        
        for fmt in formats:
            url = f"{BASE_URL}EarningsInsight_{fmt}.pdf"
            test_count += 1
            
            try:
                # Download with urllib
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.status == 200:
                        content = response.read()
                        size_kb = len(content) / 1024
                        
                        # Filename
                        filename = f"EarningsInsight_{current.strftime('%Y%m%d')}_{fmt}.pdf"
                        
                        # Skip if already exists in cloud
                        if skip_existing and filename in skip_existing:
                            continue
                        
                        found_pdfs.append({
                            'date': current.strftime("%Y-%m-%d"),
                            'format': fmt,
                            'url': url,
                            'size_kb': size_kb,
                            'filename': filename,
                            'content': content
                        })
                        
                        print(f"✅ {current.strftime('%Y-%m-%d')}: {fmt:12s} | {size_kb:6.1f} KB | Download complete")
                        break  # Move to next date if found
            
            except urllib.error.HTTPError:
                pass  # 404, etc.
            except Exception:
                pass
        
        # Progress every 200 files
        if test_count % 200 == 0:
            elapsed_days = (end_date - current).days
            total_days = (end_date - start_date).days
            progress = elapsed_days / total_days * 100 if total_days > 0 else 0
            print(f"⏳ Progress: {progress:.1f}% | Tested: {test_count:,} | Found: {len(found_pdfs)}")
        
        current -= timedelta(days=1)  # Go back one day
        time.sleep(rate_limit)
    
    print(f"\n📊 Final Results: {len(found_pdfs)} PDFs downloaded")
    return found_pdfs


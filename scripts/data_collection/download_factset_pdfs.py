"""
FactSet Earnings Insight PDF reverse search and download
Downloads PDFs from today back to 2000 in reverse order.
"""
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from src.service.csv_storage import get_last_date_from_csv as get_last_date_from_csv_storage

# Project root based paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
BASE_URL = "https://advantage.factset.com/hubfs/Website/Resources%20Section/Research%20Desk/Earnings%20Insight/"

OUTPUT_DIR = PROJECT_ROOT / "output" / "factset_pdfs"
INDEX_FILE = PROJECT_ROOT / "output" / "factset_pdfs_index.json"
CSV_FILE = PROJECT_ROOT / "output" / "extracted_estimates.csv"


def download_factset_pdfs(
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    rate_limit: float = 0.05
) -> tuple[list[dict], int]:
    """Download PDFs from FactSet.
    
    Args:
        start_date: Start date (default: 2000-01-01)
        end_date: End date (default: today)
        rate_limit: Wait time between requests (seconds)
        
    Returns:
        Tuple of (list of downloaded PDF info, number of URLs tested)
    """
    if start_date is None:
        start_date = datetime(2000, 1, 1)
    if end_date is None:
        end_date = datetime.now()
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
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
                        filename = OUTPUT_DIR / f"EarningsInsight_{current.strftime('%Y%m%d')}_{fmt}.pdf"
                        
                        # Save locally
                        with open(filename, 'wb') as f:
                            f.write(content)
                        
                        found_pdfs.append({
                            'date': current.strftime("%Y-%m-%d"),
                            'format': fmt,
                            'url': url,
                            'size_kb': size_kb,
                            'filename': str(filename.relative_to(PROJECT_ROOT))
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
    
    return found_pdfs, test_count




def save_index(found_pdfs: list[dict]) -> None:
    """Save downloaded PDF index to JSON file.
    
    Args:
        found_pdfs: List of PDF information
    """
    if not found_pdfs:
        print("\n❌ No PDFs found")
        return
    
    # Statistics by year
    print("\n📅 Distribution by year:")
    years: dict[str, int] = {}
    for pdf in found_pdfs:
        year = pdf['date'][:4]
        years[year] = years.get(year, 0) + 1
    
    for year in sorted(years.keys(), reverse=True):
        print(f"  {year}: {years[year]:3d} files")
    
    # Save JSON
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(found_pdfs, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Index saved: {INDEX_FILE.relative_to(PROJECT_ROOT)}")
    print(f"✅ PDFs saved to: {OUTPUT_DIR.relative_to(PROJECT_ROOT)}/")


def main() -> None:
    """Main function"""
    # Get start date from CSV file (last date + 1 day)
    last_date = get_last_date_from_csv_storage(None, CSV_FILE)
    if last_date:
        start_date = last_date + timedelta(days=1)
        print(f"📅 Found existing CSV file")
        print(f"   Last report date: {last_date.strftime('%Y-%m-%d')}")
        print(f"   Starting download from: {start_date.strftime('%Y-%m-%d')}")
    else:
        start_date = None  # Will default to 2000-01-01
        print(f"📅 No existing CSV file found, starting from 2000-01-01")
    
    print()
    found_pdfs, test_count = download_factset_pdfs(start_date=start_date)
    
    print("\n" + "=" * 80)
    print(f"📊 Final Results")
    print("=" * 80)
    print(f"URLs tested: {test_count:,}")
    print(f"PDFs found: {len(found_pdfs)}")
    if found_pdfs:
        print(f"Total size: {sum(p['size_kb'] for p in found_pdfs)/1024:.1f} MB")
    
    save_index(found_pdfs)


if __name__ == "__main__":
    main()

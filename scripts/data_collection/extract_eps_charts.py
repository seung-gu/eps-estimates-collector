"""
Extract Quarterly Bottom-Up EPS chart pages from FactSet PDFs
"""
import pdfplumber
import os
import glob
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from src.service.csv_storage import get_last_date_from_csv as get_last_date_from_csv_storage

# Project root based paths
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Settings
OUTPUT_DIR = PROJECT_ROOT / "output" / "estimates"
PDF_DIR = PROJECT_ROOT / "output" / "factset_pdfs"
CSV_FILE = PROJECT_ROOT / "output" / "extracted_estimates.csv"
KEYWORDS = [
    "Bottom-Up EPS Estimates: Current & Historical",
    "Bottom-up EPS Estimates: Current & Historical", 
    "Bottom-Up EPS: Current & Historical",
]
LIMIT = None  # Number of PDFs to extract (None = all)

# Create output directory
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    """Main function"""
    # PDF file list (newest first)
    pdf_files = sorted(glob.glob(f"{PDF_DIR}/*.pdf"), reverse=True)
    
    # Get last date from CSV to skip already processed PDFs
    last_date = get_last_date_from_csv_storage(None, CSV_FILE)
    if last_date:
        min_date = last_date + timedelta(days=1)
        print(f"📅 Found existing CSV file")
        print(f"   Last report date: {last_date.strftime('%Y-%m-%d')}")
        print(f"   Processing PDFs from: {min_date.strftime('%Y-%m-%d')} onwards")
    else:
        min_date = None
        print(f"📅 No existing CSV file found, processing all PDFs")
        if not pdf_files:
            print(f"\n⚠️  No PDF files found in {PDF_DIR}")
            print(f"   Please run 'uv run python scripts/data_collection/download_factset_pdfs.py' first to download PDFs.")
            return
    
    print(f"🔍 Extracting EPS charts from FactSet PDFs")
    print(f"Target: {len(pdf_files)} PDFs {'all' if LIMIT is None else f'{LIMIT} of'}")
    print("=" * 80)
    
    extracted = 0
    skipped = 0
    
    for pdf_path in pdf_files:
        if LIMIT is not None and extracted >= LIMIT:
            break
        
        filename = os.path.basename(pdf_path)
        
        # Extract date (EarningsInsight_20161209_120916.pdf -> 20161209)
        try:
            date_str = filename.split('_')[1]
            report_date_dt = datetime.strptime(date_str, '%Y%m%d')
            report_date = report_date_dt.strftime('%Y-%m-%d')
        except:
            continue
        
        # Skip if PDF date is before minimum date (already processed)
        if min_date and report_date_dt < min_date:
            skipped += 1
            continue
        
        # Check if PNG already exists
        output_path = OUTPUT_DIR / f"{date_str}.png"
        if output_path.exists():
            skipped += 1
            continue
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    
                    if text and any(kw in text for kw in KEYWORDS):
                        # Check keyword location (if at bottom of page)
                        keyword_at_bottom = False
                        for word in page.extract_words():
                            if any(kw.split()[0] in word['text'] for kw in KEYWORDS):
                                # If y coordinate is 700 or more, consider it bottom of page
                                if word['top'] > 700:
                                    keyword_at_bottom = True
                                    break
                        
                        # If keyword is at bottom, extract next page
                        if keyword_at_bottom and page_num + 1 < len(pdf.pages):
                            target_page = pdf.pages[page_num + 1]
                            target_page_num = page_num + 2
                            print(f"   ⚠️  Keyword detected at bottom -> move to next page")
                        else:
                            target_page = page
                            target_page_num = page_num + 1
                        
                        # Save high-resolution image
                        target_page.to_image(resolution=300).save(str(output_path))
                        
                        print(f"✅ {report_date:12s} Page {target_page_num:2d} -> {output_path.relative_to(PROJECT_ROOT)}")
                        extracted += 1
                        
                        # Progress (every 10 files)
                        if extracted % 10 == 0:
                            print(f"   📊 Progress: {extracted} files extracted")
                        
                        break
        
        except Exception as e:
            print(f"❌ {report_date:12s} Error: {str(e)[:50]}")
    
    print("\n" + "=" * 80)
    print(f"📊 Result: {extracted} files extracted")
    if skipped > 0:
        print(f"⏭️  Skipped: {skipped} files (already processed or before minimum date)")


if __name__ == '__main__':
    main()

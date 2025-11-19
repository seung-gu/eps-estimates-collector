"""Chart extractor for FactSet PDF reports."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pdfplumber

# Keywords to identify EPS chart pages
KEYWORDS = [
    "Bottom-Up EPS Estimates: Current & Historical",
    "Bottom-up EPS Estimates: Current & Historical",
    "Bottom-Up EPS: Current & Historical",
]


def extract_charts(
    pdfs: list[Path | str]
) -> list[tuple[str, bytes]]:
    """Extract EPS estimate chart pages from PDF files.
    
    Extracts the page containing "Bottom-Up EPS Estimates" chart from each PDF
    and returns PNG image data in memory.
    
    Args:
        pdfs: List of PDF file paths (Path objects or strings)
        
    Returns:
        List of tuples (filename, image_bytes) for extracted PNG files
    """
    extracted_files: list[tuple[str, bytes]] = []
    
    print(f"🔍 Extracting EPS charts from {len(pdfs)} PDFs")
    print("=" * 80)
    
    for pdf_path in pdfs:
        if isinstance(pdf_path, str):
            pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            print(f"⚠️  Skipping {pdf_path.name}: File not found")
            continue
        
        # Extract date from filename (EarningsInsight_20161209_120916.pdf -> 20161209)
        try:
            date_str = pdf_path.stem.split('_')[1]
            report_date_dt = datetime.strptime(date_str, '%Y%m%d')
            report_date = report_date_dt.strftime('%Y-%m-%d')
        except (IndexError, ValueError):
            print(f"⚠️  Skipping {pdf_path.name}: Cannot extract date from filename")
            continue
        
        filename = f"{date_str}.png"
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    
                    if text and any(kw in text for kw in KEYWORDS):
                        # Check keyword location (if at bottom of page)
                        keyword_at_bottom = False
                        for word in page.extract_words():
                            if any(kw.split()[0] in word['text'] for kw in KEYWORDS):
                                if word['top'] > 700:
                                    keyword_at_bottom = True
                                    break
                        
                        # If keyword is at bottom, extract next page
                        if keyword_at_bottom and page_num + 1 < len(pdf.pages):
                            target_page = pdf.pages[page_num + 1]
                            target_page_num = page_num + 2
                        else:
                            target_page = page
                            target_page_num = page_num + 1
                        
                        # Get image bytes (save to BytesIO instead of disk)
                        import io
                        img = target_page.to_image(resolution=300)
                        img_bytes = io.BytesIO()
                        img.save(img_bytes, format='PNG')
                        image_bytes = img_bytes.getvalue()
                        
                        print(f"✅ {report_date:12s} Page {target_page_num:2d} -> {filename}")
                        extracted_files.append((filename, image_bytes))
                        break
                else:
                    print(f"⚠️  {report_date}: No EPS chart page found")
        
        except Exception as e:
            print(f"❌ {report_date}: Error - {str(e)[:50]}")
    
    print(f"\n📊 Result: {len(extracted_files)} PNG files extracted")
    return extracted_files


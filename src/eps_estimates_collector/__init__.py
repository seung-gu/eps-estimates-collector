"""EPS Estimates Collector - Unified API for collecting and analyzing EPS estimates.

This package provides a comprehensive toolkit for:
- Downloading FactSet Earnings Insight PDFs
- Extracting EPS estimate charts from PDFs
- Processing charts with OCR to extract data
- Calculating P/E ratios from EPS estimates

Example:
    >>> from eps_estimates_collector import download_pdfs, extract_charts, process_images, calculate_pe_ratio
    >>> from datetime import datetime
    >>> from pathlib import Path
    >>> 
    >>> # Download PDFs
    >>> pdfs = download_pdfs(
    ...     start_date=datetime(2024, 1, 1),
    ...     end_date=datetime.now(),
    ...     outpath=Path("output/pdfs")
    ... )
    >>> 
    >>> # Extract charts
    >>> charts = extract_charts(pdfs, outpath=Path("output/charts"))
    >>> 
    >>> # Process with OCR
    >>> df = process_images(
    ...     directory=Path("output/charts"),
    ...     output_csv=Path("output/estimates.csv")
    ... )
    >>> 
    >>> # Calculate P/E ratios
    >>> pe_df = calculate_pe_ratio(
    ...     csv_path=Path("output/estimates.csv"),
    ...     price_data={'2024-01-15': 150.5, '2024-02-15': 152.3},
    ...     type='forward'
    ... )
"""

from .core import download_pdfs, extract_charts, process_images, process_image
from .analysis import calculate_pe_ratio

__version__ = "0.2.0"

__all__ = [
    'download_pdfs',
    'extract_charts',
    'process_images',
    'process_image',
    'calculate_pe_ratio',
]

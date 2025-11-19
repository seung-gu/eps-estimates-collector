"""
CLI wrapper for downloading FactSet Earnings Insight PDFs.

This script provides a command-line interface to download PDFs from FactSet.
For programmatic use, import from the main package:
    from eps_estimates_collector import download_pdfs
"""
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.eps_estimates_collector import download_pdfs


def main() -> None:
    """CLI entry point for PDF download."""
    # Default paths
    output_dir = PROJECT_ROOT / "output" / "factset_pdfs"
    
    print("=" * 80)
    print("FactSet PDF Downloader (CLI)")
    print("=" * 80)
    print()
    
    # Download PDFs (from 2016 to today)
    pdfs = download_pdfs(
        start_date=datetime(2016, 1, 1),
        end_date=datetime.now(),
        outpath=output_dir,
        rate_limit=0.05
    )
    
    print()
    print("=" * 80)
    print(f"✅ Complete: {len(pdfs)} PDFs downloaded to {output_dir}")
    print("=" * 80)
    

if __name__ == '__main__':
    main()

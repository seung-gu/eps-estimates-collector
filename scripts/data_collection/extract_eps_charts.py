"""
CLI wrapper for extracting EPS charts from FactSet PDFs.

This script provides a command-line interface to extract chart pages from PDFs.
For programmatic use, import from the main package:
    from eps_estimates_collector import extract_charts
"""
import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.eps_estimates_collector import extract_charts


def main() -> None:
    """CLI entry point for chart extraction."""
    # Default paths
    pdf_dir = PROJECT_ROOT / "output" / "factset_pdfs"
    output_dir = PROJECT_ROOT / "output" / "estimates"
    
    print("=" * 80)
    print("EPS Chart Extractor (CLI)")
print("=" * 80)
    print()
    
    # Get PDF files
    pdf_files = sorted(pdf_dir.glob("*.pdf"), reverse=True)
                
    if not pdf_files:
        print(f"⚠️  No PDF files found in {pdf_dir}")
        print(f"   Please run 'uv run python scripts/data_collection/download_factset_pdfs.py' first.")
        return
    
    # Extract charts
    charts = extract_charts(pdf_files, outpath=output_dir)
                    
    print()
    print("=" * 80)
    print(f"✅ Complete: {len(charts)} charts extracted to {output_dir}")
    print("=" * 80)


if __name__ == '__main__':
    main()

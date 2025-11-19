"""Core functionality for FactSet data collection."""

from .downloader import download_pdfs
from .extractor import extract_charts
from .ocr import process_images, process_image

__all__ = [
    'download_pdfs',
    'extract_charts',
    'process_images',
    'process_image',
]


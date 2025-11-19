"""Test script for bar graph classification using all three methods."""

import cv2
from pathlib import Path
from src.eps_estimates_collector.core.ocr.google_vision_processor import extract_text_with_boxes
from src.eps_estimates_collector.core.ocr.coordinate_matcher import match_quarters_with_numbers
from src.eps_estimates_collector.core.ocr.bar_classifier import classify_all_bars


def test_multiple_methods():
    """Classify bar graphs using all three methods and print results."""
    # Set image path (not a pytest fixture, just a local variable)
    image_path = Path('output/estimates/20161209-6.png')
    
    # Read image
    image = cv2.imread(str(image_path))
    if image is None:
        print(f"Test image not found: {image_path}")
        return
    
    # OCR and matching
    print("Performing OCR and matching...")
    ocr_results = extract_text_with_boxes(image_path)
    matched_results = match_quarters_with_numbers(ocr_results)
    print(f"Total {len(matched_results)} matches completed\n")
    
    # Classify using three methods
    print("Classifying bar graphs using three methods...")
    classified_results = classify_all_bars(image, matched_results, use_multiple_methods=True)
    
    # Print results
    print("\n=== Classification Results ===\n")
    for result in classified_results:
        quarter = result['quarter']
        eps = result['eps']
        bar_color = result['bar_color']
        confidence = result['bar_confidence']
        votes = result['bar_votes']
        methods = result['bar_methods']
        
        print(f"{quarter}: EPS={eps}, Bar={bar_color} (confidence: {confidence})")
        print(f"  Votes: dark={votes['dark']}, light={votes['light']}")
        print(f"  Method results:")
        print(f"    - Adaptive Threshold: {methods['adaptive']}")
        print(f"    - Morphology Closing: {methods['closing']}")
        print(f"    - OTSU Inverted: {methods['otsu_inv']}")
        print()
    
    # Statistics
    high_conf = sum(1 for r in classified_results if r['bar_confidence'] == 'high')
    medium_conf = sum(1 for r in classified_results if r['bar_confidence'] == 'medium')
    low_conf = sum(1 for r in classified_results if r['bar_confidence'] == 'low')
    
    print(f"\n=== Confidence Statistics ===")
    print(f"High (3/3 match): {high_conf}")
    print(f"Medium (2/3 match): {medium_conf}")
    print(f"Low (1/3 or 0/3): {low_conf}")


if __name__ == '__main__':
    test_multiple_methods()

"""Test script for coordinate-based matching."""

from pathlib import Path
from src.factset_data_collector.core.ocr.google_vision_processor import extract_text_with_boxes
from src.factset_data_collector.core.ocr.coordinate_matcher import (
    match_quarters_with_numbers,
    find_quarters_at_bottom,
    find_nearest_number_in_y_range,
    extract_number,
    extract_quarter_pattern,
    is_same_y_range,
    calculate_distance,
)


def test_coordinate_matching():
    """Test coordinate-based matching."""
    
    # Set image path (not a pytest fixture, just a local variable)
    image_path = Path('output/estimates/20161209-6.png')
    
    if not image_path.exists():
        print(f"Test image not found: {image_path}")
        return
    
    print(f"Processing image: {image_path}")
    
    # Get OCR results
    ocr_results = extract_text_with_boxes(image_path)
    print(f"OCR results: {len(ocr_results)} text regions")
    
    # Find Q patterns at bottom
    quarter_boxes = find_quarters_at_bottom(ocr_results, bottom_percent=0.3)
    print(f"\nBottom Q patterns: {len(quarter_boxes)} found")
    for qb in quarter_boxes[:5]:
        print(f"  - {qb['quarter']}: '{qb['text']}' (y:{qb['top']})")
    
    # Check number candidates around each Q box
    print(f"\n=== Checking Number Candidates ===")
    for qb in quarter_boxes[:3]:
        print(f"\nQ box: {qb['quarter']} (y:{qb['top']}, x:{qb['left']})")
        # Find all number candidates in the same y range
        y_tolerance = 50.0  # Wider tolerance
        candidates = []
        for box in ocr_results:
            if (box['left'] == qb['left'] and box['top'] == qb['top']):
                continue
            if extract_quarter_pattern(box['text']) is not None:
                continue
            number = extract_number(box['text'])
            if number is None:
                continue
            if is_same_y_range(qb, box, y_tolerance):
                distance = calculate_distance(qb, box)
                candidates.append({
                    'text': box['text'],
                    'number': number,
                    'x': box['left'],
                    'y': box['top'],
                    'distance': distance
                })
        
        candidates.sort(key=lambda x: x['distance'])
        print(f"  Number candidates: {len(candidates)} found")
        for c in candidates[:5]:
            print(f"    - '{c['text']}' = {c['number']} (x:{c['x']}, y:{c['y']}, distance:{c['distance']:.1f})")
    
    # Perform coordinate-based matching
    matched_results = match_quarters_with_numbers(
        ocr_results,
        bottom_percent=0.3,   # Bottom 30%
        y_tolerance=1000.0,   # Y coordinate tolerance: 1000 pixels
        x_tolerance=10.0      # X coordinate tolerance: 10 pixels
    )
    
    print(f"\n=== Matching Results (Total: {len(matched_results)}) ===")
    for i, result in enumerate(matched_results, 1):
        print(f"{i}. {result['quarter']}: {result['eps']}")
        print(f"   Q box: '{result['quarter_box']['text']}' "
              f"(x:{result['quarter_box']['left']}, y:{result['quarter_box']['top']})")
        print(f"   Number box: '{result['number_box']['text']}' "
              f"(x:{result['number_box']['left']}, y:{result['number_box']['top']})")
        print(f"   Distance: {result['distance']:.2f} pixels")
        print()
    
    return matched_results


if __name__ == '__main__':
    test_coordinate_matching()

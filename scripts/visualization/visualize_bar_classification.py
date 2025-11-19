"""Script to visualize bar graph classification results."""

import cv2
import numpy as np
from pathlib import Path
from src.eps_estimates_collector.core.ocr.google_vision_processor import extract_text_with_boxes
from src.eps_estimates_collector.core.ocr.coordinate_matcher import match_quarters_with_numbers
from src.eps_estimates_collector.core.ocr.bar_classifier import classify_all_bars, get_bar_region_coordinates


def visualize_classification_results(image_path: Path, output_path: Path):
    """Visualize bar graph classification results."""
    # Read image
    image = cv2.imread(str(image_path))
    if image is None:
        print(f"Cannot read image: {image_path}")
        return
    
    # OCR and matching
    print("Performing OCR and matching...")
    ocr_results = extract_text_with_boxes(image_path)
    matched_results = match_quarters_with_numbers(ocr_results)
    print(f"Total {len(matched_results)} matches completed")
    
    # Bar graph classification
    print("Classifying bar graphs...")
    classified_results = classify_all_bars(image, matched_results, use_multiple_methods=True)
    
    # Create result image
    img_result = image.copy()
    
    # Define colors (BGR format)
    Q_BOX_COLOR = (0, 255, 0)  # Green - Q box
    DARK_BAR_COLOR = (0, 0, 255)  # Red - dark bar (B=0, G=0, R=255)
    LIGHT_BAR_COLOR = (255, 0, 255)  # Magenta - light bar (B=255, G=0, R=255) - clearer distinction
    
    # Debug: Print classification results
    print("\n=== Bar Graph Classification Results ===")
    for i, result in enumerate(classified_results):
        print(f"{i+1}. {result['quarter']}: {result['bar_color']} (votes: {result['bar_votes']})")
    print()
    
    for result in classified_results:
        q_box = result['quarter_box']
        num_box = result['number_box']
        quarter = result['quarter']
        eps = result['eps']
        bar_color = result['bar_color']
        
        # Draw Q box (green)
        q_left = q_box['left']
        q_top = q_box['top']
        q_right = q_left + q_box['width']
        q_bottom = q_top + q_box['height']
        cv2.rectangle(img_result, (q_left, q_top), (q_right, q_bottom), Q_BOX_COLOR, 2)
        
        # Display Q text
        cv2.putText(img_result, quarter, (q_left, q_top - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, Q_BOX_COLOR, 2)
        
        # Determine number box color (based on bar graph type)
        num_box_color = DARK_BAR_COLOR if bar_color == 'dark' else LIGHT_BAR_COLOR
        
        # Draw number box (color changes based on bar graph type)
        num_left = num_box['left']
        num_top = num_box['top']
        num_right = num_left + num_box['width']
        num_bottom = num_top + num_box['height']
        cv2.rectangle(img_result, (num_left, num_top), (num_right, num_bottom), num_box_color, 2)
        
        # Display number text (color changes based on bar graph type)
        eps_text = f"{eps}"
        cv2.putText(img_result, eps_text, (num_left, num_top - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, num_box_color, 2)
    
    # Save
    cv2.imwrite(str(output_path), img_result)
    print(f"\nVisualization results saved to {output_path}")
    
    # Print statistics
    dark_count = sum(1 for r in classified_results if r['bar_color'] == 'dark')
    light_count = sum(1 for r in classified_results if r['bar_color'] == 'light')
    high_conf = sum(1 for r in classified_results if r['bar_confidence'] == 'high')
    medium_conf = sum(1 for r in classified_results if r['bar_confidence'] == 'medium')
    low_conf = sum(1 for r in classified_results if r['bar_confidence'] == 'low')
    
    print(f"\n=== Classification Statistics ===")
    print(f"Dark bars: {dark_count}")
    print(f"Light bars: {light_count}")
    print(f"High confidence: {high_conf}")
    print(f"Medium confidence: {medium_conf}")
    print(f"Low confidence: {low_conf}")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        image_name = sys.argv[1]
    else:
        image_name = '20161209-6.png'
    
    test_image = Path(f'output/estimates/{image_name}')
    output_path = Path(f'output/preprocessing_test/{image_name.replace(".png", "")}_bar_classification.png')
    
    visualize_classification_results(test_image, output_path)

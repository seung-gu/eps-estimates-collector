"""Script to visualize coordinate-based matching results."""

import cv2
import numpy as np
from pathlib import Path
from src.eps_estimates_collector.core.ocr.google_vision_processor import extract_text_with_boxes
from src.eps_estimates_collector.core.ocr.coordinate_matcher import match_quarters_with_numbers


def visualize_matching_results(image_path: Path, output_path: Path):
    """Visualize coordinate-based matching results."""
    # Read image
    image = cv2.imread(str(image_path))
    if image is None:
        print(f"Cannot read image: {image_path}")
        return
    
    # Get OCR results
    ocr_results = extract_text_with_boxes(image_path)
    
    # Perform coordinate-based matching
    matched_results = match_quarters_with_numbers(ocr_results)
    
    # Create result image
    img_result = image.copy()
    
    for result in matched_results:
        q_box = result['quarter_box']
        num_box = result['number_box']
        
        # Draw Q box (green)
        q_left = q_box['left']
        q_top = q_box['top']
        q_right = q_left + q_box['width']
        q_bottom = q_top + q_box['height']
        cv2.rectangle(img_result, (q_left, q_top), (q_right, q_bottom), (0, 255, 0), 2)
        
        # Display Q text
        cv2.putText(img_result, result['quarter'], (q_left, q_top - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Draw number box (red)
        num_left = num_box['left']
        num_top = num_box['top']
        num_right = num_left + num_box['width']
        num_bottom = num_top + num_box['height']
        cv2.rectangle(img_result, (num_left, num_top), (num_right, num_bottom), (0, 0, 255), 2)
        
        # Display number text
        cv2.putText(img_result, f"{result['eps']}", (num_left, num_top - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Draw connection line (yellow)
        q_center_x = q_left + q_box['width'] / 2
        q_center_y = q_top + q_box['height'] / 2
        num_center_x = num_left + num_box['width'] / 2
        num_center_y = num_top + num_box['height'] / 2
        
        cv2.line(img_result, 
                (int(q_center_x), int(q_center_y)),
                (int(num_center_x), int(num_center_y)),
                (0, 255, 255), 2)
    
    # Save
    cv2.imwrite(str(output_path), img_result)
    print(f"Matching visualization saved to {output_path}")
    print(f"Total {len(matched_results)} matches completed")


if __name__ == '__main__':
    test_image = Path('output/estimates/20161209-6.png')
    output_path = Path('output/preprocessing_test/20161209-6_coordinate_matching.png')
    
    visualize_matching_results(test_image, output_path)

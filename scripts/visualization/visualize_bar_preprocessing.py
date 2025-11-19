"""Script to apply various preprocessing techniques to bar graph regions and compare results."""

import cv2
import numpy as np
from pathlib import Path
from src.eps_estimates_collector.core.ocr.google_vision_processor import extract_text_with_boxes
from src.eps_estimates_collector.core.ocr.coordinate_matcher import match_quarters_with_numbers


def apply_preprocessing_to_bar(image: np.ndarray, q_box: dict, num_box: dict) -> dict:
    """Apply various preprocessing techniques to bar graph region."""
    # Define bar graph region
    q_center_x = q_box['left'] + q_box['width'] / 2
    num_center_x = num_box['left'] + num_box['width'] / 2
    x_center = int((q_center_x + num_center_x) / 2)
    x_width = 30
    x_min = max(0, int(x_center - x_width / 2))
    x_max = min(image.shape[1], int(x_center + x_width / 2))
    
    y_top = int(num_box['top'] + num_box['height'])
    y_bottom = int(q_box['top'])
    
    # Crop region
    cropped = image[y_top:y_bottom, x_min:x_max]
    
    if cropped.size == 0:
        return {}
    
    # Convert to grayscale
    gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
    
    results = {
        'original': cropped,
        'grayscale': gray,
    }
    
    # OTSU binarization
    _, otsu_binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    results['otsu'] = otsu_binary
    
    # OTSU binarization (inverted)
    _, otsu_binary_inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    results['otsu_inv'] = otsu_binary_inv
    
    # Adaptive threshold
    adaptive_thresh = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    results['adaptive'] = adaptive_thresh
    
    # CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    clahe_gray = clahe.apply(gray)
    results['clahe'] = clahe_gray
    
    # Histogram equalization
    hist_eq = cv2.equalizeHist(gray)
    results['hist_eq'] = hist_eq
    
    # Denoising
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
    results['denoised'] = denoised
    
    # CLAHE + OTSU
    _, clahe_otsu = cv2.threshold(clahe_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    results['clahe_otsu'] = clahe_otsu
    
    # Denoising + OTSU
    _, denoised_otsu = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    results['denoised_otsu'] = denoised_otsu
    
    return results


def visualize_all_bars_preprocessing(image_path: Path, output_dir: Path):
    """Apply preprocessing to all bar graphs and save results."""
    image = cv2.imread(str(image_path))
    if image is None:
        print(f"Cannot read image: {image_path}")
        return
    
    ocr_results = extract_text_with_boxes(image_path)
    matched_results = match_quarters_with_numbers(ocr_results)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Processing {len(matched_results)} bar graphs...\n")
    
    for result in matched_results:
        quarter = result['quarter'].replace("'", "")
        q_box = result['quarter_box']
        num_box = result['number_box']
        
        preprocessed = apply_preprocessing_to_bar(image, q_box, num_box)
        
        if preprocessed:
            for method, processed_img in preprocessed.items():
                output_path = output_dir / f"bar_{quarter}_{method}.png"
                cv2.imwrite(str(output_path), processed_img)
        
        print(f"{result['quarter']} processing completed")
    
    print(f"\nAll results saved to {output_dir}")


if __name__ == '__main__':
    test_image = Path('output/estimates/20161209-6.png')
    output_dir = Path('output/preprocessing_test/bar_preprocessing')
    
    visualize_all_bars_preprocessing(test_image, output_dir)

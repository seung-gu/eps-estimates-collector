"""Module for classifying bar graph colors."""

import cv2
import numpy as np


def get_bar_region_coordinates(q_box: dict, num_box: dict, image_width: int) -> tuple[int, int, int, int]:
    """Calculate coordinates of bar graph region.
    
    Args:
        q_box: Q box information
        num_box: Number box information
        image_width: Image width
        
    Returns:
        (x_min, x_max, y_top, y_bottom) tuple
    """
    q_center_x = q_box['left'] + q_box['width'] / 2
    num_center_x = num_box['left'] + num_box['width'] / 2
    
    x_center = int((q_center_x + num_center_x) / 2)
    x_width = 30
    x_min = max(0, int(x_center - x_width / 2))
    x_max = min(image_width, int(x_center + x_width / 2))
    
    y_top = int(num_box['top'] + num_box['height'])
    y_bottom = int(q_box['top'])
    
    return x_min, x_max, y_top, y_bottom


def classify_with_adaptive_threshold(cropped_region: np.ndarray, threshold: float = 0.7) -> str:
    """Classify bar graph using Adaptive Threshold method.
    
    Args:
        cropped_region: Cropped bar graph region (binary image)
        threshold: White pixel ratio threshold
        
    Returns:
        'dark' or 'light'
    """
    if cropped_region.size == 0:
        return 'light'
    
    white_pixels = np.sum(cropped_region == 255)
    total_pixels = cropped_region.size
    white_ratio = white_pixels / total_pixels
    
    return 'dark' if white_ratio > threshold else 'light'


def classify_with_morphology_closing(cropped_region: np.ndarray, threshold: float = 0.5) -> str:
    """Classify bar graph using Morphology Closing method.
    
    Morphology Closing fills holes, so:
    - Low white ratio (partially filled bar) -> dark
    - High white ratio (fully filled bar) -> light
    
    Args:
        cropped_region: Cropped bar graph region (binary image)
        threshold: White pixel ratio threshold
        
    Returns:
        'dark' or 'light'
    """
    if cropped_region.size == 0:
        return 'light'
    
    white_pixels = np.sum(cropped_region == 255)
    total_pixels = cropped_region.size
    white_ratio = white_pixels / total_pixels
    
    # Inverted logic: low ratio = dark (partially filled), high ratio = light (fully filled)
    return 'light' if white_ratio > threshold else 'dark'


def classify_with_otsu_inverted(cropped_region: np.ndarray, threshold: float = 0.7) -> str:
    """Classify bar graph using OTSU Binary Inverted method.
    
    Args:
        cropped_region: Cropped bar graph region (binary image, inverted)
        threshold: White pixel ratio threshold
        
    Returns:
        'dark' or 'light'
    """
    if cropped_region.size == 0:
        return 'light'
    
    white_pixels = np.sum(cropped_region == 255)
    total_pixels = cropped_region.size
    white_ratio = white_pixels / total_pixels
    
    return 'dark' if white_ratio > threshold else 'light'


def classify_bar_with_multiple_methods(
    original_image: np.ndarray,
    adaptive_image: np.ndarray,
    closing_image: np.ndarray,
    otsu_inv_image: np.ndarray,
    q_box: dict,
    num_box: dict
) -> dict:
    """Classify bar graph using all 3 preprocessing methods and calculate confidence.
    
    Args:
        original_image: Original image (BGR)
        adaptive_image: Image with Adaptive Threshold applied
        closing_image: Image with Morphology Closing applied
        otsu_inv_image: OTSU Binary Inverted image
        q_box: Q box information
        num_box: Number box information
        
    Returns:
        {
            'bar_color': 'dark' or 'light',
            'confidence': 'high' (3/3), 'medium' (2/3), 'low' (1/3 or 0/3),
            'votes': {'dark': 0-3, 'light': 0-3},
            'methods': {
                'adaptive': 'dark' or 'light',
                'closing': 'dark' or 'light',
                'otsu_inv': 'dark' or 'light'
            }
        }
    """
    # Calculate bar graph region coordinates
    x_min, x_max, y_top, y_bottom = get_bar_region_coordinates(
        q_box, num_box, original_image.shape[1]
    )
    
    if y_bottom <= y_top or x_max <= x_min:
        return {
            'bar_color': 'light',
            'confidence': 'low',
            'votes': {'dark': 0, 'light': 0},
            'methods': {}
        }
    
    # Crop bar graph region from each preprocessed image
    adaptive_cropped = adaptive_image[y_top:y_bottom, x_min:x_max]
    closing_cropped = closing_image[y_top:y_bottom, x_min:x_max]
    otsu_inv_cropped = otsu_inv_image[y_top:y_bottom, x_min:x_max]
    
    # Classify with each method
    result_adaptive = classify_with_adaptive_threshold(adaptive_cropped)
    result_closing = classify_with_morphology_closing(closing_cropped)
    result_otsu_inv = classify_with_otsu_inverted(otsu_inv_cropped)
    
    # Aggregate votes
    votes = {'dark': 0, 'light': 0}
    votes[result_adaptive] += 1
    votes[result_closing] += 1
    votes[result_otsu_inv] += 1
    
    # Determine final result (majority vote)
    final_color = 'dark' if votes['dark'] > votes['light'] else 'light'
    
    # Calculate confidence
    if votes[final_color] == 3:
        confidence = 'high'  # 3/3 match
    elif votes[final_color] == 2:
        confidence = 'medium'  # 2/3 match
    else:
        confidence = 'low'  # 1/3 or 0/3
    
    return {
        'bar_color': final_color,
        'confidence': confidence,
        'votes': votes,
        'methods': {
            'adaptive': result_adaptive,
            'closing': result_closing,
            'otsu_inv': result_otsu_inv
        }
    }


def classify_bar_color(image: np.ndarray, q_box: dict, num_box: dict, 
                      brightness_threshold: float = 150.0) -> str:
    """Classify bar graph color between Q box and number box.
    
    Args:
        image: Image array (BGR format)
        q_box: Q box information (includes left, top, width, height)
        num_box: Number box information (includes left, top, width, height)
        brightness_threshold: Brightness threshold (lower than this = dark, higher = light)
        
    Returns:
        'dark' or 'light'
    """
    # Calculate bar graph region coordinates
    x_min, x_max, y_top, y_bottom = get_bar_region_coordinates(
        q_box, num_box, image.shape[1]
    )
    
    # Crop region
    cropped = image[y_top:y_bottom, x_min:x_max]
    
    if cropped.size == 0:
        return 'light'  # Default value
    
    # Convert to grayscale
    gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
    
    # Calculate mean brightness of entire region
    mean_brightness = np.mean(gray)
    
    # Classify by brightness
    if mean_brightness < brightness_threshold:
        return 'dark'
    else:
        return 'light'


def preprocess_images_for_classification(image: np.ndarray) -> dict[str, np.ndarray]:
    """Generate preprocessed images for bar graph classification.
    
    Args:
        image: Original image (BGR format)
        
    Returns:
        {
            'adaptive': Adaptive Threshold image,
            'closing': Morphology Closing image,
            'otsu_inv': OTSU Binary Inverted image
        }
    """
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Adaptive Threshold
    adaptive = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    # OTSU Binary
    _, otsu_binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Morphology Closing
    kernel = np.ones((3, 3), np.uint8)
    closing = cv2.morphologyEx(otsu_binary, cv2.MORPH_CLOSE, kernel)
    
    # OTSU Binary Inverted
    _, otsu_inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    return {
        'adaptive': adaptive,
        'closing': closing,
        'otsu_inv': otsu_inv
    }


def classify_all_bars(image: np.ndarray, matched_results: list[dict], 
                     use_multiple_methods: bool = True) -> list[dict]:
    """Classify bar graph colors for all matched results.
    
    Args:
        image: Image array (BGR format)
        matched_results: Result list from match_quarters_with_numbers
        use_multiple_methods: True to use all 3 methods, False to use legacy method
        
    Returns:
        Result list with bar graph color information added
    """
    if use_multiple_methods:
        # Generate preprocessed images (once only)
        preprocessed = preprocess_images_for_classification(image)
        
        classified_results = []
        
        for result in matched_results:
            classification = classify_bar_with_multiple_methods(
                image,
                preprocessed['adaptive'],
                preprocessed['closing'],
                preprocessed['otsu_inv'],
                result['quarter_box'],
                result['number_box']
            )
            
            classified_results.append({
                **result,
                'bar_color': classification['bar_color'],
                'bar_confidence': classification['confidence'],
                'bar_votes': classification['votes'],
                'bar_methods': classification['methods']
            })
        
        return classified_results
    else:
        # Use legacy method
        classified_results = []
        
        for result in matched_results:
            bar_color = classify_bar_color(
                image,
                result['quarter_box'],
                result['number_box']
            )
            
            classified_results.append({
                **result,
                'bar_color': bar_color
            })
        
        return classified_results

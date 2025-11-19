"""Module for matching quarter (Q) patterns and numbers (EPS) based on coordinates."""

import re
import math


def normalize_quarter_text(text: str) -> str:
    """Normalize Q pattern text.
    
    OCR misrecognition handling:
    - Q -> O, 0 (when Q is recognized as O or 0)
    - 1 -> I, l (when 1 is recognized as I or l)
    
    Args:
        text: Original text
        
    Returns:
        Normalized text
    """
    # Convert O or 0 recognized as Q to Q
    text = re.sub(r'^[O0](?=[1-4])', 'Q', text, flags=re.IGNORECASE)
    
    # Convert I or l recognized as 1 to 1 (only when following Q)
    text = re.sub(r'Q([Il])(?=\d)', r'Q1', text, flags=re.IGNORECASE)
    
    return text


def extract_quarter_pattern(text: str) -> str | None:
    """Extract Q(1-4)YY pattern from text.
    
    Args:
        text: Original text
        
    Returns:
        Normalized quarter string (e.g., "Q1'17") or None
    """
    # Normalize
    normalized = normalize_quarter_text(text)
    
    # Pattern: Q1'17, Q2'18, etc.
    pattern = r"Q([1-4])'(\d{2})"
    match = re.search(pattern, normalized, re.IGNORECASE)
    if match:
        quarter = match.group(1)
        year = match.group(2)
        return f"Q{quarter}'{year}"
    
    # Pattern: Q1 2017, Q2 2018, etc.
    pattern = r"Q([1-4])\s+20(\d{2})"
    match = re.search(pattern, normalized, re.IGNORECASE)
    if match:
        quarter = match.group(1)
        year = match.group(2)
        return f"Q{quarter}'{year}"
    
    # Pattern: Q114, Q214, etc. (when OCR recognizes Q1'14 as Q114)
    pattern = r"Q([1-4])(\d{2})"
    match = re.search(pattern, normalized, re.IGNORECASE)
    if match:
        quarter = match.group(1)
        year = match.group(2)
        # Check if year is in reasonable range (14-99 or 00-25)
        if 14 <= int(year) <= 99 or 0 <= int(year) <= 25:
            return f"Q{quarter}'{year}"
    
    # Pattern: 0114, 0214, etc. (when OCR recognizes Q1'14 as 0114)
    pattern = r"[0Oo]([1-4])(\d{2})"
    match = re.search(pattern, normalized)
    if match:
        quarter = match.group(1)
        year = match.group(2)
        # Check if year is in reasonable range (14-99 or 00-25)
        if 14 <= int(year) <= 99 or 0 <= int(year) <= 25:
            return f"Q{quarter}'{year}"
    
    # Pattern: Q1i7y, Q2i7y, etc. (when OCR misrecognizes Q1'17)
    pattern = r"Q([1-4])[iIl1](\d)[yi]"
    match = re.search(pattern, normalized, re.IGNORECASE)
    if match:
        quarter = match.group(1)
        year_digit = match.group(2)
        # Convert year to 2 digits (7 -> 17, 8 -> 18, etc.)
        if year_digit in ['7', '8', '9']:
            year = f"1{year_digit}"
        else:
            year = f"2{year_digit}"
        return f"Q{quarter}'{year}"
    
    return None


def extract_number(text: str) -> float | None:
    """Extract number from text.
    
    Args:
        text: Text containing numbers
        
    Returns:
        Extracted number or None
    """
    # Remove commas and minus signs, then extract number
    cleaned = text.replace(',', '').replace('-', '')
    
    # Pattern for numbers with decimal points
    pattern = r'-?\d+\.?\d*'
    match = re.search(pattern, cleaned)
    
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    
    return None


def calculate_distance(box1: dict, box2: dict) -> float:
    """Calculate distance between two boxes (center point based).
    
    Args:
        box1: First box (includes left, top, width, height)
        box2: Second box (includes left, top, width, height)
        
    Returns:
        Euclidean distance
    """
    center1_x = box1['left'] + box1['width'] / 2
    center1_y = box1['top'] + box1['height'] / 2
    
    center2_x = box2['left'] + box2['width'] / 2
    center2_y = box2['top'] + box2['height'] / 2
    
    return math.sqrt((center1_x - center2_x) ** 2 + (center1_y - center2_y) ** 2)


def is_same_y_range(box1: dict, box2: dict, y_tolerance: float = 20.0) -> bool:
    """Check if two boxes are in the same y range.
    
    Args:
        box1: First box
        box2: Second box
        y_tolerance: y coordinate tolerance (pixels)
        
    Returns:
        True if in same y range
    """
    # Compare center y coordinates of boxes
    center1_y = box1['top'] + box1['height'] / 2
    center2_y = box2['top'] + box2['height'] / 2
    
    return abs(center1_y - center2_y) <= y_tolerance


def find_quarters_at_bottom(ocr_results: list[dict], bottom_percent: float = 0.3) -> list[dict]:
    """Find Q patterns at the bottom.
    
    Args:
        ocr_results: OCR result list (each item includes text, left, top, width, height)
        bottom_percent: Ratio considered as bottom (0.3 = bottom 30%)
        
    Returns:
        List of Q pattern boxes at bottom
    """
    if not ocr_results:
        return []
    
    # Calculate maximum y coordinate of image (bottom of lowest box)
    max_y = max(box['top'] + box['height'] for box in ocr_results)
    bottom_threshold = max_y - (max_y * bottom_percent)
    
    quarter_boxes = []
    
    for box in ocr_results:
        # Check if in bottom region
        box_bottom = box['top'] + box['height']
        if box_bottom >= bottom_threshold:
            # Check if Q pattern
            quarter = extract_quarter_pattern(box['text'])
            if quarter:
                quarter_boxes.append({
                    **box,
                    'quarter': quarter
                })
    
    # Sort by x coordinate (left to right)
    quarter_boxes.sort(key=lambda x: x['left'])
    
    return quarter_boxes


def find_nearest_number_in_y_range(quarter_box: dict, ocr_results: list[dict], 
                                   y_tolerance: float = 1000.0,
                                   x_tolerance: float = 10.0) -> dict | None:
    """Find nearest number within same y range.
    
    Args:
        quarter_box: Quarter box
        ocr_results: OCR result list
        y_tolerance: y coordinate tolerance (maximum distance to numbers above Q box)
        x_tolerance: x coordinate tolerance (only consider numbers at similar x position, very small)
        
    Returns:
        Nearest number box or None
    """
    candidate_numbers = []
    
    # Center coordinates of Q box
    q_center_x = quarter_box['left'] + quarter_box['width'] / 2
    q_center_y = quarter_box['top'] + quarter_box['height'] / 2
    
    for box in ocr_results:
        # Exclude same box (compare by coordinates)
        if (box['left'] == quarter_box['left'] and 
            box['top'] == quarter_box['top'] and
            box['width'] == quarter_box['width'] and
            box['height'] == quarter_box['height']):
            continue
        
        # Exclude text containing Q pattern
        if extract_quarter_pattern(box['text']) is not None:
            continue
        
        # Check if number
        number = extract_number(box['text'])
        if number is None:
            continue
        
        # Center coordinates of box
        box_center_x = box['left'] + box['width'] / 2
        box_center_y = box['top'] + box['height'] / 2
        
        # Check if above Q box (y coordinate should be smaller)
        if box_center_y >= q_center_y:
            continue
        
        # Calculate y difference
        y_diff = q_center_y - box_center_y
        if y_diff > y_tolerance:  # Exclude if too far above
            continue
        
        # Check if x coordinate is in similar range (very strict)
        x_diff = abs(box_center_x - q_center_x)
        if x_diff > x_tolerance:
            continue
        
        # Exclude large numbers like years (>= 2000)
        if number >= 2000:
            continue
        
        # Calculate distance (weight x difference much more)
        distance = math.sqrt(x_diff ** 2 * 10 + y_diff ** 2 * 0.1)  # 10x weight on x difference
        
        candidate_numbers.append({
            **box,
            'number': number,
            'distance': distance,
            'x_diff': x_diff,
            'y_diff': y_diff
        })
    
    if not candidate_numbers:
        return None
    
    # Sort by distance (closest first)
    candidate_numbers.sort(key=lambda x: x['distance'])
    
    return candidate_numbers[0]


def match_quarters_with_numbers(ocr_results: list[dict], 
                                bottom_percent: float = 0.3,
                                y_tolerance: float = 1000.0,
                                x_tolerance: float = 10.0) -> list[dict]:
    """Match Q patterns at bottom with nearest numbers within same y range.
    
    Args:
        ocr_results: OCR result list (each item includes text, left, top, width, height)
        bottom_percent: Ratio considered as bottom
        y_tolerance: y coordinate tolerance (maximum distance to numbers above Q box, large value)
        x_tolerance: x coordinate tolerance (only consider numbers at similar x position, small value)
        
    Returns:
        List of matched quarter-number pairs [{'quarter': 'Q1'17', 'eps': 27.85, ...}, ...]
    """
    # Find Q patterns at bottom
    quarter_boxes = find_quarters_at_bottom(ocr_results, bottom_percent)
    
    if not quarter_boxes:
        return []
    
    matched_results = []
    
    for quarter_box in quarter_boxes:
        # Find nearest number within same y range
        nearest_number_box = find_nearest_number_in_y_range(
            quarter_box, ocr_results, y_tolerance, x_tolerance
        )
        
        if nearest_number_box:
            matched_results.append({
                'quarter': quarter_box['quarter'],
                'eps': nearest_number_box['number'],
                'quarter_box': {
                    'text': quarter_box['text'],
                    'left': quarter_box['left'],
                    'top': quarter_box['top'],
                    'width': quarter_box['width'],
                    'height': quarter_box['height']
                },
                'number_box': {
                    'text': nearest_number_box['text'],
                    'left': nearest_number_box['left'],
                    'top': nearest_number_box['top'],
                    'width': nearest_number_box['width'],
                    'height': nearest_number_box['height']
                },
                'distance': nearest_number_box['distance']
            })
    
    return matched_results

"""Module for parsing quarters and values."""

import re
from datetime import datetime


def parse_quarter(text: str) -> str | None:
    """Extract quarter information from text.
    
    Args:
        text: Text containing quarter (e.g., "Q1'17", "Q1 2017", "Q114")
        
    Returns:
        Quarter string (e.g., "Q1'17") or None
    """
    # Pattern: Q1'17, Q2'18, etc.
    pattern = r"Q([1-4])'(\d{2})"
    match = re.search(pattern, text)
    if match:
        quarter = match.group(1)
        year = match.group(2)
        return f"Q{quarter}'{year}"
    
    # Pattern: Q1 2017, Q2 2018, etc.
    pattern = r"Q([1-4])\s+20(\d{2})"
    match = re.search(pattern, text)
    if match:
        quarter = match.group(1)
        year = match.group(2)
        return f"Q{quarter}'{year}"
    
    # Pattern: Q114, Q214, etc. (when OCR recognizes Q1'14 as Q114)
    pattern = r"Q([1-4])(\d{2})"
    match = re.search(pattern, text)
    if match:
        quarter = match.group(1)
        year = match.group(2)
        # Check if year is in reasonable range (14-99 or 00-25)
        if 14 <= int(year) <= 99 or 0 <= int(year) <= 25:
            return f"Q{quarter}'{year}"
    
    # Pattern: 0114, 0214, etc. (when OCR recognizes Q1'14 as 0114, Q recognized as 0 or O)
    pattern = r"[0Oo]([1-4])(\d{2})"
    match = re.search(pattern, text)
    if match:
        quarter = match.group(1)
        year = match.group(2)
        # Check if year is in reasonable range (14-99 or 00-25)
        if 14 <= int(year) <= 99 or 0 <= int(year) <= 25:
            return f"Q{quarter}'{year}"
    
    # Pattern: Q1i7y, Q2i7y, etc. (when OCR misrecognizes Q1'17)
    pattern = r"Q([1-4])[iIl1](\d)[yi]"
    match = re.search(pattern, text, re.IGNORECASE)
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


def parse_number(text: str) -> float | None:
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


def extract_quarter_eps_pairs(text: str) -> list[dict]:
    """Extract quarter and EPS pairs from text.
    
    Args:
        text: Full text extracted by OCR
        
    Returns:
        List of dictionaries containing quarter and EPS information
    """
    lines = text.split('\n')
    results = []
    
    # Combine all lines into one string to find patterns
    full_text = ' '.join(lines)
    
    # Find quarter patterns (Q114, 0114, O114, etc.)
    quarter_patterns = [
        r"Q([1-4])(\d{2})",  # Q114
        r"[0Oo]([1-4])(\d{2})",  # 0114, O114
        r"Q([1-4])'(\d{2})",  # Q1'14
    ]
    
    found_quarters = []
    for pattern in quarter_patterns:
        for match in re.finditer(pattern, full_text):
            quarter_num = match.group(1)
            year = match.group(2)
            # Check if year is in reasonable range
            if 14 <= int(year) <= 99 or 0 <= int(year) <= 25:
                quarter_str = f"Q{quarter_num}'{year}"
                if quarter_str not in [q['quarter'] for q in found_quarters]:
                    found_quarters.append({
                        'quarter': quarter_str,
                        'pos': match.start()
                    })
    
    # Find numbers around each quarter
    for quarter_info in found_quarters:
        quarter = quarter_info['quarter']
        pos = quarter_info['pos']
        
        # Extract text around quarter information (200 chars before and after)
        start = max(0, pos - 200)
        end = min(len(full_text), pos + 200)
        context = full_text[start:end]
        
        # Find number patterns (likely EPS value range)
        number_pattern = r'\b(\d+\.?\d*)\b'
        numbers = re.findall(number_pattern, context)
        
        for num_str in numbers:
            try:
                num = float(num_str)
                # Check EPS value range (values between 10-1000)
                if 10 <= num <= 1000:
                    results.append({
                        'quarter': quarter,
                        'eps': num
                    })
                    break  # Use only first valid number
            except ValueError:
                continue
    
    # Remove duplicates
    seen = set()
    unique_results = []
    for r in results:
        key = (r['quarter'], round(r['eps'], 2))
        if key not in seen:
            seen.add(key)
            unique_results.append(r)
    
    return unique_results


def extract_from_boxes(boxes: list[dict]) -> list[dict]:
    """Extract quarter and EPS pairs from box information.
    
    Args:
        boxes: List of box information extracted by extract_text_with_boxes
        
    Returns:
        List of dictionaries containing quarter and EPS information
    """
    results = []
    
    # Sort boxes by y coordinate (top to bottom)
    sorted_boxes = sorted(boxes, key=lambda x: (x['top'], x['left']))
    
    # Combine adjacent boxes to form text
    combined_texts = []
    for i, box in enumerate(sorted_boxes):
        text = box['text'].strip()
        if not text:
            continue
        
        # If starts with Q, try combining with next boxes
        if text == 'Q' or text.startswith('Q'):
            # Check next few boxes (if on same row)
            combined = text
            for j in range(i + 1, min(i + 5, len(sorted_boxes))):
                next_box = sorted_boxes[j]
                # Check if on same row (small y coordinate difference)
                if abs(next_box['top'] - box['top']) < box['height'] * 2:
                    combined += next_box['text'].strip()
                else:
                    break
            
            quarter = parse_quarter(combined)
            if quarter:
                combined_texts.append({
                    'text': combined,
                    'quarter': quarter,
                    'top': box['top'],
                    'left': box['left']
                })
                continue
        
        # If not already combined, add as is
        quarter = parse_quarter(text)
        if quarter:
            combined_texts.append({
                'text': text,
                'quarter': quarter,
                'top': box['top'],
                'left': box['left']
            })
    
    # Match quarter information with numbers
    for quarter_info in combined_texts:
        quarter = quarter_info['quarter']
        quarter_y = quarter_info['top']
        
        # Find numbers on same row or row below
        for box in sorted_boxes:
            # Find numbers near same column as quarter info box
            if abs(box['left'] - quarter_info['left']) < 200:  # Near same column
                # Numbers below quarter info (y coordinate is larger)
                if box['top'] > quarter_y - 50:  # Small margin
                    number = parse_number(box['text'])
                    if number is not None and 10 <= number <= 1000:  # EPS value range
                        results.append({
                            'quarter': quarter,
                            'eps': number
                        })
                        break  # Use only first matching number
    
    # Also try legacy method (extract both quarter and number from single box)
    for box in sorted_boxes:
        text = box['text']
        quarter = parse_quarter(text)
        if quarter:
            number = parse_number(text)
            if number is not None:
                # Remove duplicates
                if not any(r['quarter'] == quarter and abs(r['eps'] - number) < 0.01 
                          for r in results):
                    results.append({
                        'quarter': quarter,
                        'eps': number
                    })
    
    return results


def get_report_date_from_filename(filename: str) -> str:
    """Extract report date from filename.
    
    Args:
        filename: Filename (e.g., "20251031-6.png")
        
    Returns:
        Date string (e.g., "2025-10-31")
    """
    # Extract date part from filename (YYYYMMDD format)
    match = re.search(r'(\d{8})', filename)
    if match:
        date_str = match.group(1)
        try:
            date = datetime.strptime(date_str, '%Y%m%d')
            return date.strftime('%Y-%m-%d')
        except ValueError:
            return filename
    
    return filename


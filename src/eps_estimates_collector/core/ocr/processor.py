"""Main processor for extracting quarters and values from chart images."""

import logging
from datetime import datetime, timedelta
from pathlib import Path

import cv2
import pandas as pd

from src.eps_estimates_collector.utils.csv_storage import read_csv
from src.eps_estimates_collector.utils.cloudflare import read_csv_from_cloud
from .bar_classifier import classify_all_bars
from .coordinate_matcher import match_quarters_with_numbers
from .google_vision_processor import extract_text_from_image, extract_text_with_boxes
from .parser import (
    extract_quarter_eps_pairs,
    get_report_date_from_filename
)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def process_image(image_path: Path) -> list[dict]:
    """Extract quarter and EPS information from a single image.
    
    Args:
        image_path: Image file path
        
    Returns:
        List of dictionaries containing quarter and EPS information
    """
    try:
        # Perform OCR
        ocr_results = extract_text_with_boxes(image_path)
        logger.debug(f"OCR results count: {len(ocr_results)}")
        
        if not ocr_results:
            logger.warning(f"No OCR results for image: {image_path}")
            return []
        
        # Coordinate-based matching
        matched_results = match_quarters_with_numbers(ocr_results)
        logger.debug(f"Matched results count: {len(matched_results)}")
        
        # Bar graph classification
        image = cv2.imread(str(image_path))
        if image is None:
            logger.error(f"Cannot read image: {image_path}")
            return []
        
        matched_results = classify_all_bars(
            image,
            matched_results,
            use_multiple_methods=True
        )
        
        if not matched_results:
            logger.warning(f"No matched results for image: {image_path}")
            return []
        
        # Add report date
        report_date = get_report_date_from_filename(image_path.name)
        
        # Organize results
        processed_results = []
        for result in matched_results:
            processed_result = {
                'report_date': report_date,
                'quarter': result.get('quarter', ''),
                'eps': result.get('eps', 0.0),
                'is_estimate': True  # Values extracted from images are considered estimates
            }
            
            # Add bar graph classification information (if available)
            if 'bar_color' in result:
                processed_result['bar_color'] = result['bar_color']
            if 'bar_confidence' in result:
                processed_result['bar_confidence'] = result['bar_confidence']
            
            processed_results.append(processed_result)
        
        return processed_results
    
    except Exception as e:
        logger.error(f"Error processing image: {image_path} - {e}", exc_info=True)
        return []


def _load_existing_data() -> tuple[pd.DataFrame | None, pd.DataFrame | None, set[str]]:
    """Load existing data from public URL and get processed dates."""
    existing_df = read_csv_from_cloud("extracted_estimates.csv")
    existing_confidence_df = read_csv_from_cloud("extracted_estimates_confidence.csv")
    processed_dates = set()
    
    if existing_df is not None and not existing_df.empty:
        existing_df = existing_df.drop(columns=['Confidence'], errors='ignore')
        existing_df['Report_Date'] = pd.to_datetime(existing_df['Report_Date'])
        processed_dates = set(existing_df['Report_Date'].dt.strftime('%Y%m%d'))
    
    return existing_df, existing_confidence_df, processed_dates


def _get_images_to_process(directory: Path, processed_dates: set[str], limit: int | None) -> list[Path]:
    """Get list of images to process (exclude already processed ones)."""
    all_images = sorted(directory.glob('*.png'))
    new_images = [img for img in all_images if img.stem not in processed_dates]
    
    if limit:
        new_images = new_images[:limit]
    
    return new_images


def _merge_data(current_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
    """Merge new data with existing data."""
    if current_df.empty:
        return new_df.copy()
    
    if new_df.empty:
        return current_df.copy()
    
    # Create copies to avoid modifying originals
    current_copy = current_df.copy()
    new_copy = new_df.copy()
    
    # Ensure Report_Date is datetime (both should already be datetime, but ensure consistency)
    current_copy['Report_Date'] = pd.to_datetime(current_copy['Report_Date'])
    new_copy['Report_Date'] = pd.to_datetime(new_copy['Report_Date'])
    
    # Debug: log counts before merge
    logger.debug(f"Merging: current={len(current_copy)} records, new={len(new_copy)} records")
    
    # Concat and deduplicate (keep='last' means new data overwrites old for same date)
    result_df = pd.concat([current_copy, new_copy], ignore_index=True)\
        .drop_duplicates(subset=['Report_Date'], keep='last')\
        .sort_values('Report_Date')\
        .reset_index(drop=True)
    
    # Debug: log count after merge
    logger.debug(f"After merge: {len(result_df)} records")
    
    # Sort quarter columns
    quarter_cols = sorted([c for c in result_df.columns if c != 'Report_Date'], key=_parse_quarter_for_sort)
    return result_df[['Report_Date'] + quarter_cols]


def process_directory(directory: Path, limit: int | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Process all images in a directory.
    
    Args:
        directory: Directory path containing images
        limit: Maximum number of images to process (None to process all)
        
    Returns:
        Tuple of (main DataFrame, confidence DataFrame)
    """
    # Load existing data
    existing_df, existing_confidence_df, processed_dates = _load_existing_data()
    
    # Get images to process
    image_files = _get_images_to_process(directory, processed_dates, limit)
    
    if not image_files:
        if (existing_df is None or existing_df.empty) and not list(directory.glob('*.png')):
            print(f"\n⚠️  No PNG images found in {directory}")
        empty_df = pd.DataFrame(columns=['Report_Date'])
        return (existing_df if existing_df is not None and not existing_df.empty else empty_df,
                existing_confidence_df if existing_confidence_df is not None and not existing_confidence_df.empty else empty_df)
    
    # Process images
    print(f"\n🔄 Processing {len(image_files)} new images...")
    
    # Initialize current_df with existing data (deep copy to avoid modification)
    if existing_df is not None and not existing_df.empty:
        current_df = existing_df.copy(deep=True)
        # Ensure Report_Date is datetime (should already be, but ensure consistency)
        current_df['Report_Date'] = pd.to_datetime(current_df['Report_Date'])
        print(f"📋 Loaded {len(current_df)} existing records")
        logger.debug(f"Existing dates: {sorted(current_df['Report_Date'].dt.strftime('%Y-%m-%d').tolist()[:5])}...")
    else:
        current_df = pd.DataFrame()
        print("📋 No existing data found")
    
    all_long_results = []
    
    for idx, image_path in enumerate(image_files, 1):
        print(f"[{idx}/{len(image_files)}] {image_path.name}", end=" ... ")
        
        try:
            results = process_image(image_path)
            if not results:
                print("⚠️  No data")
                continue
            
            all_long_results.extend(results)
            new_df = convert_to_wide_format(pd.DataFrame(results))
            
            # Debug: check before merge
            before_count = len(current_df)
            current_df = _merge_data(current_df, new_df)
            after_count = len(current_df)
            
            if after_count < before_count:
                logger.warning(f"Data loss detected: {before_count} -> {after_count} records")
            
            print("✅")
                
        except Exception as e:
            print(f"❌ {e}")
            logger.error(f"Error: {e}")
    
    print(f"\n📊 Complete: {len(current_df)} total records (existing: {len(existing_df) if existing_df is not None and not existing_df.empty else 0}, new: {len(image_files)})\n")
    
    # If no new data was processed, return existing data
    if current_df.empty and (existing_df is not None and not existing_df.empty):
        # Format existing data before returning
        existing_df_formatted = existing_df.copy()
        existing_df_formatted['Report_Date'] = pd.to_datetime(existing_df_formatted['Report_Date']).dt.strftime('%Y-%m-%d')
        existing_confidence_formatted = existing_confidence_df.copy() if existing_confidence_df is not None and not existing_confidence_df.empty else pd.DataFrame(columns=['Report_Date'])
        if not existing_confidence_formatted.empty:
            existing_confidence_formatted['Report_Date'] = pd.to_datetime(existing_confidence_formatted['Report_Date']).dt.strftime('%Y-%m-%d')
        return existing_df_formatted, existing_confidence_formatted
    
    if current_df.empty:
        empty_df = pd.DataFrame(columns=['Report_Date'])
        return empty_df, pd.DataFrame(columns=['Report_Date', 'Confidence'])
    
    # Calculate confidence for new data only
    confidence_df = _calculate_new_confidence(all_long_results, current_df) if all_long_results else None
    
    # Merge with existing confidence
    confidence_df = _merge_confidence(existing_confidence_df, confidence_df)
    
    # Format dates (ensure all dates are formatted consistently)
    if not current_df.empty:
        current_df['Report_Date'] = pd.to_datetime(current_df['Report_Date']).dt.strftime('%Y-%m-%d')
    if not confidence_df.empty:
        confidence_df['Report_Date'] = pd.to_datetime(confidence_df['Report_Date']).dt.strftime('%Y-%m-%d')
    
    return current_df, confidence_df


def _calculate_new_confidence(all_long_results: list, current_df: pd.DataFrame) -> pd.DataFrame | None:
    """Calculate confidence DataFrame for newly processed data."""
    if not all_long_results:
        return None
    
    df_long = pd.DataFrame(all_long_results)
    
    # Normalize report_date to datetime
    df_long['report_date'] = pd.to_datetime(df_long['report_date'])
    new_dates = set(df_long['report_date'].dt.strftime('%Y-%m-%d'))
    
    # Create copy to avoid modifying original
    df_copy = current_df.copy()
    df_copy['Report_Date'] = pd.to_datetime(df_copy['Report_Date'])
    new_df_wide = df_copy[df_copy['Report_Date'].dt.strftime('%Y-%m-%d').isin(new_dates)].copy()
    
    if new_df_wide.empty:
        logger.warning(f"No matching dates found. new_dates: {new_dates}, current_df dates: {df_copy['Report_Date'].dt.strftime('%Y-%m-%d').tolist()}")
        return None
    
    return calculate_confidence_dataframe(new_df_wide, df_long, df_copy)


def _merge_confidence(existing: pd.DataFrame | None, new: pd.DataFrame | None) -> pd.DataFrame:
    """Merge existing and new confidence DataFrames."""
    if existing is None or existing.empty:
        return new if new is not None and not new.empty else pd.DataFrame(columns=['Report_Date', 'Confidence'])
    
    if new is None or new.empty:
        return existing.copy()
    
    existing['Report_Date'] = pd.to_datetime(existing['Report_Date'])
    new['Report_Date'] = pd.to_datetime(new['Report_Date'])
    
    return pd.concat([existing, new], ignore_index=True)\
        .drop_duplicates(subset=['Report_Date'], keep='last')\
        .sort_values('Report_Date')\
        .reset_index(drop=True)


def convert_to_wide_format(df: pd.DataFrame) -> pd.DataFrame:
    """Convert Long format DataFrame to wide format.
    
    Args:
        df: Long format DataFrame (report_date, quarter, eps, ...)
        
    Returns:
        Wide format DataFrame (Report_Date, Q1'14, Q2'14, ..., Confidence)
    """
    if df.empty:
        return pd.DataFrame(columns=['Report_Date'])
    
    # Add * to EPS values (if bar_color is 'light', mark as estimate)
    df = df.copy()
    if 'bar_color' in df.columns:
        # Light bar graphs are marked as estimates (* added)
        df['eps_str'] = df.apply(
            lambda row: f"{row['eps']}*" if row.get('bar_color') == 'light' else str(row['eps']),
            axis=1
        )
    else:
        df['eps_str'] = df['eps'].astype(str)
    
    # Convert to wide format using pivot
    df_pivot = df.pivot_table(
        index='report_date',
        columns='quarter',
        values='eps_str',
        aggfunc='first'  # Use first value if multiple combinations exist
    )
    
    # Convert index to column
    df_pivot = df_pivot.reset_index()
    df_pivot.columns.name = None
    
    # Rename column: report_date -> Report_Date
    df_pivot = df_pivot.rename(columns={'report_date': 'Report_Date'})
    
    # Ensure Report_Date is datetime (for consistent merging)
    df_pivot['Report_Date'] = pd.to_datetime(df_pivot['Report_Date'])
    
    # Sort quarter columns (Q1'14, Q2'14, ... order)
    quarter_columns = sorted(
        [col for col in df_pivot.columns if col != 'Report_Date'],
        key=lambda x: _parse_quarter_for_sort(x)
    )
    
    # Column order: Report_Date, Q1'14, Q2'14, ...
    df_pivot = df_pivot[['Report_Date'] + quarter_columns]
    
    # Convert empty values to empty strings (display as empty cells in CSV)
    df_pivot = df_pivot.fillna('')
    
    return df_pivot


def calculate_confidence_dataframe(
    df_wide: pd.DataFrame, 
    df_long: pd.DataFrame,
    full_df_wide: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Calculate confidence DataFrame for new data."""
    consistency_df = full_df_wide if full_df_wide is not None else df_wide
    
    # Ensure Report_Date is datetime for comparison
    consistency_df['Report_Date'] = pd.to_datetime(consistency_df['Report_Date'])
    first_date = sorted(consistency_df['Report_Date'].unique())[0] if len(consistency_df) > 0 else None
    
    # Normalize df_long report_date to datetime for comparison
    df_long = df_long.copy()
    df_long['report_date'] = pd.to_datetime(df_long['report_date'])
    
    results = []
    for report_date in df_wide['Report_Date']:
        # Convert report_date to datetime for comparison
        report_date_dt = pd.to_datetime(report_date)
        date_data = df_long[df_long['report_date'] == report_date_dt]
        
        if date_data.empty:
            logger.warning(f"No matching data for date {report_date} in df_long")
            results.append({'Report_Date': report_date, 'Confidence': 0.0})
            continue
        
        bar_score = _calculate_bar_score(date_data)
        consistency_score = 100.0 if report_date_dt == first_date else \
            calculate_consistency_with_previous_week_wide(str(report_date_dt.date()), date_data, consistency_df)
        
        confidence = round((bar_score * 0.5) + (consistency_score * 0.5), 1)
        results.append({'Report_Date': report_date, 'Confidence': confidence})
    
    return pd.DataFrame(results)


def _calculate_bar_score(date_data: pd.DataFrame) -> float:
    """Calculate bar classification confidence score."""
    if 'bar_confidence' not in date_data.columns:
        return 0.0
    
    scores = {'high': 100.0, 'medium': 67.0, 'low': 33.0}
    bar_scores = [scores.get(conf, 0.0) for conf in date_data['bar_confidence']]
    return sum(bar_scores) / len(bar_scores) if bar_scores else 0.0


def calculate_consistency_with_previous_week_wide(
    current_date: str,
    current_data: pd.DataFrame,
    full_df_wide: pd.DataFrame
) -> float:
    """Calculate consistency with previous week (actuals only)."""
    try:
        current_dt = pd.to_datetime(current_date)
        full_df_wide['Report_Date'] = pd.to_datetime(full_df_wide['Report_Date'])
        
        previous_dates = full_df_wide[full_df_wide['Report_Date'] < current_dt]['Report_Date']
        if len(previous_dates) == 0:
            return 0.0
        
        previous_date = previous_dates.max()
        current_row = full_df_wide[full_df_wide['Report_Date'] == current_dt]
        previous_row = full_df_wide[full_df_wide['Report_Date'] == previous_date]
        
        if current_row.empty or previous_row.empty:
            return 0.0
        
        current_row = current_row.iloc[0]
        previous_row = previous_row.iloc[0]
        
        # Get actual quarters (dark bars)
        actual_quarters = set()
        if 'bar_color' in current_data.columns:
            actual_quarters = set(current_data[current_data['bar_color'] == 'dark']['quarter'].unique())
        
        if not actual_quarters:
            return 0.0
        
        # Compare values
        matches = 0
        total = 0
        
        for quarter in actual_quarters:
            if quarter not in full_df_wide.columns:
                continue
            
            curr_val = str(current_row.get(quarter, ''))
            prev_val = str(previous_row.get(quarter, ''))
            
            if not curr_val or '*' in curr_val or not prev_val or '*' in prev_val:
                continue
            
            try:
                curr_eps = float(curr_val.replace('*', ''))
                prev_eps = float(prev_val.replace('*', ''))
                total += 1
                
                if abs(curr_eps - prev_eps) / max(abs(prev_eps), 0.01) <= 0.2:
                    matches += 1
            except (ValueError, TypeError):
                continue
        
        return (matches / total * 100.0) if total > 0 else 0.0
    
    except Exception as e:
        logger.warning(f"Error calculating consistency ({current_date}): {e}")
        return 0.0


def _parse_quarter_for_sort(quarter: str) -> tuple[int, int]:
    """Convert quarter string to tuple for sorting.
    
    Args:
        quarter: Quarter string (e.g., "Q1'14", "Q2'15")
        
    Returns:
        (year, quarter) tuple (e.g., (2014, 1), (2015, 2))
    """
    try:
        # Parse Q1'14 format
        if "'" in quarter:
            q_part, year_part = quarter.split("'")
            q_num = int(q_part[1:])  # Q1 -> 1
            year = 2000 + int(year_part)  # '14 -> 2014
        else:
            # Parse Q114 format
            q_num = int(quarter[1])
            year = 2000 + int(quarter[2:4])
        
        return (year, q_num)
    except (ValueError, IndexError):
        # Return (0, 0) on parse failure to sort at the beginning
        return (0, 0)
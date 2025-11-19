"""P/E ratio calculation from EPS estimates."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal
import re

import pandas as pd


def _parse_quarter_to_date(quarter_str: str) -> datetime | None:
    """Parse quarter string (e.g., "Q1'14") to datetime.
    
    Args:
        quarter_str: Quarter string like "Q1'14", "Q2'15", etc.
        
    Returns:
        Datetime representing the start of the quarter, or None
    """
    match = re.match(r"Q([1-4])'(\d{2})", quarter_str)
    if not match:
        return None
    
    quarter = int(match.group(1))
    year_short = int(match.group(2))
    
    # Convert 2-digit year to 4-digit year
    # FactSet data starts from 2016, so all quarters are in 2000s
    # Standard conversion: 00-49 -> 2000-2049, 50-99 -> 1950-1999
    # For FactSet data (2014+), we use 2000+ for all cases
    if year_short >= 50:
        # Years 50-99: 1950-1999 (unlikely for FactSet data, but handle for completeness)
        year = 1900 + year_short
    else:
        # Years 00-49: 2000-2049 (covers all FactSet data from 2014+)
        year = 2000 + year_short
    
    # Calculate month (Q1=Jan, Q2=Apr, Q3=Jul, Q4=Oct)
    month = (quarter - 1) * 3 + 1
    
    return datetime(year, month, 1)


def _get_quarter_eps_sum(
    row: pd.Series,
    quarter_cols: list[str],
    report_date: datetime,
    type: Literal['forward', 'trailing-like', 'mix']
) -> float | None:
    """Calculate 4-quarter EPS sum based on type.
    
    Args:
        row: DataFrame row with quarter columns
        quarter_cols: List of quarter column names
        report_date: Report date
        type: Type of EPS calculation:
            - 'forward': Q[1:5] - Next 4 quarters after report_date (indices 1-4)
            - 'mix': Q[0:4] - Report date and next 3 quarters (indices 0-3)
            - 'trailing-like': Q[-3:1] - Last 3 quarters before and report date (indices -3 to 0)
        
    Returns:
        4-quarter EPS sum, or None if insufficient data
    """
    # Parse all quarters and their dates
    quarter_data = []
    for col in quarter_cols:
        val = row[col]
        if pd.notna(val) and str(val).strip() and str(val) != '':
            try:
                eps_val = float(str(val).replace('*', '').strip())
                if eps_val > 0:
                    quarter_date = _parse_quarter_to_date(col)
                    if quarter_date:
                        quarter_data.append({
                            'quarter': col,
                            'eps': eps_val,
                            'date': quarter_date
                        })
            except (ValueError, TypeError):
                continue
    
    if not quarter_data:
        return None
    
    # Sort by date
    quarter_data.sort(key=lambda x: x['date'])
    
    # Find report_date position in sorted quarters
    report_idx = None
    for i, q in enumerate(quarter_data):
        if q['date'] >= report_date:
            report_idx = i
            break
    
    # If report_date is after all quarters, use last index
    if report_idx is None:
        report_idx = len(quarter_data)
    
    if type == 'forward':
        # Q[1:5] - Next 4 quarters after report_date (indices 1-4 relative to report_date)
        start_idx = report_idx + 1  # Skip first (index 1)
        end_idx = start_idx + 4     # Take 4 quarters (indices 1-4)
        
        if end_idx <= len(quarter_data):
            return sum(q['eps'] for q in quarter_data[start_idx:end_idx])
        elif start_idx < len(quarter_data):
            return sum(q['eps'] for q in quarter_data[start_idx:])
        else:
            return None
    
    elif type == 'mix':
        # Q[0:4] - Report date and next 3 quarters (indices 0-3 relative to report_date)
        start_idx = report_idx      # Include report_date quarter (index 0)
        end_idx = start_idx + 4     # Take 4 quarters total (indices 0-3)
        
        if end_idx <= len(quarter_data):
            return sum(q['eps'] for q in quarter_data[start_idx:end_idx])
        elif start_idx < len(quarter_data):
            return sum(q['eps'] for q in quarter_data[start_idx:])
        else:
            return None
    
    elif type == 'trailing-like':
        # Q[-3:1] - Last 3 quarters before and report date (indices -3 to 0 relative to report_date)
        start_idx = max(0, report_idx - 3)  # Start 3 quarters before report_date
        end_idx = report_idx + 1            # Include report_date quarter (index 0)
        
        if start_idx < len(quarter_data) and end_idx <= len(quarter_data):
            return sum(q['eps'] for q in quarter_data[start_idx:end_idx])
        elif start_idx < len(quarter_data):
            return sum(q['eps'] for q in quarter_data[start_idx:])
        else:
            return None
    
    return None


def calculate_pe_ratio(
    csv_path: Path | str,
    price_data: pd.DataFrame | dict | None = None,
    type: Literal['forward', 'mix', 'trailing-like'] = 'forward',
    output_csv: Path | str | None = None
) -> pd.DataFrame:
    """Calculate P/E ratios from EPS estimates.
    
    Calculates Price-to-Earnings (P/E) ratios using 4-quarter EPS sums and stock prices.
    EPS is calculated as the sum of 4 quarters based on the type:
    - forward: Q[1:5] - Next 4 quarters after report date (skip first, take next 4)
    - mix: Q[0:4] - Report date and next 3 quarters (include report date, take next 3)
    - trailing-like: Q[-3:1] - Last 3 quarters before and report date (take 3 before, include report date)
    
    Args:
        csv_path: Path to CSV file containing EPS estimates (from extract_eps)
        price_data: Stock price data. Can be:
            - DataFrame with columns: Date (or Report_Date), Price
            - Dict mapping dates (YYYY-MM-DD) to prices
            - None: Returns template DataFrame showing required format
        type: Type of P/E ratio to calculate:
            - 'forward': Q[1:5] - Next 4 quarters after report date (skip first, take next 4)
            - 'mix': Q[0:4] - Report date and next 3 quarters (include report date, take next 3)
            - 'trailing-like': Q[-3:1] - Last 3 quarters before and report date (take 3 before, include report date)
        output_csv: Optional path to save results as CSV file
        
    Returns:
        DataFrame with P/E ratios:
        - Report_Date: Report date
        - Price_Date: Date of price used (most recent price on or before report_date)
        - Price: Stock price used
        - EPS_4Q_Sum: 4-quarter EPS sum used for calculation
        - PE_Ratio: Calculated P/E ratio (Price / EPS_4Q_Sum)
        - Type: Type of calculation ('forward', 'trailing-like', or 'mix')
        
    Note:
        Stock prices are matched to the most recent price on or before the report date.
        If output_csv is provided, results are automatically saved to CSV.
    """
    # Read EPS CSV
    if isinstance(csv_path, str):
        csv_path = Path(csv_path)
    
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    df_eps = pd.read_csv(csv_path)
    df_eps['Report_Date'] = pd.to_datetime(df_eps['Report_Date'])
    
    # If no price data provided, return template
    if price_data is None:
        print("⚠️  No price data provided. Returning template DataFrame.")
        print("   Please provide price_data as DataFrame or dict mapping dates to prices.")
        
        template = pd.DataFrame({
            'Report_Date': df_eps['Report_Date'],
            'PE_Ratio': None,
            'EPS_4Q_Sum': None,
            'Price': None,
            'Note': 'Price data required'
        })
        return template
    
    # Convert price_data to DataFrame if dict
    if isinstance(price_data, dict):
        price_df = pd.DataFrame([
            {'Date': k, 'Price': v} for k, v in price_data.items()
        ])
        price_df['Date'] = pd.to_datetime(price_df['Date'])
    else:
        price_df = price_data.copy()
        if 'Date' not in price_df.columns and 'Report_Date' in price_df.columns:
            price_df['Date'] = pd.to_datetime(price_df['Report_Date'])
        else:
            price_df['Date'] = pd.to_datetime(price_df['Date'])
    
    # Get quarter columns
    quarter_cols = [col for col in df_eps.columns if col != 'Report_Date']
    
    # Calculate P/E ratios
    results = []
    
    for _, row in df_eps.iterrows():
        report_date = row['Report_Date']
        
        # Find closest price (use price on or before report_date)
        price_candidates = price_df[price_df['Date'] <= report_date]
        if price_candidates.empty:
            # If no price before report_date, use closest price
            price_row = price_df.iloc[(price_df['Date'] - report_date).abs().argsort()[:1]]
        else:
            # Use most recent price before or on report_date
            price_row = price_candidates.iloc[[price_candidates['Date'].idxmax()]]
        
        if price_row.empty:
            continue
        
        price = float(price_row['Price'].iloc[0])
        price_date = price_row['Date'].iloc[0]
        
        # Calculate 4-quarter EPS sum based on type
        eps_sum = _get_quarter_eps_sum(row, quarter_cols, report_date, type)
        
        if eps_sum and eps_sum > 0:
            pe_ratio = price / eps_sum
            results.append({
                'Report_Date': report_date.strftime('%Y-%m-%d'),
                'Price_Date': price_date.strftime('%Y-%m-%d'),
                'Price': price,
                'EPS_4Q_Sum': eps_sum,
                'PE_Ratio': pe_ratio,
                'Type': type
            })
    
    if not results:
        return pd.DataFrame(columns=['Report_Date', 'Price_Date', 'Price', 'EPS_4Q_Sum', 'PE_Ratio', 'Type'])
    
    df_result = pd.DataFrame(results)
    
    # Save to CSV if output path provided
    if output_csv:
        if isinstance(output_csv, str):
            output_csv = Path(output_csv)
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        df_result.to_csv(output_csv, index=False)
        print(f"✅ P/E ratio data saved to: {output_csv}")
    
    return df_result


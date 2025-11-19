"""P/E ratio calculation from EPS estimates."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal
import re
import tempfile

import pandas as pd

from src.eps_estimates_collector.utils.csv_storage import read_csv


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
    type: Literal['forward', 'mix', 'trailing-like'] = 'forward'
) -> pd.DataFrame:
    """Calculate P/E ratios from EPS estimates using S&P 500 prices.
    
    Calculates Price-to-Earnings (P/E) ratios using 4-quarter EPS sums and S&P 500 stock prices.
    EPS is calculated as the sum of 4 quarters based on the type:
    - forward: Q[1:5] - Next 4 quarters after report date (skip first, take next 4)
    - mix: Q[0:4] - Report date and next 3 quarters (include report date, take next 3)
    - trailing-like: Q[-3:1] - Last 3 quarters before and report date (take 3 before, include report date)
    
    Args:
        type: Type of P/E ratio to calculate:
            - 'forward': Q[1:5] - Next 4 quarters after report date (skip first, take next 4)
            - 'mix': Q[0:4] - Report date and next 3 quarters (include report date, take next 3)
            - 'trailing-like': Q[-3:1] - Last 3 quarters before and report date (take 3 before, include report date)
        
    Returns:
        DataFrame with P/E ratios:
        - Report_Date: Report date
        - Price_Date: Date of price used (most recent price on or before report_date)
        - Price: S&P 500 stock price used
        - EPS_4Q_Sum: 4-quarter EPS sum used for calculation
        - PE_Ratio: Calculated P/E ratio (Price / EPS_4Q_Sum)
        - Type: Type of calculation ('forward', 'trailing-like', or 'mix')
        
    Note:
        Stock prices are matched to the most recent price on or before the report date.
        EPS data is always loaded from public URL.
        S&P 500 (^GSPC) data is automatically loaded from yfinance.
        Requires yfinance package: pip install yfinance or uv add yfinance
    """
    # Auto-load from public URL
    temp_path = Path(tempfile.gettempdir()) / "extracted_estimates.csv"
    df_eps = read_csv("extracted_estimates.csv", temp_path)
    
    if df_eps is None:
        raise FileNotFoundError(
            "CSV file not found in public URL. Please ensure extracted_estimates.csv "
            "exists at https://pub-62707afd3ebb422aae744c63c49d36a0.r2.dev/extracted_estimates.csv"
        )
    
    df_eps['Report_Date'] = pd.to_datetime(df_eps['Report_Date'])
    
    # Determine date range from EPS data (use actual CSV date range)
    min_date = df_eps['Report_Date'].min()
    max_date = df_eps['Report_Date'].max()
    start_date = min_date.strftime('%Y-%m-%d')
    end_date = max_date.strftime('%Y-%m-%d')
    
    # Auto-load S&P 500 price data
    try:
        import yfinance as yf
        print(f"📈 Loading S&P 500 price data from yfinance ({start_date} to {end_date})...")
        sp500 = yf.Ticker('^GSPC')
        hist = sp500.history(start=start_date, end=end_date)
        price_dict = {date.strftime('%Y-%m-%d'): float(close) for date, close in zip(hist.index, hist['Close'])}
        print(f"✅ Loaded {len(price_dict)} S&P 500 price points")
    except ImportError:
        raise ImportError(
            "yfinance is required for automatic S&P 500 price loading. "
            "Install it with: pip install yfinance or uv add yfinance"
        )
    except Exception as e:
        raise Exception(f"Failed to load S&P 500 price data: {e}")
    
    # Convert price_dict to DataFrame
    price_df = pd.DataFrame([
        {'Date': k, 'Price': v} for k, v in price_dict.items()
    ])
    price_df['Date'] = pd.to_datetime(price_df['Date'])
    
    # Get quarter columns
    quarter_cols = [col for col in df_eps.columns if col != 'Report_Date']
    
    # Use only dates that have price data (trading days only)
    df_eps_sorted = df_eps.sort_values('Report_Date')
    
    # Calculate P/E ratios for each price date
    results = []
    
    for _, price_row in price_df.iterrows():
        price_date = price_row['Date']
        price = float(price_row['Price'])
        
        # Find most recent EPS row on or before this price date
        eps_candidates = df_eps_sorted[df_eps_sorted['Report_Date'] <= price_date]
        if eps_candidates.empty:
            continue
        
        eps_row = eps_candidates.iloc[-1]
        report_date = eps_row['Report_Date']
        
        # Calculate 4-quarter EPS sum based on type (use report_date for EPS calculation)
        eps_sum = _get_quarter_eps_sum(eps_row, quarter_cols, report_date, type)
        
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
    return df_result


"""P/E ratio calculation from EPS estimates."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

# Type definitions
PE_RATIO_TYPE = Literal['forward', 'trailing']
import re
import tempfile

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import logging

# Suppress matplotlib font manager warnings
logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)

from ..utils.csv_storage import read_csv


class SP500:
    """S&P 500 Market Data with EPS and P/E ratio calculations.
    
    Loads and caches S&P 500 price data and EPS estimates data.
    Provides convenient methods to calculate P/E ratios and EPS.
    
    Example:
        >>> from factset_report_analyzer.analysis import SP500
        >>> sp500 = SP500()
        >>> 
        >>> # Get current P/E ratio
        >>> current = sp500.current_pe
        >>> print(f"P/E: {current['pe_ratio']:.2f}")
        >>> 
        >>> # Get P/E ratio for specific date
        >>> pe = sp500.pe_ratio(pd.Timestamp('2024-01-01'))
        >>> 
        >>> # Get EPS for specific date
        >>> eps = sp500.eps(pd.Timestamp('2024-01-01'))
    """
    
    def __init__(self):
        """Initialize and load S&P 500 and EPS data."""
        self._df_eps = None
        self._price_df = None
        self._type: PE_RATIO_TYPE = 'forward'  # Default to forward
        self._load_data()
    
    def set_type(self, type: PE_RATIO_TYPE) -> None:
        """Set the type for EPS and P/E ratio calculations.
        
        Args:
            type: 'forward' or 'trailing'
            
        Example:
            >>> sp500 = SP500()
            >>> sp500.set_type('trailing')
            >>> eps = sp500.eps  # Now returns trailing EPS
        """
        if type not in ['forward', 'trailing']:
            raise ValueError("type must be 'forward' or 'trailing'")
        self._type = type
    
    def _load_data(self):
        """Load EPS and S&P 500 price data."""
        print("📊 Loading S&P 500 data...")
        
        # Load EPS data
        temp_path = Path(tempfile.gettempdir()) / "extracted_estimates.csv"
        self._df_eps = read_csv("extracted_estimates.csv", temp_path)
        
        if self._df_eps is None:
            raise FileNotFoundError(
                "EPS data not found. Please ensure extracted_estimates.csv is available."
            )
        
        self._df_eps['Report_Date'] = pd.to_datetime(self._df_eps['Report_Date'])
        self._df_eps = self._df_eps.sort_values('Report_Date')
        print(f"  ✅ EPS data: {len(self._df_eps)} reports")
        
        # Load S&P 500 price data
        min_date = self._df_eps['Report_Date'].min().strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            import yfinance as yf
            ticker = yf.Ticker('^GSPC')
            hist = ticker.history(start=min_date, end=end_date)
            self._price_df = pd.DataFrame({
                'Date': hist.index,
                'Price': hist['Close'].values
            })
            self._price_df['Date'] = pd.to_datetime(self._price_df['Date']).dt.tz_localize(None)  # Remove timezone
            self._price_df = self._price_df.sort_values('Date')
            print(f"  ✅ Price data: {len(self._price_df)} trading days")
        except ImportError:
            raise ImportError(
                "yfinance is required. Install with: pip install yfinance or uv add yfinance"
            )
        except Exception as e:
            raise Exception(f"Failed to load S&P 500 price data: {e}")
    
    @property
    def price(self) -> pd.DataFrame:
        """Get all S&P 500 price data.
        
        Returns:
            DataFrame with Date and Price columns
            
        Example:
            >>> sp500 = SP500()
            >>> prices = sp500.price
            >>> print(prices.head())
        """
        return self._price_df[['Date', 'Price']].copy()
    
    @property
    def eps(self) -> pd.DataFrame:
        """Get all EPS data based on current type setting.
        
        Returns:
            DataFrame with Date and EPS columns
            
        Example:
            >>> sp500 = SP500()
            >>> eps_data = sp500.eps  # forward (default)
            >>> sp500.set_type('trailing')
            >>> eps_data = sp500.eps  # trailing
        """
        dates = self._price_df['Date']
        eps_values = calculate_eps_sum(self._df_eps, dates, self._type)
        return pd.DataFrame({
            'Date': dates,
            'EPS': eps_values
        })
    
    @property
    def pe_ratio(self) -> pd.DataFrame:
        """Get all P/E ratio data based on current type setting.
        
        Returns:
            DataFrame with Date, Price, EPS, PE_Ratio, Type
            
        Example:
            >>> sp500 = SP500()
            >>> pe_df = sp500.pe_ratio  # forward (default)
            >>> sp500.set_type('trailing')
            >>> pe_df = sp500.pe_ratio  # trailing
        """
        dates = self._price_df['Date']
        price_data = self._price_df.copy()
        price_data['EPS'] = calculate_eps_sum(self._df_eps, dates, self._type)
        price_data['PE_Ratio'] = price_data['Price'] / price_data['EPS']
        price_data['Type'] = self._type
        return price_data[['Date', 'Price', 'EPS', 'PE_Ratio', 'Type']].reset_index(drop=True)
    
    @property
    def current_pe(self) -> dict:
        """Get current P/E ratio (most recent date with valid data).
        
        Returns:
            Dict with date, price, eps, pe_ratio, type
            
        Example:
            >>> sp500 = SP500()
            >>> current = sp500.current_pe
            >>> print(f"Forward P/E: {current['pe_ratio']:.2f}")
        """
        pe_df = self.pe_ratio
        # Find last row with valid EPS
        valid_df = pe_df.dropna(subset=['EPS'])
        if valid_df.empty:
            return None
        
        latest = valid_df.iloc[-1]
        return {
            'date': latest['Date'],
            'price': latest['Price'],
            'eps': latest['EPS'],
            'pe_ratio': latest['PE_Ratio'],
            'type': latest['Type']
        }
    
    @property
    def data(self) -> dict:
        """Get raw data DataFrames.
        
        Returns:
            Dict with 'eps' and 'price' DataFrames
        """
        return {
            'eps': self._df_eps,
            'price': self._price_df
        }
    

def quarter_mapper(report_date: pd.Timestamp, start: int, end: int = 0) -> list[str]:
    """Map relative quarter positions to quarter column names.
    
    Args:
        report_date: Timestamp of the report date
        start: Relative start position (e.g., -4 for 4 quarters before current)
        end: Relative end position (e.g., 0 for current quarter, inclusive)
        
    Returns:
        List of quarter column names (e.g., ["Q1'19", "Q2'19", "Q3'19", "Q4'19"])
    """
    base_quarter = report_date.quarter
    base_year = report_date.year
    
    # Generate quarter range
    quarters = []
    for i in range(start, end + 1):
        # Calculate quarter and year with offset
        total_quarters = (base_year * 4 + base_quarter - 1) + i
        q = (total_quarters % 4) + 1
        y = (total_quarters // 4) % 100
        quarters.append(f"Q{q}'{y:02d}")
    
    return quarters


def calculate_eps_sum(
    df_eps: pd.DataFrame,
    dates: pd.Series,
    type: PE_RATIO_TYPE
) -> pd.Series:
    """Calculate 4-quarter EPS sum for given dates.
    
    Args:
        df_eps: DataFrame with EPS data (must have 'Report_Date' column)
        dates: Series of dates to calculate EPS for
        type: Type of EPS calculation ('forward' or 'trailing')
        
    Returns:
        Series of EPS sums
        
    Example:
        >>> eps_series = calculate_eps_sum(df_eps, df['Report_Date'], 'forward')
    """
    df_eps_sorted = df_eps.sort_values('Report_Date')
    
    results = [
        _calculate_eps_for_date(df_eps_sorted, date, type)
        for date in dates
    ]
    return pd.Series(results, index=dates.index)


def _calculate_eps_for_date(
    df_eps_sorted: pd.DataFrame,
    price_date: pd.Timestamp,
    type: PE_RATIO_TYPE
) -> float | None:
    """Calculate 4-quarter EPS sum for a single date."""
    # Get quarter column names using price_date
    if type == 'forward':
        needed_quarters = quarter_mapper(price_date, 0, 3)
    else:  # trailing
        needed_quarters = quarter_mapper(price_date, -4, -1)
    
    # Filter to only needed quarter columns
    eps_candidates = df_eps_sorted[df_eps_sorted['Report_Date'] <= price_date]
    if eps_candidates.empty:
        return None
    
    eps_filtered = eps_candidates[needed_quarters]
    
    # Get most recent value for each quarter column
    values = [
        float(str(eps_filtered[col].dropna().iloc[-1]).replace('*', '').strip())
        for col in needed_quarters
        if col in eps_filtered.columns and not eps_filtered[col].dropna().empty
    ]
    
    if len(values) == 4:
        return sum(values) if sum(values) > 0 else None
    
    return None



def plot_pe_ratio_with_price(
    output_path: Path | None = None,
    std_threshold: float = 1.5,
    figsize: tuple[int, int] = (14, 12)
) -> None:
    """Plot S&P 500 Price with P/E Ratios, highlighting periods outside ±1.5σ range.
    
    Creates two subplots showing S&P 500 Price alongside different P/E ratio types:
    - Q(-4)+Q(-3)+Q(-2)+Q(-1) (trailing): Last 4 quarters before report date
    - Q(0)+Q(1)+Q(2)+Q(3) (forward): Report date quarter and next 3 quarters
    
    Each subplot highlights periods where P/E ratio is outside ±1.5σ range:
    - Red bands: P/E > +1.5σ (overvalued periods)
    - Blue bands: P/E < -1.5σ (undervalued periods)
    
    Args:
        output_path: Path to save the plot. If None, displays the plot.
        std_threshold: Standard deviation threshold (default: 1.5)
        figsize: Figure size tuple (width, height) in inches (default: (14, 12))
    """
    # Initialize SP500
    sp500 = SP500()
    
    # Fetch data for both types
    types = ['trailing', 'forward']
    type_labels = {
        'trailing': 'Q(-4)+Q(-3)+Q(-2)+Q(-1)',
        'forward': 'Q(0)+Q(1)+Q(2)+Q(3)'
    }
    type_colors = {
        'trailing': 'green',
        'forward': 'red'
    }
    
    data_dict = {}
    # Get forward P/E data
    sp500.set_type('forward')
    df_forward = sp500.pe_ratio
    if not df_forward.empty:
        df_forward = df_forward.rename(columns={'Date': 'Price_Date'})
        df_forward = df_forward.sort_values('Price_Date')
        data_dict['forward'] = df_forward
    
    # Get trailing P/E data
    sp500.set_type('trailing')
    df_trailing = sp500.pe_ratio
    if not df_trailing.empty:
        df_trailing = df_trailing.rename(columns={'Date': 'Price_Date'})
        df_trailing = df_trailing.sort_values('Price_Date')
        data_dict['trailing'] = df_trailing
    
    if not data_dict:
        raise ValueError("No P/E ratio data available. Please ensure EPS data is available.")
    
    # Create figure with 2 subplots
    fig, axes = plt.subplots(2, 1, figsize=figsize, sharex=True)
    today_str = datetime.now().strftime('%Y-%m-%d')
    fig.suptitle(
        f'S&P 500 Price with P/E Ratios (Last Updated: {today_str})',
        fontsize=16,
        fontweight='bold',
        y=0.995
    )
    
    for idx, pe_type in enumerate(types):
        if pe_type not in data_dict:
            continue
            
        ax = axes[idx]
        df = data_dict[pe_type]
        
        # Convert dates to numpy array for easier manipulation
        dates = pd.to_datetime(df['Price_Date']).values
        prices = df['Price'].values
        pe_ratios = df['PE_Ratio'].values
        
        # Use original data without any clipping or smoothing
        # Calculate statistics on original data
        pe_mean = np.mean(pe_ratios)
        pe_std = np.std(pe_ratios)
        upper_threshold = pe_mean + std_threshold * pe_std
        lower_threshold = pe_mean - std_threshold * pe_std
        
        # Create secondary y-axis for P/E ratio
        ax2 = ax.twinx()
        
        # Highlight periods outside ±1.5σ range - use vertical bands across full y-axis
        overvalued_mask = pe_ratios > upper_threshold
        undervalued_mask = pe_ratios < lower_threshold
        
        # Find continuous regions for vertical bands
        in_overvalued = False
        in_undervalued = False
        overvalued_start = None
        undervalued_start = None
        
        for i in range(len(dates)):
            if overvalued_mask[i]:
                if not in_overvalued:
                    overvalued_start = dates[i]
                    in_overvalued = True
            else:
                if in_overvalued:
                    ax.axvspan(overvalued_start, dates[i-1] if i > 0 else dates[0], 
                              alpha=0.2, color='red', zorder=0)
                    in_overvalued = False
            
            if undervalued_mask[i]:
                if not in_undervalued:
                    undervalued_start = dates[i]
                    in_undervalued = True
            else:
                if in_undervalued:
                    ax.axvspan(undervalued_start, dates[i-1] if i > 0 else dates[0], 
                              alpha=0.2, color='blue', zorder=0)
                    in_undervalued = False
        
        # Handle case where region extends to end
        if in_overvalued:
            ax.axvspan(overvalued_start, dates[-1], alpha=0.2, color='red', zorder=0)
        if in_undervalued:
            ax.axvspan(undervalued_start, dates[-1], alpha=0.2, color='blue', zorder=0)
        
        # Plot mean and threshold lines
        ax2.axhline(y=pe_mean, color='gray', linestyle='--', linewidth=1.2, alpha=0.7, zorder=1)
        ax2.axhline(y=upper_threshold, color='gold', linestyle=':', linewidth=1.2, alpha=0.7, zorder=1)
        ax2.axhline(y=lower_threshold, color='gold', linestyle=':', linewidth=1.2, alpha=0.7, zorder=1)
        
        # Plot S&P 500 Price (left axis) - smoother line
        ax.plot(dates, prices, 'k-', linewidth=1.8, label='S&P 500 Price', alpha=0.85, zorder=2)
        ax.set_ylabel('S&P 500 Price', fontsize=11, fontweight='bold')
        ax.tick_params(axis='y', labelsize=9)
        ax.grid(True, alpha=0.15, linestyle='-', linewidth=0.3)
        
        # Plot P/E Ratio (right axis) - use original values
        color = type_colors[pe_type]
        ax2.plot(dates, pe_ratios, color=color, linewidth=1.5, 
                label=f'{type_labels[pe_type]} P/E Ratio', alpha=0.7, zorder=3)
        ax2.set_ylabel('P/E Ratio', fontsize=11, fontweight='bold', color=color)
        ax2.tick_params(axis='y', labelsize=9, labelcolor=color)
        ax2.margins(y=0.2)  # Add 20% margin to y-axis
        
        # Set title
        ax.set_title(
            f'S&P 500 Price with {type_labels[pe_type]} P/E Ratio (Highlighting periods outside ±{std_threshold}σ range)',
            fontsize=12,
            fontweight='bold',
            pad=10
        )
        
        # Format x-axis dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_minor_locator(mdates.MonthLocator((1, 7)))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=0, ha='center', fontsize=9)
        
        # Create cleaner legend
        legend_elements = [
            plt.Line2D([0], [0], color='black', linewidth=1.8, label='S&P 500 Price'),
            plt.Line2D([0], [0], color=color, linewidth=1.0, label=f'{type_labels[pe_type]} P/E Ratio', alpha=0.6),
            plt.Line2D([0], [0], color='gray', linestyle='--', linewidth=1.2, label=f'Mean: {pe_mean:.2f}'),
            plt.Line2D([0], [0], color='gold', linestyle=':', linewidth=1.2, label=f'+{std_threshold}σ: {upper_threshold:.2f}'),
            plt.Line2D([0], [0], color='gold', linestyle=':', linewidth=1.2, label=f'-{std_threshold}σ: {lower_threshold:.2f}'),
            plt.Rectangle((0, 0), 1, 1, facecolor='red', alpha=0.2, label=f'P/E > +{std_threshold}σ'),
            plt.Rectangle((0, 0), 1, 1, facecolor='blue', alpha=0.2, label=f'P/E < -{std_threshold}σ')
        ]
        
        ax.legend(handles=legend_elements, loc='upper left', fontsize=8, 
                 framealpha=0.9, edgecolor='lightgray')
    
    # Set x-axis label on bottom subplot
    axes[-1].set_xlabel('Date', fontsize=11, fontweight='bold')
    
    # Adjust layout
    plt.tight_layout(rect=[0, 0, 1, 0.98])
    
    # Save or show
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"✅ Plot saved to {output_path}")
    else:
        plt.show()
    
    plt.close()


def plot_time_series(
    dates: pd.Series,
    values: pd.Series | list[pd.Series],
    sigma: float | None = None,
    sigma_index: int = 0,
    output_path: Path | None = None,
    figsize: tuple[int, int] = (14, 8),
    labels: list[str] | None = None,
    colors: list[str] | None = None
) -> None:
    """Plot time series data with optional sigma threshold highlighting."""
    if isinstance(values, pd.Series):
        values = [values]
    if len(values) > 2:
        raise ValueError("Maximum 2 value series allowed")
    
    dates = pd.to_datetime(dates).values
    colors = colors or ['blue', 'red'][:len(values)]
    labels = labels or [v.name if v.name else f'Series {i+1}' for i, v in enumerate(values)]
    
    fig, ax = plt.subplots(figsize=figsize)
    ax2 = ax.twinx() if len(values) == 2 else None
    
    # Sigma threshold regions
    if sigma is not None:
        if sigma_index < len(values):
            v = values[sigma_index].values
            mean, std = np.mean(v), np.std(v)
            upper, lower = mean + sigma * std, mean - sigma * std
            for mask, color in [(v > upper, 'red'), (v < lower, 'blue')]:
                starts = np.where(np.diff(np.concatenate(([False], mask, [False]))))[0]
                for i in range(0, len(starts), 2):
                    if i+1 < len(starts):
                        ax.axvspan(dates[starts[i]], dates[starts[i+1]-1], alpha=0.2, color=color, zorder=0)
            for y, style in [(mean, '--'), (upper, ':'), (lower, ':')]:
                ax.axhline(y=y, color='gray' if style == '--' else 'gold', linestyle=style, 
                        linewidth=1.2, alpha=0.7, zorder=1)
        else:
            print(f"Sigma index {sigma_index} is out of range for {len(values)} values")
    
    # Plot series
    for i, val in enumerate(values):
        (ax2 if i == 1 else ax).plot(dates, val.values, color=colors[i], linewidth=1.5,
                                     label=labels[i], alpha=0.7, zorder=2)
    
    ax.set_xlabel('Date', fontsize=11, fontweight='bold')
    ax.set_ylabel(labels[0], fontsize=11, fontweight='bold', color=colors[0])
    ax.tick_params(axis='y', labelsize=9, labelcolor=colors[0])
    ax.grid(True, alpha=0.15, linestyle='-', linewidth=0.3)
    if ax2:
        ax2.set_ylabel(labels[1], fontsize=11, fontweight='bold', color=colors[1])
        ax2.tick_params(axis='y', labelsize=9, labelcolor=colors[1])
    
    lines, lbls = ax.get_legend_handles_labels()
    if ax2:
        lines2, lbls2 = ax2.get_legend_handles_labels()
        lines, lbls = lines + lines2, lbls + lbls2
    ax.legend(lines, lbls, loc='upper left', fontsize=9, framealpha=0.9, edgecolor='lightgray')
    
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=0, ha='center', fontsize=9)
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"✅ Plot saved to {output_path}")
    else:
        plt.show()
    plt.close()


if __name__ == "__main__":
    # Example usage
    sp500 = SP500()
    sp500.peg_ratio
    print("Current P/E Ratio:")
    current = sp500.current_pe
    print(f"  Date: {current['date']}")
    print(f"  P/E: {current['pe_ratio']:.2f}")

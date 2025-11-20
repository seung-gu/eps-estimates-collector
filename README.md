# EPS Estimates Collector

A Python package for extracting quarterly EPS (Earnings Per Share) estimates from financial reports using OCR and image processing techniques.

> **⚠️ Disclaimer**: This package is for **educational and research purposes only**. For production use, please use [FactSet's official API](https://developer.factset.com/). This package processes publicly available PDF reports and is not affiliated with or endorsed by FactSet.

## Overview

This project processes chart images containing S&P 500 quarterly EPS data and extracts quarter labels (e.g., Q1'14, Q2'15) and corresponding EPS values. The extracted data is saved in CSV format for further analysis.

### Motivation

Financial data providers (FactSet, Bloomberg, Investing.com, etc.) typically offer historical EPS data as **actual values**—once a quarter's earnings are reported, the estimate is overwritten with the actual figure. This creates a challenge for backtesting predictive models: using historical data means testing against information that was already reflected in stock prices at the time, making it difficult to evaluate the true predictive power of EPS estimates.

To address this, this project extracts **point-in-time EPS estimates** from historical earnings insight reports. By preserving the estimates as they appeared at each report date (before actual earnings were announced), a dataset can be built that accurately reflects what was known and expected at each point in time, enabling more meaningful backtesting and predictive analysis.

## Project Structure

```
eps-estimates-collector/
├── src/eps_estimates_collector/
│   ├── core/                        # Data collection
│   │   ├── downloader.py            # PDF download
│   │   ├── extractor.py             # Chart extraction
│   │   └── ocr/                     # OCR processing
│   │       ├── processor.py         # Main pipeline
│   │       ├── google_vision_processor.py
│   │       ├── parser.py
│   │       ├── bar_classifier.py
│   │       └── coordinate_matcher.py
│   ├── analysis/                    # P/E ratio calculation
│   │   └── pe_ratio.py
│   └── utils/                       # Cloud storage
│       ├── cloudflare.py            # R2 operations
│       └── csv_storage.py           # CSV I/O
├── scripts/data_collection/         # CLI scripts
├── actions/workflow.py              # GitHub Actions
└── pyproject.toml
```

## Installation

Install from PyPI:

```bash
pip install eps-estimates-collector
```

Or with `uv`:

```bash
uv pip install eps-estimates-collector
```

### Requirements

- **Google Cloud Vision API** (Required):
  - Create service account and download JSON key
  - Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable
  - [Setup Guide](https://cloud.google.com/vision/docs/setup)

- **Cloudflare R2** (Optional - CI/CD only):
  - For GitHub Actions workflow only
  - Automatically included via `boto3` dependency

## Workflow Overview

The complete workflow from PDF documents to final P/E ratio calculation:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    📄 Step 1: PDF Download                          │
│                                                                     │
│  FactSet Earnings Insight Reports                                   │
│  └─> Download PDFs from FactSet website                             │
│      (e.g., EarningsInsight_20251114_111425.pdf)                    │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│              🖼️  Step 2: EPS Chart Page Extraction                  │
│                                                                     │
│  PDF Document                                                       │
│  └─> Extract EPS chart page (Page 6)                                │
│      └─> Convert to PNG image                                       │
│          (e.g., 20161209-6.png)                                     │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│              🔍 Step 3: OCR Processing & Data Extraction            │
│                                                                     │
│  Chart Image                                                        │
│  ├─> Google Cloud Vision API (149 text regions detected)            │
│  ├─> Coordinate-based matching (Q1'14 ↔ 27.85)                      │
│  ├─> Bar classification (dark = actual, light = estimate)           │
│  └─> Extract quarter labels and EPS values                          │
│                                                                     │
│  Output: CSV with quarterly EPS estimates                           │
│  └─> extracted_estimates.csv                                        │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│              📊 Step 4: P/E Ratio Calculation                       │
│                                                                     │
│  EPS Estimates + S&P 500 Prices                                     │
│  ├─> Load EPS data from public URL                                  │
│  ├─> Load S&P 500 prices from yfinance (2016-12-09 to today)        │
│  ├─> Calculate 4-quarter EPS sum (forward/mix/trailing-like)        │
│  └─> Calculate P/E Ratio = Price / EPS_4Q_Sum                       │
│                                                                     │
│  Output: DataFrame with P/E ratios                                  │
└─────────────────────────────────────────────────────────────────────┘
```

### Visual Workflow

**Step 1: PDF Document** → Downloads FactSet Earnings Insight PDF reports

<table>
<tr>
<td width="50%">
<strong>Step 2: EPS Chart Page Extraction</strong><br>
<img src="output/preprocessing_test/20161209-6_original.png" alt="Original Chart" width="100%">
</td>
<td width="50%">
<strong>Step 3: OCR Processing & Bar Classification</strong><br>
<img src="output/preprocessing_test/20161209-6_bar_classification.png" alt="Bar Classification" width="100%">
<small><em>Red bars = Actual values, Magenta bars = Estimates</em></small>
</td>
</tr>
</table>

**Step 4: P/E Ratio Calculation** → See example output below

### Example: P/E Ratio Calculation Result

```python
from eps_estimates_collector import calculate_pe_ratio

# Calculate trailing-like P/E ratios
pe_df = calculate_pe_ratio('trailing-like')
print(pe_df)
```

**Output:**
```
📈 Loading S&P 500 price data from yfinance (2016-12-09 to 2025-11-20)...
✅ Loaded 2249 S&P 500 price points

      Report_Date  Price_Date    Price  EPS_4Q_Sum  PE_Ratio         Type
0      2016-12-09  2016-12-09  2249.69      122.28     18.40  trailing-like
1      2016-12-09  2016-12-12  2257.48      122.28     18.46  trailing-like
2      2016-12-09  2016-12-13  2271.72      122.28     18.58  trailing-like
...
2246   2025-11-07  2025-11-13  6600.00      278.30     23.72  trailing-like
2247   2025-11-14  2025-11-14  6700.00      278.84     24.03  trailing-like
2248   2025-11-14  2025-11-19  6700.00      278.84     24.03  trailing-like

[2249 rows x 6 columns]
```

## Usage

### Python API

```python
from eps_estimates_collector import calculate_pe_ratio

# Calculate P/E ratios (auto-loads CSV and S&P 500 prices)
pe_df = calculate_pe_ratio(type='forward')
print(pe_df)
```

**P/E Types:**
- `forward`: Q[1:5] - Next 4 quarters (skip current)
- `mix`: Q[0:4] - Current + next 3 quarters
- `trailing-like`: Q[-3:1] - Last 3 + current quarter

## Architecture

### Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      📦 Storage Structure                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📦 Public Bucket (R2_PUBLIC_BUCKET_NAME)                       │
│     ├── extracted_estimates.csv          ← Public URL (no auth) │
│     └── extracted_estimates_confidence.csv                      │
│                                                                 │
│  🔒 Private Bucket (R2_BUCKET_NAME)                             │
│     ├── reports/*.pdf                    ← API key required     │
│     └── estimates/*.png                  ← API key required     │
└─────────────────────────────────────────────────────────────────┘
```

### User Flow 1: API Users (Read-only)

```
┌──────────────────────────────────────────────────────────────────┐
│  Python Script                                                   │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  from eps_estimates_collector import calculate_pe_ratio          │
│                                                                  │
│  pe_df = calculate_pe_ratio(type='forward')                      │
│     │                                                            │
│     ├─ read_csv_from_cloud("extracted_estimates.csv")            │
│     │      │                                                     │
│     │      └─ GET https://pub-xxx.r2.dev/extracted_estimates.csv │
│     │            ↑                                               │
│     │            └─ ✅ No API key needed (public URL)            │
│     │                                                            │
│     └─ Calculate P/E ratios → Return DataFrame                   │
└──────────────────────────────────────────────────────────────────┘
```

**Features:**
- ✅ No API keys required
- ✅ Always loads latest data
- ✅ No local files needed
- ✅ Auto-loads S&P 500 prices from yfinance

### User Flow 2: GitHub Actions Workflow (Read/Write)

```
┌─────────────────────────────────────────────────────────────────┐
│  Workflow Steps                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 1: Check last date                                        │
│     read_csv_from_cloud("extracted_estimates.csv")              │
│        → GET public URL                                         │
│        → Get last Report_Date                                   │
│                                                                 │
│  Step 2: Download new PDFs                                      │
│     download_pdfs(start_date=last_date)                         │
│        → FactSet website                                        │
│        → Save to local (temp)                                   │
│                                                                 │
│  Step 3: Extract charts                                         │
│     extract_charts(pdfs)                                        │
│        → PDF → PNG                                              │
│        → Save to local (temp)                                   │
│                                                                 │
│  Step 4: Process images                                         │
│     process_images(directory)                                   │
│        ├─ read_csv_from_cloud() ← Load existing CSV             │
│        ├─ OCR processing                                        │
│        ├─ Merge existing + new data                             │
│        └─ Return DataFrame (don't save locally)                 │
│                                                                 │
│  Step 5: Upload results                                         │
│     ├─ write_csv_to_cloud(df, "extracted_estimates.csv")        │
│     │     → PUT to public bucket (with API key)                 │
│     │     → Accessible via public URL                           │
│     │                                                           │
│     └─ upload_to_cloud(pdfs/pngs)                               │
│           → PUT to private bucket (with API key)                │
│           → Only accessible with API key                        │
└─────────────────────────────────────────────────────────────────┘
```

**Features:**
- ✅ Reads from public URL (existing data)
- ✅ Writes to public bucket (CSV) with API key
- ✅ Writes to private bucket (PDF/PNG) with API key
- ✅ Appends new data (no overwrite)

### Environment Variables

```bash
# API Users
# → No setup needed (public URL hardcoded)

# GitHub Actions Workflow
R2_BUCKET_NAME=factset-data          # 🔒 Private bucket
R2_PUBLIC_BUCKET_NAME=factset-public # 📦 Public bucket
R2_ACCOUNT_ID=xxx
R2_ACCESS_KEY_ID=xxx
R2_SECRET_ACCESS_KEY=xxx
CI=true
```

## Data Format

### Main CSV (`extracted_estimates.csv`)

| Report_Date | Q4'13 | Q1'14 | Q2'14 | ... |
|-------------|-------|-------|-------|-----|
| 2016-12-09  | 24.89 | 26.23 | 27.45 | ... |
| 2016-12-16  | 24.89 | 26.25 | 27.48 | ... |

- **Report_Date**: Report date (YYYY-MM-DD)
- **Quarters**: EPS estimates in dollars
- **Public URL**: `https://pub-62707afd3ebb422aae744c63c49d36a0.r2.dev/extracted_estimates.csv`

### Confidence CSV

Same structure, contains OCR confidence scores (0-1).

## API Reference

### `calculate_pe_ratio(type='forward')`

Calculate P/E ratios from EPS estimates using S&P 500 prices.

**Parameters:**
- `type` (str): `'forward'`, `'mix'`, or `'trailing-like'`
  - `'forward'`: Q[1:5] - Next 4 quarters after report date
  - `'mix'`: Q[0:4] - Report date and next 3 quarters
  - `'trailing-like'`: Q[-3:1] - Last 3 quarters before and report date

**Returns:** DataFrame with columns:
- `Report_Date`: EPS report date
- `Price_Date`: Trading day price date
- `Price`: S&P 500 closing price
- `EPS_4Q_Sum`: 4-quarter EPS sum
- `PE_Ratio`: Calculated P/E ratio
- `Type`: P/E type used

**Example:**
```python
from eps_estimates_collector import calculate_pe_ratio

# Auto-loads CSV from public URL and S&P 500 prices from yfinance
pe_df = calculate_pe_ratio(type='forward')
print(pe_df)
```

## GitHub Actions

### Setup Secrets

Settings → Secrets → Actions:
```
GOOGLE_APPLICATION_CREDENTIALS_JSON
R2_BUCKET_NAME
R2_PUBLIC_BUCKET_NAME
R2_ACCOUNT_ID
R2_ACCESS_KEY_ID
R2_SECRET_ACCESS_KEY
```

### Workflow

- **Schedule**: Every Monday 00:00 UTC
- **Manual**: GitHub Actions tab
- **Steps**:
  1. Check last report date (public URL)
  2. Download new PDFs
  3. Extract charts → Process with OCR
  4. Upload to cloud (PDFs/PNGs → private, CSVs → public)

## Recent Updates

### v0.3.0 (2025-11-19) - Cloud-First Architecture
- ✅ **Cloud-first design**: CSV data always from public URL
- ✅ **Two-bucket strategy**: Private (PDF/PNG) + Public (CSV)
- ✅ **Simplified codebase**: Removed local file logic
- ✅ **Code cleanup**: 45% reduction in csv_storage.py
- ✅ **Better organization**: Split functions by responsibility
- ✅ **API-focused**: Optimized for package users

### v0.2.0 (2025-11-19)
- Unified package structure
- Code reduction (33%)
- P/E ratio calculation module

## Technical Details

- **OCR**: Google Cloud Vision API (149 regions/image)
- **Text Matching**: Coordinate-based spatial algorithm
- **Bar Classification**: 3-method ensemble (100% agreement)
- **Confidence Score**: Bar classification (0.5) + consistency (0.5)

See [DEVELOPMENT_LOG.md](DEVELOPMENT_LOG.md) for detailed technical documentation.

## Legal Disclaimer

**This package is provided for educational and research purposes only.**

- This package processes publicly available PDF reports from FactSet's website
- The data extraction and processing methods are implemented for academic research
- **This package is NOT affiliated with, endorsed by, or sponsored by FactSet**
- **For production use, please use [FactSet's official API](https://developer.factset.com/)**

**No Warranty**: This software is provided "as is" without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement.

**Limitation of Liability**: In no event shall the authors or copyright holders be liable for any claim, damages, or other liability arising from the use of this software.

**Data Usage**: Users are responsible for ensuring compliance with FactSet's terms of service and any applicable data usage agreements when using this package.

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Acknowledgments

- FactSet (Earnings Insight reports) - [Official FactSet API](https://developer.factset.com/)
- Google Cloud Vision API
- Cloudflare R2

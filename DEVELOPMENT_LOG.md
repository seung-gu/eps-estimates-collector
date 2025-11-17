# Development Log / Research Journal

This document tracks the development journey, experiments, challenges, and decisions made during the development of the Chart OCR Processor.

## Timeline

### Phase 1: Cloud-based Vision API Experiments

#### Attempt 1: OpenAI Vision API
- **Date**: Initial exploration
- **Approach**: Used OpenAI's vision model for text extraction from chart images
- **Results**: 
  - Performance was unsatisfactory
  - The model struggled to accurately identify and extract quarter labels (Q1'14, Q2'15, etc.) and EPS values from the chart images
  - Low accuracy in matching quarter labels with their corresponding values
- **Decision**: Abandoned this approach due to poor performance

#### Attempt 2: Gemini Vision Model
- **Date**: After OpenAI Vision API
- **Approach**: Tested Google's Gemini Vision model as an alternative
- **Results**:
  - Showed better results compared to OpenAI Vision
  - Better accuracy in text recognition
- **Challenges**:
  - Encountered significant rate limiting issues
  - Unable to process large batches of images efficiently
  - Cost and scalability concerns for processing 379+ images
- **Decision**: Abandoned due to rate limiting constraints

### Phase 2: Local Image Processing with Tesseract OCR

#### Implementation: Tesseract OCR Pipeline
- **Date**: After cloud API experiments
- **Approach**: Implemented local image processing solution using:
  - OpenCV for image preprocessing
  - Tesseract OCR for text extraction
  - Custom parsing logic for quarter labels and EPS values

**Image Preprocessing Pipeline**:
1. Grayscale conversion
2. Noise reduction using Non-local Means Denoising
3. Binary thresholding (Otsu's method)
4. Morphological operations for text enhancement

**Results**:
- Successfully implemented local processing pipeline
- No rate limiting issues
- Can process images in batch

**Challenges Discovered**:

1. **Poor Text Detection Accuracy**
   - Tesseract's bounding box detection was inaccurate
   - Many text regions were missed or incorrectly identified
   - Visualization shows fragmented and missing bounding boxes

   <img src="output/preprocessing_test/20161209-6_boxes_visualized.png" alt="Tesseract OCR Detection Results" width="600">

2. **Quarter Label Recognition Issues**
   - OCR often misrecognized quarter labels:
     - `Q1'14` → `Q114` or `0114`
     - `Q2'17` → `Q217` or `0217`
   - Implemented pattern matching to handle these misrecognitions
   - Still missing many quarter labels entirely

3. **Spatial Relationship Problems**
   - Difficulty in correctly matching quarter labels with their corresponding EPS values
   - Text boxes don't accurately represent spatial relationships
   - Current matching algorithm assigns same EPS value (32.64) to multiple quarters
   - Example: Q1'14 should be 27.85, but extracted as 32.64

4. **Limited Text Region Detection**
   - Only 141 text boxes detected from a complex chart image
   - Many quarter labels and values are missed
   - Box visualization shows poor coverage

**Current Status**:
- ✅ Basic OCR pipeline working
- ✅ Quarter label parsing handles common OCR misrecognitions
- ⚠️ Text detection accuracy: Poor
- ⚠️ Quarter-EPS matching: Inaccurate (all values showing as 32.64)
- ⚠️ Missing many quarter labels and values

**Test Results** (5 images processed):
- Extracted 10 records from first image (2016-12-09)
- Only Q2'17 matched correctly (32.64)
- All other quarters had incorrect EPS values
- Many quarters missing from extraction

### Phase 3: CRAFT Text Detection Model (In Progress)

#### Research: CRAFT Model for Text Detection
- **Date**: Current phase
- **Motivation**: Address Tesseract's poor text detection capabilities
- **Approach**: Implement CRAFT (Character Region Awareness for Text detection) model
  - Deep learning-based text detection
  - Superior text region segmentation
  - Better handling of complex layouts (charts, tables)

**Why CRAFT?**
- More accurate text region detection compared to Tesseract
- Better handling of text in complex layouts (like charts)
- Improved ability to detect text at various scales and orientations
- Better separation of text regions before OCR recognition
- Can provide precise bounding boxes for text regions

#### Implementation: CRAFT Model Integration

**Model Setup**:
- Used pre-trained CRAFT model (`craft_mlt_25k.pth`)
- Integrated PyTorch-based CRAFT detector
- Model outputs two score maps:
  - **Region Score Map**: Character-level text region confidence
  - **Affinity Score Map**: Character connection confidence

**CRAFT Score Maps Visualization**:

The CRAFT model generates two important score maps that help understand text detection:

1. **Region Score Map**: Shows character-level text region confidence
   <img src="output/preprocessing_test/20161209-6_region_score.png" alt="Region Score Map" width="600">

2. **Affinity Score Map**: Shows character connection confidence
   <img src="output/preprocessing_test/20161209-6_affinity_score.png" alt="Affinity Score Map" width="600">

**Threshold Tuning**:

Different threshold combinations were tested to optimize text detection:

- **Threshold 0.2, 0.2** (text_threshold=0.2, link_threshold=0.2):
  <img src="output/preprocessing_test/20161209-6_threshold_0.2_0.2_boxes.png" alt="Threshold 0.2, 0.2" width="600">

- **Threshold 0.25, 0.25** (text_threshold=0.25, link_threshold=0.25):
  <img src="output/preprocessing_test/20161209-6_threshold_0.25_0.25_boxes.png" alt="Threshold 0.25, 0.25" width="600">

- **Threshold 0.3, 0.3** (text_threshold=0.3, link_threshold=0.3):
  <img src="output/preprocessing_test/20161209-6_threshold_0.3_0.3_boxes.png" alt="Threshold 0.3, 0.3" width="600">

**Threshold Tuning Results**:

After extensive testing, the optimal configuration was determined:

- **text_threshold=0.3**: Region score threshold (character detection)
- **link_threshold=0.15**: Affinity score threshold (character connection) - lowered to allow more character connections
- **low_text=0.2**: Initial binarization threshold for connected component detection
- **Result**: 125 text regions detected (optimal balance between detection coverage and accuracy)

#### OCR Engine Comparison: EasyOCR vs Tesseract

After implementing CRAFT for text detection, we compared two OCR engines for text recognition:

**Final Configuration**:
- CRAFT detection: text_threshold=0.3, link_threshold=0.15, low_text=0.2
- No whitelist filtering (all characters recognized)
- Both engines process the same 125 detected text regions
- EasyOCR selected as the final OCR engine

**EasyOCR Results** (125 valid OCR results with optimal threshold settings):
- Excellent accuracy for decimal numbers: `30.61`, `81.79`, `34.18`, `27.85`, `83.20`, `37.50`, `35.20`, `31.64`, `30.86`, `30.18`
- Correctly identifies all numeric values including decimals
- Better handling of large numbers: `2992`, `2972`, `3135`, `3033`, `696`
- Recognizes text labels: `Inc:`, `&` (when whitelist is removed)
- **Selected as the final OCR engine** for production use

<img src="output/preprocessing_test/20161209-6_craft_ocr_easyocr.png" alt="EasyOCR Results (Final)" width="600">

**Tesseract Results** (114 valid OCR results):
- Some decimal recognition issues: `8179` instead of `81.79`
- More false positives: single characters like `a`, `.`
- Inconsistent decimal point handling: `35.000` vs `35.00`
- Still struggles with some number patterns

<img src="output/preprocessing_test/20161209-6_craft_ocr_tesseract.png" alt="Tesseract Results" width="600">

### Phase 4: Google Cloud Vision API (Final Solution)

#### Implementation: Google Cloud Vision API
- **Date**: Final phase
- **Approach**: Use Google Cloud Vision API for both text detection and recognition
- **Advantage**: Google Vision API performs both detection and recognition in a single call, eliminating the need for separate detection models

**Why Google Cloud Vision API?**
- Built-in text detection and recognition in one API call
- Superior accuracy compared to local OCR solutions
- Handles complex layouts (charts, tables) excellently
- No need for separate detection models (CRAFT) or preprocessing
- Professional-grade OCR performance

**Results**:
- **149 text regions detected and recognized** from a single chart image
- Excellent accuracy for all numeric values:
  - Large numbers: `150.00`, `140.00`, `130.00`, `120.00`, `110.00`, `100.00`
  - Decimal values: `83.20`, `81.79`, `71.43`, `59.34`, `83.10`
  - Complex numbers: `117.97`, `118.75`, `116.76`, `108.47`, `102.43`, `94.86`, `132.69`
  - Small decimals: `37.50`, `35.00`, `32.50`, `30.00`, `27.85`, `27.50`, `25.00`, `22.50`, `20.00`
- Recognizes all text labels: `FACTSET`, `EARNINGS INSIGHT`, `Bottom-Up EPS`, `S&P 500`, etc.
- **Selected as the final production solution**

<img src="output/preprocessing_test/20161209-6_google_ocr_full.png" alt="Google Cloud Vision Results" width="600">

**Key Findings**:
1. **Google Cloud Vision API outperforms all local solutions**: 149 regions detected vs 125 with CRAFT+EasyOCR
2. **Single API call for detection and recognition**: No need for separate detection models
3. **Superior accuracy**: Perfect decimal recognition, no misrecognitions
4. **Production-ready**: Professional-grade OCR suitable for production use

### Phase 5: Coordinate-Based Quarter-Value Matching Algorithm

#### Implementation: Spatial Relationship Matching
- **Date**: After Google Cloud Vision API integration
- **Approach**: Use coordinate information from OCR results to match quarter labels with their corresponding EPS values
- **Challenge**: OCR provides text and coordinates, but doesn't automatically match quarters with values

**Algorithm Overview**:

1. **Q Pattern Extraction and Normalization**:
   - Extract Q patterns from bottom 30% of image (where quarter labels are located)
   - Normalize OCR misrecognitions:
     - `Q` → `O`, `0` (when Q is recognized as O or 0)
     - `1` → `I`, `l` (when 1 is recognized as I or l)
   - Pattern matching for: `Q1'17`, `Q114`, `0114`, `Q1i7y` etc.
   - Sort Q boxes by x-coordinate (left to right) for chronological order

2. **Spatial Matching Algorithm**:
   - For each Q box, find the nearest number in the same y-range
   - **Constraints**:
     - x_tolerance: 10 pixels (Q box and number must be vertically aligned)
     - y_tolerance: 1000 pixels (number can be above Q box, but not too far)
     - Number must be above Q box (y coordinate smaller)
     - Exclude Q patterns from number candidates
     - Exclude large numbers (>= 2000, likely years)

3. **Distance Calculation**:
   - Calculate Euclidean distance between Q box center and number box center
   - Weight x-difference more heavily (10x) than y-difference (0.1x)
   - Select the number with minimum distance

**Results**:
- **16 quarter-value pairs successfully matched** from test image
- All matches are spatially correct (Q box and EPS value are vertically aligned)
- Chronological order maintained (sorted by x-coordinate)

<img src="output/preprocessing_test/20161209-6_coordinate_matching.png" alt="Coordinate-Based Matching Results" width="600">

**Example Matches**:
- Q1'14: 27.85 (x_diff: 3px, y_diff: 582px)
- Q2'14: 29.67 (x_diff: 0px, y_diff: 676px)
- Q3'14: 29.96 (x_diff: 2px, y_diff: 688px)
- Q4'14: 30.33 (x_diff: 1px, y_diff: 708px)
- ... (all 16 quarters matched correctly)

**Key Parameters**:
- `bottom_percent = 0.3`: Bottom 30% of image for Q pattern detection
- `x_tolerance = 10.0`: Maximum x-coordinate difference (pixels)
- `y_tolerance = 1000.0`: Maximum y-coordinate difference (pixels)
- `brightness_threshold = 150.0`: For bar color classification (dark vs light)

### Phase 6: Image Preprocessing for Bar Graph Classification

#### Research: Image Preprocessing Techniques
- **Date**: After coordinate-based matching implementation
- **Approach**: Test various image preprocessing techniques to optimize bar graph classification
- **Challenge**: Different bar graph types (filled vs partially filled) require different preprocessing approaches

**Preprocessing Techniques Tested**:

We tested 14 different preprocessing techniques on the chart images:

1. **Original Image**: Baseline for comparison
   <img src="output/preprocessing_test/image_preprocessing/00_original.png" alt="Original" width="600">

2. **Grayscale Conversion**: Convert color image to grayscale
   <img src="output/preprocessing_test/image_preprocessing/01_grayscale.png" alt="Grayscale" width="600">

3. **OTSU Binary**: Global thresholding using Otsu's method
   <img src="output/preprocessing_test/image_preprocessing/02_otsu_binary.png" alt="OTSU Binary" width="600">

4. **OTSU Binary Inverted**: Inverted OTSU thresholding
   <img src="output/preprocessing_test/image_preprocessing/03_otsu_binary_inv.png" alt="OTSU Binary Inverted" width="600">

5. **Adaptive Threshold**: Local adaptive thresholding (Gaussian)
   <img src="output/preprocessing_test/image_preprocessing/04_adaptive_threshold.png" alt="Adaptive Threshold" width="600">

6. **CLAHE**: Contrast Limited Adaptive Histogram Equalization
   <img src="output/preprocessing_test/image_preprocessing/05_clahe.png" alt="CLAHE" width="600">

7. **Histogram Equalization**: Global histogram equalization
   <img src="output/preprocessing_test/image_preprocessing/06_histogram_equalization.png" alt="Histogram Equalization" width="600">

8. **Gaussian Blur**: Noise reduction using Gaussian filter
   <img src="output/preprocessing_test/image_preprocessing/07_gaussian_blur.png" alt="Gaussian Blur" width="600">

9. **Non-local Means Denoising**: Advanced noise reduction
   <img src="output/preprocessing_test/image_preprocessing/08_denoised.png" alt="Denoised" width="600">

10. **Morphology Closing**: Dilation followed by erosion (fills gaps)
    <img src="output/preprocessing_test/image_preprocessing/09_morphology_closing.png" alt="Morphology Closing" width="600">

11. **Morphology Opening**: Erosion followed by dilation (removes noise)
    <img src="output/preprocessing_test/image_preprocessing/10_morphology_opening.png" alt="Morphology Opening" width="600">

12. **CLAHE + OTSU**: CLAHE preprocessing followed by OTSU thresholding
    <img src="output/preprocessing_test/image_preprocessing/11_clahe_otsu.png" alt="CLAHE + OTSU" width="600">

13. **Denoised + OTSU**: Denoising followed by OTSU thresholding
    <img src="output/preprocessing_test/image_preprocessing/12_denoised_otsu.png" alt="Denoised + OTSU" width="600">

14. **Histogram Equalization + OTSU**: Histogram equalization followed by OTSU thresholding
    <img src="output/preprocessing_test/image_preprocessing/13_hist_eq_otsu.png" alt="Histogram Equalization + OTSU" width="600">

**Selected Preprocessing Methods**:

After extensive testing, we selected **two preprocessing methods** based on bar graph characteristics:

1. **Morphology Closing** (for partially filled bar graphs):
   - **Rationale**: Partially filled bar graphs have gaps and holes
   - **Effect**: Morphology closing (dilation + erosion) fills small gaps and holes in the bars
   - **Result**: Partially filled bars become more solid, making brightness classification more reliable
   - **Why it works**: Closing operation connects nearby pixels, filling internal gaps while preserving the overall shape

2. **Adaptive Threshold** (for fully filled bar graphs):
   - **Rationale**: Fully filled bar graphs have clear, distinct contours
   - **Effect**: Adaptive thresholding creates sharp boundaries between bars and background
   - **Result**: Clear separation of bar regions, making contour detection and classification easier
   - **Why it works**: Local adaptive thresholding adapts to varying lighting conditions, creating consistent boundaries

**Implementation Strategy**:
- Apply both preprocessing methods to each image
- Classify bar graphs using brightness analysis on preprocessed images
- Select the method that provides the clearest distinction between dark and light bars

### Phase 7: Multi-Method Bar Graph Classification with Confidence Scoring

#### Implementation: Three-Method Ensemble Classification
- **Date**: After image preprocessing research
- **Approach**: Use three preprocessing methods simultaneously and apply voting mechanism with confidence scoring
- **Challenge**: Single method may misclassify certain bar graph types; need robust ensemble approach

**Selected Methods**:

After analyzing the preprocessing results, we selected **three methods** for ensemble classification:

1. **Adaptive Threshold**:
   - Creates sharp boundaries between bars and background
   - Optimal for fully filled bar graphs with clear contours
   - Threshold: 0.7 (white pixel ratio > 0.7 = dark bar)

2. **Morphology Closing**:
   - Fills gaps and holes in partially filled bars
   - Optimal for partially filled bar graphs
   - **Important**: Uses inverted logic (low ratio = dark, high ratio = light)
   - Threshold: 0.5 (white pixel ratio > 0.5 = light bar, ≤ 0.5 = dark bar)
   - **Rationale**: Morphology closing fills holes, so:
     - Low white ratio (0.05-0.1) = partially filled = **dark**
     - High white ratio (0.9-0.95) = fully filled = **light**

3. **OTSU Binary Inverted**:
   - Inverted binary image (dark regions become white)
   - Helps identify dark bars more clearly
   - Threshold: 0.7 (white pixel ratio > 0.7 = dark bar)

**Algorithm**:

1. **Preprocessing** (performed once per image):
   - Convert to grayscale
   - Generate three preprocessed images:
     - Adaptive Threshold (Gaussian, block size 11)
     - Morphology Closing (OTSU binary + closing operation)
     - OTSU Binary Inverted

2. **Bar Region Extraction**:
   - For each matched Q-number pair:
     - Crop bar region between Q box and number box
     - Extract region from all three preprocessed images

3. **Classification**:
   - Calculate white pixel ratio for each cropped region
   - Apply method-specific threshold and logic
   - Each method votes: 'dark' or 'light'

4. **Voting and Confidence**:
   - **High confidence (3/3)**: All three methods agree
   - **Medium confidence (2/3)**: Two methods agree
   - **Low confidence (1/3 or 0/3)**: Methods disagree
   - Final classification: Majority vote

**Threshold Tuning Process**:

Initial thresholds were too low (0.3-0.4), causing all bars to be classified as 'dark'. After analyzing the distribution:

- **Adaptive Threshold**: min=0.518, max=0.987, median=0.982 → Threshold: **0.7**
- **Morphology Closing**: min=0.052, max=0.947, median=0.065 → Threshold: **0.5** (with inverted logic)
- **OTSU Inverted**: min=0.475, max=0.948, median=0.935 → Threshold: **0.7**

**Critical Fix: Morphology Closing Logic**:

Initially, Morphology Closing used the same logic as other methods (`white_ratio > threshold = dark`), but this was incorrect. Since closing fills holes:
- **Low white ratio (0.05-0.07)**: Partially filled bars → **dark**
- **High white ratio (0.9-0.95)**: Fully filled bars → **light**

The logic was corrected to: `white_ratio > threshold = light` (inverted).

**Results**:

After fixing the Morphology Closing logic, all three methods achieve **100% agreement**:

- **Test Image 1 (20161209-6.png)**:
  - Dark bars: 10
  - Light bars: 6
  - High confidence (3/3): 16 (100%)
  - Medium confidence: 0
  - Low confidence: 0

<img src="output/preprocessing_test/20161209-6_bar_classification.png" alt="Bar Classification Results 1" width="600">

- **Test Image 2 (20161216-6.png)**:
  - Dark bars: 10
  - Light bars: 6
  - High confidence (3/3): 16 (100%)
  - Medium confidence: 0
  - Low confidence: 0

<img src="output/preprocessing_test/20161216-6_bar_classification.png" alt="Bar Classification Results 2" width="600">

**Key Findings**:

1. **Ensemble approach is essential**: Single method may misclassify, but three methods together provide robust classification
2. **Method-specific logic matters**: Morphology Closing requires inverted logic due to its hole-filling nature
3. **Threshold tuning is critical**: Initial thresholds (0.3-0.4) were too low; optimal thresholds (0.5-0.7) were found through distribution analysis
4. **Perfect agreement is achievable**: With proper thresholds and logic, all three methods can achieve 100% agreement
5. **Visualization helps validation**: Color-coded bounding boxes (red for dark, magenta for light) make it easy to verify classification accuracy

### Phase 8: Confidence Score Calculation with Weighted Components

#### Implementation: Composite Confidence Scoring
- **Date**: After multi-method bar graph classification
- **Approach**: Calculate final confidence score by combining bar graph classification confidence with consistency check against previous week's data
- **Challenge**: Need to balance internal classification reliability with external data consistency

**Confidence Score Components**:

The final confidence score is calculated as a **weighted average** of two components:

1. **Bar Graph Classification Confidence** (Weight: 0.5):
   - Based on agreement among three classification methods
   - **High (3/3 match)**: 100% confidence
   - **Medium (2/3 match)**: 67% confidence
   - **Low (1/3 or 0/3 match)**: 33% confidence
   - Average across all matched quarter-value pairs for the report date

2. **Previous Week Data Consistency** (Weight: 0.5):
   - Compares current week's **actual values** (dark bars) with closest previous week's actual values
   - Only compares actual values (excludes estimates marked with `*`)
   - **80% match threshold**: Values within 20% difference are considered consistent
   - Consistency rate = (matching quarters / total comparable quarters) × 100
   - **Special case**: First data entry uses 100% consistency (no previous data to compare)

**Final Confidence Calculation**:

```
Final Confidence = (Bar Score × 0.5) + (Consistency Score × 0.5)
```

**Example**:
- Bar graph classification: 3/3 match for all quarters → Bar Score = 100%
- Previous week consistency: 12 out of 15 quarters match → Consistency Score = 80%
- Final Confidence = (100 × 0.5) + (80 × 0.5) = **90.0%**

**Key Design Decisions**:

1. **Equal weights (0.5, 0.5)**: Both components are equally important
   - Internal classification reliability (bar graph methods agreement)
   - External data consistency (alignment with historical data)

2. **Actual values only for consistency check**: 
   - Only compares actual values (dark bars) between weeks
   - Estimates (light bars) are excluded from consistency calculation
   - Rationale: Estimates can vary significantly, but actuals should be stable

3. **Closest previous date** (not strictly 7 days):
   - Finds the closest previous date with data available
   - Handles missing weeks gracefully
   - More robust than strict 7-day interval

4. **First data entry exception**:
   - First report date uses 100% consistency score
   - No previous data available for comparison
   - Relies solely on bar graph classification confidence

**Results**:

The confidence score provides a reliable indicator of data quality:
- **High confidence (80-100%)**: Both classification and consistency are strong
- **Medium confidence (50-80%)**: One component is weaker
- **Low confidence (<50%)**: Both components indicate potential issues

This weighted approach ensures that the final confidence score reflects both the internal reliability of the classification process and the external consistency with historical data patterns.

## Key Learnings

1. **Cloud APIs Limitations** (OpenAI, Gemini):
   - Rate limiting is a significant constraint for batch processing
   - Performance may not meet requirements for specialized use cases
   - Cost and scalability concerns for processing large batches

2. **Google Cloud Vision API Success**:
   - Professional-grade OCR outperforms all local solutions (149 regions vs 125 with CRAFT+EasyOCR)
   - Single API call handles both detection and recognition, eliminating need for separate models
   - Superior accuracy with perfect decimal recognition and no misrecognitions
   - Handles complex layouts (charts, tables) excellently
   - Production-ready solution suitable for large-scale batch processing
   - No preprocessing required, works directly on original images

3. **Tesseract OCR Limitations**:
   - Text detection (not just recognition) is a critical component
   - Poor detection leads to poor overall results
   - Preprocessing helps but doesn't solve fundamental detection issues

4. **One-Stage vs Two-Stage Approach**:
   - Initially explored two-stage approach (CRAFT for detection + EasyOCR/Tesseract for recognition)
   - Two-stage requires separate models and more complex pipeline
   - **Final solution: Google Cloud Vision API** provides one-stage approach (detection + recognition in single API call)
   - One-stage approach is simpler, more accurate, and production-ready
   - Better detection leads to better recognition, but unified solution eliminates integration complexity

5. **CRAFT Model Benefits**:
   - Provides two score maps (Region and Affinity) for better understanding
   - Threshold tuning is crucial for optimal detection
   - Significantly better text region detection than Tesseract
   - Handles complex layouts (charts, tables) much better

6. **OCR Engine Selection**:
   - Google Cloud Vision API: Best overall performance, selected as final solution
   - EasyOCR: Performs better than Tesseract for number recognition, especially decimals
   - Tesseract: Struggles with decimal point recognition in some cases
   - Whitelist filtering helps but needs careful character selection
   - For production use, cloud-based solutions (Google Vision) outperform local OCR engines

7. **Coordinate-Based Matching**:
   - Spatial relationships are crucial for matching quarter labels with values
   - x-coordinate alignment is more important than y-coordinate (x_tolerance: 10px vs y_tolerance: 1000px)
   - Q pattern normalization handles OCR misrecognitions effectively
   - Sorting by x-coordinate maintains chronological order automatically
   - Distance weighting (x: 10x, y: 0.1x) ensures vertical alignment priority

8. **Image Preprocessing for Bar Classification**:
   - Different bar graph types require different preprocessing approaches
   - Morphology closing is optimal for partially filled bars (fills gaps and holes)
   - Adaptive threshold is optimal for fully filled bars (creates clear contours)
   - Testing multiple preprocessing techniques is essential for finding the best approach
   - The choice of preprocessing method significantly affects classification accuracy

9. **Multi-Method Ensemble Classification**:
   - Using multiple methods with voting mechanism provides robust classification
   - Method-specific logic is crucial (e.g., Morphology Closing requires inverted logic)
   - Threshold tuning through distribution analysis is essential for optimal performance
   - Confidence scoring (3/3, 2/3, 1/3) helps identify reliable classifications
   - Perfect agreement (100% 3/3 match) is achievable with proper tuning
   - Ensemble approach significantly reduces misclassification compared to single method

10. **Composite Confidence Scoring**:
   - Final confidence combines internal classification reliability with external data consistency
   - Equal weights (0.5, 0.5) balance both components effectively
   - Bar graph classification confidence (3/3=100%, 2/3=67%, 1/3=33%) reflects method agreement
   - Previous week consistency check validates against historical patterns
   - Only actual values (dark bars) are used for consistency comparison
   - Closest previous date approach handles missing weeks gracefully
   - First data entry exception ensures fair scoring when no historical data exists
   - Weighted average provides comprehensive quality indicator for extracted data

## References

### OCR and Text Detection
- **Google Cloud Vision API**: [Official Documentation](https://cloud.google.com/vision/docs) - Final production solution for text detection and recognition
- **CRAFT Model**: [Character Region Awareness for Text Detection](https://github.com/clovaai/CRAFT-pytorch) - Deep learning-based text detection model (used in research phase)
- **EasyOCR**: [EasyOCR GitHub](https://github.com/JaidedAI/EasyOCR) - OCR engine tested for text recognition (used in comparison experiments)
- **Tesseract OCR**: https://github.com/tesseract-ocr/tesseract - Open-source OCR engine (used in initial experiments)

### Image Processing
- **OpenCV**: [OpenCV Documentation](https://docs.opencv.org/) - Image preprocessing and computer vision operations

### PDF Processing
- **pdfplumber**: [pdfplumber Documentation](https://github.com/jsvine/pdfplumber) - PDF parsing and page-to-image conversion for extracting chart pages from FactSet PDFs


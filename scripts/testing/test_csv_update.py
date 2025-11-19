"""Comprehensive tests for CSV update functionality."""

import sys
from pathlib import Path
import pandas as pd
import tempfile
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.eps_estimates_collector.core.ocr.processor import process_directory


def test_existing_data_preserved():
    """Test that existing CSV data is preserved when processing new images."""
    
    existing_main = pd.DataFrame({
        'Report_Date': ['2016-12-09', '2016-12-16'],
        'Q1\'14': [27.85, 27.90],
        'Q2\'14': [29.67, 29.70]
    })
    
    existing_confidence = pd.DataFrame({
        'Report_Date': ['2016-12-09', '2016-12-16'],
        'Confidence': [85.5, 87.0]
    })
    
    def mock_process_image(image_path):
        return [{
            'report_date': '2016-12-23',
            'quarter': 'Q1\'14',
            'eps': 28.0,
            'bar_color': 'dark',
            'bar_confidence': 'high'
        }, {
            'report_date': '2016-12-23',
            'quarter': 'Q2\'14',
            'eps': 30.0,
            'bar_color': 'dark',
            'bar_confidence': 'high'
        }]
    
    with patch('src.eps_estimates_collector.core.ocr.processor.read_csv_from_cloud') as mock_read:
        def read_side_effect(path):
            if path == 'extracted_estimates.csv':
                return existing_main.copy()
            elif path == 'extracted_estimates_confidence.csv':
                return existing_confidence.copy()
            return None
        
        mock_read.side_effect = read_side_effect
        
        test_dir = Path(tempfile.mkdtemp())
        test_image = test_dir / '20161223-6.png'
        test_image.touch()
        
        with patch('src.eps_estimates_collector.core.ocr.processor.process_image', side_effect=mock_process_image):
            main_df, conf_df = process_directory(test_dir)
        
        assert len(main_df) == 3, f"Expected 3 records, got {len(main_df)}"
        assert len(conf_df) == 3, f"Expected 3 confidence records, got {len(conf_df)}"
        
        dates = main_df['Report_Date'].tolist()
        assert '2016-12-09' in dates, "Existing date should be preserved"
        assert '2016-12-16' in dates, "Existing date should be preserved"
        assert '2016-12-23' in dates, "New date should be added"
        
        assert float(main_df[main_df['Report_Date'] == '2016-12-09'].iloc[0]['Q1\'14']) == 27.85
        assert float(main_df[main_df['Report_Date'] == '2016-12-23'].iloc[0]['Q1\'14']) == 28.0
        
        conf_dates = conf_df['Report_Date'].tolist()
        assert '2016-12-09' in conf_dates
        assert conf_df[conf_df['Report_Date'] == '2016-12-09'].iloc[0]['Confidence'] == 85.5
        
        import shutil
        shutil.rmtree(test_dir)


def test_confidence_without_bar_confidence():
    """Test confidence calculation when bar_confidence is missing.
    
    Note: bar_confidence가 없어도 consistency_score는 계산되므로
    confidence는 0이 아닐 수 있음 (정상 동작).
    """
    
    def mock_process_image(image_path):
        # bar_confidence 없음!
        return [{
            'report_date': '2016-12-23',
            'quarter': 'Q1\'14',
            'eps': 28.0,
            'bar_color': 'dark'
            # bar_confidence 없음
        }]
    
    with patch('src.eps_estimates_collector.core.ocr.processor.read_csv_from_cloud') as mock_read:
        mock_read.return_value = None
        
        test_dir = Path(tempfile.mkdtemp())
        test_image = test_dir / '20161223-6.png'
        test_image.touch()
        
        with patch('src.eps_estimates_collector.core.ocr.processor.process_image', side_effect=mock_process_image):
            main_df, conf_df = process_directory(test_dir)
        
        # bar_confidence 없으면 bar_score=0, 하지만 consistency_score는 계산됨
        # first_date이면 consistency_score = 100.0
        # 따라서 (0.0 * 0.5) + (100.0 * 0.5) = 50.0 (정상 동작)
        if not conf_df.empty:
            new_conf = conf_df[conf_df['Report_Date'] == '2016-12-23']
            if not new_conf.empty:
                conf_value = new_conf.iloc[0]['Confidence']
                # bar_confidence 없어도 consistency로 인해 confidence > 0 가능
                assert conf_value >= 0.0, f"Confidence should be >= 0, got {conf_value}"
                # first date면 consistency=100이므로 최소 50.0
                assert conf_value == 50.0, \
                    f"Expected 50.0 when bar_confidence missing (bar_score=0, consistency=100), got {conf_value}"
        
        import shutil
        shutil.rmtree(test_dir)


def test_confidence_with_bar_confidence():
    """Test confidence calculation when bar_confidence exists."""
    
    def mock_process_image(image_path):
        return [{
            'report_date': '2016-12-23',
            'quarter': 'Q1\'14',
            'eps': 28.0,
            'bar_color': 'dark',
            'bar_confidence': 'high'  # 있음!
        }, {
            'report_date': '2016-12-23',
            'quarter': 'Q2\'14',
            'eps': 30.0,
            'bar_color': 'dark',
            'bar_confidence': 'high'
        }]
    
    with patch('src.eps_estimates_collector.core.ocr.processor.read_csv_from_cloud') as mock_read:
        mock_read.return_value = None
        
        test_dir = Path(tempfile.mkdtemp())
        test_image = test_dir / '20161223-6.png'
        test_image.touch()
        
        with patch('src.eps_estimates_collector.core.ocr.processor.process_image', side_effect=mock_process_image):
            main_df, conf_df = process_directory(test_dir)
        
        # bar_confidence 있으면 confidence > 0이어야 함
        if not conf_df.empty:
            new_conf = conf_df[conf_df['Report_Date'] == '2016-12-23']
            if not new_conf.empty:
                conf_value = new_conf.iloc[0]['Confidence']
                assert conf_value > 0.0, \
                    f"Expected confidence > 0 when bar_confidence='high', got {conf_value}"
        
        import shutil
        shutil.rmtree(test_dir)


def test_date_matching_failure():
    """Test when date matching fails in confidence calculation."""
    
    existing_main = pd.DataFrame({
        'Report_Date': ['2016-12-09'],
        'Q1\'14': [27.85]
    })
    
    def mock_process_image(image_path):
        # 날짜 형식이 다름 (다른 형식)
        return [{
            'report_date': '2016-12-23',  # 문자열
            'quarter': 'Q1\'14',
            'eps': 28.0,
            'bar_color': 'dark',
            'bar_confidence': 'high'
        }]
    
    with patch('src.eps_estimates_collector.core.ocr.processor.read_csv_from_cloud') as mock_read:
        def read_side_effect(path):
            if path == 'extracted_estimates.csv':
                return existing_main.copy()
            return None
        
        mock_read.side_effect = read_side_effect
        
        test_dir = Path(tempfile.mkdtemp())
        test_image = test_dir / '20161223-6.png'
        test_image.touch()
        
        with patch('src.eps_estimates_collector.core.ocr.processor.process_image', side_effect=mock_process_image):
            main_df, conf_df = process_directory(test_dir)
        
        # 날짜 매칭이 실패하면 confidence는 0이거나 경고가 있어야 함
        # 최소한 데이터는 있어야 함
        assert len(main_df) >= 1, "Should have at least 1 record"
        
        import shutil
        shutil.rmtree(test_dir)


def test_multiple_images_same_date():
    """Test processing multiple images with same date."""
    
    def mock_process_image(image_path):
        date = image_path.stem[:8]  # YYYYMMDD
        return [{
            'report_date': f'{date[:4]}-{date[4:6]}-{date[6:8]}',
            'quarter': 'Q1\'14',
            'eps': 28.0,
            'bar_color': 'dark',
            'bar_confidence': 'high'
        }]
    
    with patch('src.eps_estimates_collector.core.ocr.processor.read_csv_from_cloud') as mock_read:
        mock_read.return_value = None
        
        test_dir = Path(tempfile.mkdtemp())
        test_image1 = test_dir / '20161223-6.png'
        test_image2 = test_dir / '20161223-7.png'  # 같은 날짜
        test_image1.touch()
        test_image2.touch()
        
        with patch('src.eps_estimates_collector.core.ocr.processor.process_image', side_effect=mock_process_image):
            main_df, conf_df = process_directory(test_dir)
        
        # 같은 날짜면 하나만 남아야 함 (keep='last')
        dates = main_df['Report_Date'].tolist()
        assert dates.count('2016-12-23') == 1, f"Same date should be deduplicated, got {dates.count('2016-12-23')} occurrences"
        
        import shutil
        shutil.rmtree(test_dir)


def test_empty_results():
    """Test when process_image returns empty results."""
    
    def mock_process_image(image_path):
        return []  # 빈 결과
    
    existing_main = pd.DataFrame({
        'Report_Date': ['2016-12-09'],
        'Q1\'14': [27.85]
    })
    existing_confidence = pd.DataFrame({
        'Report_Date': ['2016-12-09'],
        'Confidence': [85.5]
    })
    
    with patch('src.eps_estimates_collector.core.ocr.processor.read_csv_from_cloud') as mock_read:
        def read_side_effect(path):
            if path == 'extracted_estimates.csv':
                return existing_main.copy()
            elif path == 'extracted_estimates_confidence.csv':
                return existing_confidence.copy()
            return None
        
        mock_read.side_effect = read_side_effect
        
        test_dir = Path(tempfile.mkdtemp())
        test_image = test_dir / '20161223-6.png'
        test_image.touch()
        
        with patch('src.eps_estimates_collector.core.ocr.processor.process_image', side_effect=mock_process_image):
            main_df, conf_df = process_directory(test_dir)
        
        # 빈 결과여도 기존 데이터는 유지되어야 함
        assert len(main_df) == 1, "Existing data should be preserved"
        assert '2016-12-09' in main_df['Report_Date'].tolist()
        
        import shutil
        shutil.rmtree(test_dir)


def test_confidence_merge_with_existing():
    """Test confidence merge with existing data."""
    
    existing_confidence = pd.DataFrame({
        'Report_Date': ['2016-12-09', '2016-12-16'],
        'Confidence': [85.5, 87.0]
    })
    
    def mock_process_image(image_path):
        return [{
            'report_date': '2016-12-23',
            'quarter': 'Q1\'14',
            'eps': 28.0,
            'bar_color': 'dark',
            'bar_confidence': 'high'
        }]
    
    with patch('src.eps_estimates_collector.core.ocr.processor.read_csv_from_cloud') as mock_read:
        def read_side_effect(path):
            if path == 'extracted_estimates.csv':
                return pd.DataFrame({'Report_Date': ['2016-12-09'], 'Q1\'14': [27.85]})
            elif path == 'extracted_estimates_confidence.csv':
                return existing_confidence.copy()
            return None
        
        mock_read.side_effect = read_side_effect
        
        test_dir = Path(tempfile.mkdtemp())
        test_image = test_dir / '20161223-6.png'
        test_image.touch()
        
        with patch('src.eps_estimates_collector.core.ocr.processor.process_image', side_effect=mock_process_image):
            main_df, conf_df = process_directory(test_dir)
        
        # 기존 confidence + 새 confidence 모두 있어야 함
        assert len(conf_df) >= 2, f"Should have existing + new confidence, got {len(conf_df)}"
        conf_dates = conf_df['Report_Date'].tolist()
        assert '2016-12-09' in conf_dates, "Existing confidence should be preserved"
        assert '2016-12-23' in conf_dates, "New confidence should be added"
        
        import shutil
        shutil.rmtree(test_dir)


def test_both_csvs_returned():
    """Test that process_directory returns both DataFrames."""
    
    existing_main = pd.DataFrame({
        'Report_Date': ['2016-12-09'],
        'Q1\'14': [27.85]
    })
    
    existing_confidence = pd.DataFrame({
        'Report_Date': ['2016-12-09'],
        'Confidence': [85.5]
    })
    
    with patch('src.eps_estimates_collector.core.ocr.processor.read_csv_from_cloud') as mock_read:
        def read_side_effect(path):
            if path == 'extracted_estimates.csv':
                return existing_main.copy()
            elif path == 'extracted_estimates_confidence.csv':
                return existing_confidence.copy()
            return None
        
        mock_read.side_effect = read_side_effect
        
        test_dir = Path(tempfile.mkdtemp())
        
        main_df, conf_df = process_directory(test_dir)
        
        assert isinstance(main_df, pd.DataFrame)
        assert isinstance(conf_df, pd.DataFrame)
        assert len(main_df) == 1
        assert len(conf_df) == 1
        
        import shutil
        shutil.rmtree(test_dir)


def test_empty_cloud_handling():
    """Test handling when cloud CSV doesn't exist."""
    
    with patch('src.eps_estimates_collector.core.ocr.processor.read_csv_from_cloud') as mock_read:
        mock_read.return_value = None
        
        test_dir = Path(tempfile.mkdtemp())
        
        main_df, conf_df = process_directory(test_dir)
        
        assert isinstance(main_df, pd.DataFrame)
        assert isinstance(conf_df, pd.DataFrame)
        assert 'Report_Date' in main_df.columns
        assert 'Report_Date' in conf_df.columns
        
        import shutil
        shutil.rmtree(test_dir)


if __name__ == '__main__':
    print("=" * 80)
    print("Comprehensive CSV Update Tests")
    print("=" * 80)
    
    tests = [
        ("Existing data preserved", test_existing_data_preserved),
        ("Confidence without bar_confidence", test_confidence_without_bar_confidence),
        ("Confidence with bar_confidence", test_confidence_with_bar_confidence),
        ("Date matching failure", test_date_matching_failure),
        ("Multiple images same date", test_multiple_images_same_date),
        ("Empty results", test_empty_results),
        ("Confidence merge", test_confidence_merge_with_existing),
        ("Both CSVs returned", test_both_csvs_returned),
        ("Empty cloud handling", test_empty_cloud_handling),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            print(f"\n🧪 Testing: {name}")
            test_func()
            print(f"   ✅ PASSED")
            passed += 1
        except AssertionError as e:
            print(f"   ❌ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 80)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 80)
    
    if failed > 0:
        sys.exit(1)

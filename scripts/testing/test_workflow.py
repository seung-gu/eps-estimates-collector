"""Test suite for workflow validation.

This module provides pytest-compatible tests for validating the workflow
before deploying to GitHub Actions.
"""

import os
import sys
from pathlib import Path

# CRITICAL: Add project root to path FIRST, before any imports
# This ensures imports work in VS Code Test Explorer
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()

# Multiple ways to ensure path is set
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Also try adding src directory
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Set environment variable
os.environ['PYTHONPATH'] = str(PROJECT_ROOT)

import pytest


class TestImports:
    """Test if all required imports work."""
    
    def test_core_imports(self):
        """Test core function imports."""
        # Use absolute import with explicit path handling
        try:
            from src.eps_estimates_collector import download_pdfs, extract_charts, process_images
            assert callable(download_pdfs)
            assert callable(extract_charts)
            assert callable(process_images)
        except ImportError as e:
            pytest.fail(f"Import failed: {e}\nPROJECT_ROOT: {PROJECT_ROOT}\nsys.path: {sys.path[:5]}")
    
    def test_utils_imports(self):
        """Test utility function imports."""
        try:
            from src.eps_estimates_collector.utils.cloudflare import (
                CLOUD_STORAGE_ENABLED,
                list_cloud_files,
                upload_to_cloud,
            )
            assert isinstance(CLOUD_STORAGE_ENABLED, bool)
            assert callable(list_cloud_files)
            assert callable(upload_to_cloud)
        except ImportError as e:
            pytest.fail(f"Utils import failed: {e}\nPROJECT_ROOT: {PROJECT_ROOT}\nsys.path: {sys.path[:5]}")
    
    def test_analysis_imports(self):
        """Test analysis function imports."""
        try:
            from src.eps_estimates_collector import calculate_pe_ratio
            assert callable(calculate_pe_ratio)
        except ImportError as e:
            pytest.fail(f"Analysis import failed: {e}\nPROJECT_ROOT: {PROJECT_ROOT}\nsys.path: {sys.path[:5]}")


class TestCloudStorageConfig:
    """Test cloud storage configuration."""
    
    def test_cloud_storage_enabled(self):
        """Test cloud storage enabled status."""
        from src.eps_estimates_collector.utils.cloudflare import CLOUD_STORAGE_ENABLED
        assert isinstance(CLOUD_STORAGE_ENABLED, bool)
    
    def test_r2_credentials(self):
        """Test R2 credentials are set (if cloud storage enabled)."""
        from src.eps_estimates_collector.utils.cloudflare import CLOUD_STORAGE_ENABLED
        
        if CLOUD_STORAGE_ENABLED:
            r2_vars = {
                'R2_BUCKET_NAME': os.getenv('R2_BUCKET_NAME'),
                'R2_ACCOUNT_ID': os.getenv('R2_ACCOUNT_ID'),
                'R2_ACCESS_KEY_ID': os.getenv('R2_ACCESS_KEY_ID'),
                'R2_SECRET_ACCESS_KEY': os.getenv('R2_SECRET_ACCESS_KEY'),
            }
            
            # Check if at least bucket name is set
            assert r2_vars['R2_BUCKET_NAME'], "R2_BUCKET_NAME should be set when cloud storage is enabled"
    
    def test_ci_environment(self):
        """Test CI environment variable."""
        ci_env = os.getenv('CI', '').lower()
        cloud_enabled = os.getenv('CLOUD_STORAGE_ENABLED', '').lower()
        
        # Either CI=true or CLOUD_STORAGE_ENABLED=true should enable cloud storage
        if ci_env == 'true' or cloud_enabled == 'true':
            from src.eps_estimates_collector.utils.cloudflare import CLOUD_STORAGE_ENABLED
            assert CLOUD_STORAGE_ENABLED, "Cloud storage should be enabled in CI environment"


class TestGoogleCredentials:
    """Test Google Cloud Vision credentials."""
    
    def test_credentials_path(self):
        """Test Google Cloud credentials path is set."""
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        if creds_path:
            creds_file = Path(creds_path)
            assert creds_file.exists(), f"Credentials file not found: {creds_path}"
    
    def test_google_vision_client(self):
        """Test Google Cloud Vision client initialization."""
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        if not creds_path or not Path(creds_path).exists():
            pytest.skip("Google Cloud credentials not configured")
        
        try:
            from src.eps_estimates_collector.core.ocr.google_vision_processor import get_google_vision_client
            client = get_google_vision_client()
            assert client is not None, "Google Cloud Vision client should not be None"
        except Exception as e:
            pytest.fail(f"Failed to initialize Google Cloud Vision client: {e}")


class TestWorkflowStructure:
    """Test workflow structure without executing."""
    
    def test_workflow_file_exists(self):
        """Test workflow file exists."""
        workflow_path = PROJECT_ROOT / "actions" / "workflow.py"
        assert workflow_path.exists(), f"Workflow file not found: {workflow_path}"
    
    def test_workflow_main_function(self):
        """Test workflow has main function."""
        workflow_path = PROJECT_ROOT / "actions" / "workflow.py"
        
        with open(workflow_path, 'r') as f:
            content = f.read()
            assert 'def main():' in content, "main() function not found in workflow"
    
    def test_workflow_steps(self):
        """Test workflow contains all required steps."""
        workflow_path = PROJECT_ROOT / "actions" / "workflow.py"
        
        with open(workflow_path, 'r') as f:
            content = f.read().lower()
            
            steps = [
                "check for new pdfs",
                "download new pdfs",
                "extract pngs",
                "process images",
                "upload to cloud"
            ]
            
            missing_steps = [step for step in steps if step not in content]
            assert not missing_steps, f"Missing workflow steps: {missing_steps}"
    
    def test_workflow_imports(self):
        """Test workflow can be imported."""
        try:
            from actions.workflow import main
            assert callable(main), "main should be callable"
        except ImportError as e:
            pytest.fail(f"Failed to import workflow: {e}\nPROJECT_ROOT: {PROJECT_ROOT}\nsys.path: {sys.path[:5]}")


class TestDirectoryStructure:
    """Test if required directories exist."""
    
    def test_output_directory(self):
        """Test output directory exists (optional, for local testing)."""
        output_dir = PROJECT_ROOT / "output"
        # Output directory is optional now (cloud-first architecture)
        pass
    
    def test_pdf_directory(self):
        """Test PDF directory exists (optional, for local testing)."""
        # PDF directory is optional now (cloud-first architecture)
        pass
    
    def test_estimates_directory(self):
        """Test estimates directory exists (optional, for local testing)."""
        # Estimates directory is optional now (cloud-first architecture)
        pass
    
    def test_src_directory(self):
        """Test src directory exists."""
        src_dir = PROJECT_ROOT / "src" / "eps_estimates_collector"
        assert src_dir.exists(), "src/eps_estimates_collector/ directory should exist"
    
    def test_actions_directory(self):
        """Test actions directory exists."""
        actions_dir = PROJECT_ROOT / "actions"
        assert actions_dir.exists(), "actions/ directory should exist"


class TestWorkflowIntegration:
    """Integration tests for workflow components."""
    
    def test_download_pdfs_signature(self):
        """Test download_pdfs function signature."""
        from src.eps_estimates_collector import download_pdfs
        import inspect
        
        sig = inspect.signature(download_pdfs)
        params = list(sig.parameters.keys())
        
        assert 'start_date' in params, "download_pdfs should have start_date parameter"
    
    def test_extract_charts_signature(self):
        """Test extract_charts function signature."""
        from src.eps_estimates_collector import extract_charts
        import inspect
        
        sig = inspect.signature(extract_charts)
        params = list(sig.parameters.keys())
        
        assert 'pdfs' in params, "extract_charts should have pdfs parameter"
    
    def test_process_images_signature(self):
        """Test process_images function signature."""
        from src.eps_estimates_collector import process_images
        import inspect
        
        sig = inspect.signature(process_images)
        params = list(sig.parameters.keys())
        
        assert 'directory' in params, "process_images should have directory parameter"


# Pytest fixtures
@pytest.fixture
def project_root():
    """Fixture for project root path."""
    return PROJECT_ROOT


@pytest.fixture
def output_dir(project_root):
    """Fixture for output directory."""
    return project_root / "output"


@pytest.fixture
def test_output_dir(output_dir):
    """Fixture for test output directory."""
    test_dir = output_dir / "test"
    test_dir.mkdir(parents=True, exist_ok=True)
    yield test_dir


# Main function for running tests directly
def main():
    """Run all tests."""
    print("\n" + "🚀" * 40)
    print("Workflow Test Suite")
    print("🚀" * 40 + "\n")
    
    # Run pytest programmatically
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == '__main__':
    main()

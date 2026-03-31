"""
Basic import tests to verify all modules can be imported successfully.
"""

import pytest


class TestImports:
    """Test that all main modules can be imported without errors."""

    def test_import_alert_manager(self):
        """Test alert_manager module imports successfully."""
        try:
            import alert_manager  # noqa: F401
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import alert_manager: {e}")

    def test_import_trading_analytics(self):
        """Test trading_analytics module imports successfully."""
        try:
            import trading_analytics  # noqa: F401
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import trading_analytics: {e}")

    def test_import_portfolio_analyzer(self):
        """Test portfolio_analyzer module imports successfully."""
        try:
            import portfolio_analyzer  # noqa: F401
            assert True
        except ImportError as e:
            pytest.fail(f"Failed to import portfolio_analyzer: {e}")


class TestEnvironment:
    """Test environment and dependencies."""

    def test_python_version(self):
        """Verify Python version is 3.11+."""
        import sys
        assert sys.version_info >= (3, 11), f"Python 3.11+ required, got {sys.version_info}"

    def test_required_packages(self):
        """Verify all required packages are installed."""
        required_packages = [
            'dhanhq',
            'python_dotenv',
            'aiohttp',
            'mcp',
            'websockets',
            'httpx',
            'pandas',
            'numpy',
            'ta',
            'scipy',
            'dateutil',
            'pytz',
            'fastapi',
            'uvicorn',
        ]

        for package in required_packages:
            try:
                __import__(package.replace('_', '-').replace('-', '_'))
            except ImportError:
                pytest.fail(f"Required package '{package}' is not installed")

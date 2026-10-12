"""CloudGuard AI Test Execution Runner.
Can be executed directly: python run_tests.py
"""
import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import pytest
except ImportError:
    print("pytest is not installed. Please run: pip install pytest")
    sys.exit(1)


def main():
    """Runs automated test suite with verbose output and test coverage."""
    print("=" * 70)
    print(" CloudGuard AI — Comprehensive Test Suite Runner")
    print("=" * 70)
    print(f"Project directory: {PROJECT_ROOT}")
    print(f"Target test folder: {PROJECT_ROOT / 'tests'}\n")

    args = [
        "-v",
        "--tb=short",
        str(PROJECT_ROOT / "tests")
    ]

    exit_code = pytest.main(args)
    print("\n" + "=" * 70)
    if exit_code == 0:
        print("✅ ALL CLOUDGUARD AI TESTS PASSED SUCCESSFULLY!")
    else:
        print(f"❌ TEST SUITE COMPLETED WITH EXIT CODE {exit_code}")
    print("=" * 70)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

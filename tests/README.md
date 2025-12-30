# Stock Tracker Test Suite

Comprehensive test suite for the Stock Tracker application covering all features, calculations, and workflows.

## Test Structure

```
tests/
├── conftest.py              # Pytest fixtures and configuration
├── test_data_manager.py     # Tests for DataManager class (CSV operations)
├── test_calculations.py     # Tests for TradeCalculator class (buy/sell/transfer logic)
├── test_new_features.py     # Tests for newly implemented features
├── test_integration.py      # Integration tests for complete workflows
└── test_data/              # Test data files (auto-created)
```

## Installation

### 1. Install Test Dependencies

```bash
pip install -r requirements-test.txt
```

### 2. Verify Installation

```bash
pytest --version
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run with Coverage Report

```bash
pytest --cov=utils --cov-report=html
```

This generates an HTML coverage report in `htmlcov/index.html`.

### Run Specific Test File

```bash
# Test DataManager only
pytest tests/test_data_manager.py

# Test TradeCalculator only
pytest tests/test_calculations.py

# Test new features only
pytest tests/test_new_features.py

# Test integration workflows only
pytest tests/test_integration.py
```

### Run Specific Test Class

```bash
pytest tests/test_calculations.py::TestBuyTradeProcessing
```

### Run Specific Test

```bash
pytest tests/test_calculations.py::TestBuyTradeProcessing::test_process_buy_trade_new_stock
```

### Run Tests in Parallel (Faster)

```bash
pytest -n auto
```

Uses all available CPU cores.

### Run with Verbose Output

```bash
pytest -v
```

Shows each test name as it runs.

### Run and Stop on First Failure

```bash
pytest -x
```

### Run Only Failed Tests from Last Run

```bash
pytest --lf
```

## Test Categories

### Unit Tests

**DataManager Tests** (`test_data_manager.py`)
- CSV file creation and initialization
- Reading/writing consolidated and trade data
- CRUD operations (Create, Read, Update, Delete)
- Data validation
- Helper methods (get_accounts, get_symbols)
- Data migration

**TradeCalculator Tests** (`test_calculations.py`)
- Buy trade calculations (new and existing holdings)
- Sell trade calculations (partial and full positions)
- Transfer trade processing
- Adding existing holdings (pre-populate)
- Rebuild holdings from trade history
- Delete trade and rebuild workflow
- Edge cases (large numbers, penny stocks, etc.)

### Feature Tests

**New Features Tests** (`test_new_features.py`)
- Buy preview calculations
- Sell preview calculations
- Dropdown sorting (alphabetical)
- Capital gain/loss column in trade history
- Row numbering in consolidated view
- Visual grouping displays
- Form state management
- Date validation
- Button styling

### Integration Tests

**Integration Tests** (`test_integration.py`)
- Complete buy workflows
- Complete sell workflows
- Multiple account trading
- Delete and rebuild workflows
- Complex trading scenarios (DCA, profit taking)
- Error recovery
- Data integrity verification

## Test Coverage

### Current Coverage

Run `pytest --cov=utils --cov-report=term` to see current coverage:

```
Expected coverage:
- DataManager: ~95%
- TradeCalculator: ~90%
- Overall: ~85%+
```

### Coverage Goals

- **Critical Paths:** 100% (buy, sell, rebuild)
- **Data Operations:** 95%+
- **Edge Cases:** 80%+
- **UI Logic:** 70%+ (some UI-specific code not unit-testable)

## Writing New Tests

### Test Naming Convention

```python
class TestFeatureName:
    """Test specific feature or component."""

    def test_should_do_something_when_condition(self):
        """Test description in plain English."""
        # Arrange
        # Act
        # Assert
```

### Using Fixtures

```python
def test_with_populated_data(populated_data_manager):
    """Use pre-populated test data."""
    record = populated_data_manager.get_consolidated_record('TFSA', 'AAPL')
    assert record is not None
```

### Available Fixtures

See `conftest.py` for all available fixtures:

- `temp_data_dir` - Temporary directory for test data
- `data_manager` - Fresh DataManager instance
- `calculator` - Fresh TradeCalculator instance
- `populated_data_manager` - DataManager with sample data
- `sample_consolidated_data` - Sample holdings DataFrame
- `sample_trades_data` - Sample trades DataFrame
- `buy_trade_data` - Template for buy trade
- `sell_trade_data` - Template for sell trade
- `existing_holding_data` - Template for pre-populate

### Creating New Fixtures

Add to `conftest.py`:

```python
@pytest.fixture
def my_custom_fixture():
    """Description of what this provides."""
    # Setup
    data = create_test_data()
    yield data
    # Teardown (if needed)
    cleanup(data)
```

## Testing Best Practices

### 1. Isolation

Each test should be independent:
- ✅ Use fixtures for setup
- ✅ Use temp directories (auto-cleaned)
- ❌ Don't rely on test execution order
- ❌ Don't share state between tests

### 2. Clarity

```python
# ✅ Good: Descriptive names
def test_buy_trade_calculates_correct_average_price():
    pass

# ❌ Bad: Vague names
def test_buy():
    pass
```

### 3. Arrange-Act-Assert

```python
def test_something():
    # Arrange - Set up test data
    trade = create_test_trade()

    # Act - Execute the code being tested
    result = calculator.process_trade(trade)

    # Assert - Verify the results
    assert result == expected_value
```

### 4. Test One Thing

Each test should verify one specific behavior.

### 5. Use Meaningful Assertions

```python
# ✅ Good: Explains what's being tested
assert record['Quantity'] == 100, "Quantity should be 100 after buying 100 shares"

# ❌ Bad: No context
assert record['Quantity'] == 100
```

## Troubleshooting

### Tests Fail with "Module not found"

```bash
# Make sure you're in the project root
cd /path/to/dad-stock-tracker

# Run tests
pytest
```

### Tests Fail with "Streamlit error"

Some tests may trigger Streamlit warnings. These are expected:
```
UserWarning: st.cache_resource will be deprecated...
```

### Coverage Report Not Generated

Install coverage:
```bash
pip install pytest-cov
```

### Tests Run Slow

Use parallel execution:
```bash
pytest -n auto
```

### Permission Errors

Make sure test directory is writable:
```bash
chmod +w tests/
```

## Continuous Integration (CI)

### GitHub Actions Example

Create `.github/workflows/tests.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.11
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      - name: Run tests
        run: pytest --cov=utils --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Test Data

Tests use temporary directories and don't affect your real data:

- ✅ Each test gets a fresh temp directory
- ✅ Temp directories are auto-deleted after tests
- ✅ Your actual `data/consolidated.csv` is never touched
- ✅ Your actual `data/trades.csv` is never touched

## Maintenance

### Adding Tests for New Features

1. Identify what needs testing
2. Choose appropriate test file:
   - Data operations → `test_data_manager.py`
   - Calculations → `test_calculations.py`
   - UI features → `test_new_features.py`
   - Workflows → `test_integration.py`
3. Write test using existing fixtures
4. Run `pytest --cov` to verify coverage
5. Ensure test passes and doesn't break others

### Updating Tests After Code Changes

When modifying application code:
1. Run tests to see what breaks
2. Update tests to match new behavior
3. Add new tests for new functionality
4. Verify all tests pass before committing

## Quick Reference

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=utils

# Run specific file
pytest tests/test_calculations.py

# Run with verbose output
pytest -v

# Run in parallel
pytest -n auto

# Stop on first failure
pytest -x

# Re-run failed tests
pytest --lf

# Show print statements
pytest -s

# Generate HTML coverage report
pytest --cov=utils --cov-report=html
```

## Support

For questions or issues with tests:
1. Check this README
2. Review test code for examples
3. Check pytest documentation: https://docs.pytest.org/

## Statistics

**Total Tests:** 100+
**Test Files:** 4
**Fixtures:** 10
**Coverage Target:** 85%+
**Execution Time:** ~10 seconds (with parallel execution)

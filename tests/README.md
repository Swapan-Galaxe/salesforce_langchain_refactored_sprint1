# Test Suite for Salesforce AI Assistant

This folder contains all test utilities and mock data for testing the LangChain-powered Salesforce AI Assistant without making actual Salesforce API calls.

## Files

### Core Test Files

1. **test_data.py**
   - Generates realistic mock Salesforce data
   - Creates 50 test leads with various statuses, ratings, and sources
   - Creates 30 test opportunities with realistic amounts and stages
   - Can export data to JSON for inspection

2. **mock_salesforce_agent.py**
   - Drop-in replacement for the real SalesforceAgent
   - Uses test data instead of making API calls
   - Maintains same interface as production agent
   - Still uses OpenAI for AI scoring (to test LangChain functionality)

3. **test_config.py**
   - Configuration manager for switching between mock and real data
   - Controlled via `USE_MOCK_DATA` environment variable
   - Automatically selects appropriate agent based on configuration

4. **test_runner.py**
   - Automated test suite for all system components
   - Tests mock data generation, AI scoring, and LangChain agent
   - Provides detailed test results and diagnostics

5. **app_test.py**
   - Test-enabled version of the main Streamlit app
   - Shows test mode banner when using mock data
   - Includes test data summary and export features
   - All functionality works identically with test data

## Usage

### Running Tests

From the project root directory:

```bash
# Run automated test suite
py tests/test_runner.py

# Or from within tests folder
cd tests
py test_runner.py
```

### Running Test App

From the project root directory:

```bash
# Run Streamlit app with test data
streamlit run tests/app_test.py
```

### Configuration

Set in your `.env` file:

```bash
# Use mock data (no Salesforce API calls)
USE_MOCK_DATA=true

# Use real Salesforce data
USE_MOCK_DATA=false
```

## Test Data Structure

### Mock Leads (50 total)
- Realistic names, companies, emails
- Various statuses: Open, Working, Closed, Nurturing, Qualified
- Multiple lead sources: Web, Phone, Partner, Trade Show, etc.
- Ratings: Hot, Warm, Cold
- Proper date fields (CreatedDate, LastModifiedDate)

### Mock Opportunities (30 total)
- Realistic opportunity names
- Amount ranges: $10K - $1M
- Various stages: Prospecting, Qualification, Negotiation, etc.
- Probability aligned with stage
- Proper date fields and relationships

## Benefits

1. **No API Limits**: Test unlimited without consuming Salesforce API calls
2. **Consistent Data**: Same test data every time for reliable testing
3. **Full Functionality**: All LangChain features work with mock data
4. **Easy Switching**: Toggle between test/production with one setting
5. **Safe Development**: No risk of affecting real Salesforce data
6. **Cost Effective**: Only uses OpenAI for AI features, not data fetching

## Test Scenarios

All these queries work with test data:

```
"Show me top 5 leads"
"What deals are at risk?"
"Give me pipeline summary"
"Compare top 2 opportunities"
"What should I focus on today?"
"Find stale leads"
"Suggest discount strategy for United Oil"
```

## Requirements

- Python 3.7+
- OpenAI API key (for AI scoring features)
- All dependencies from main requirements.txt

## Notes

- Test data is generated randomly each time the script runs
- OpenAI API calls are still made for AI scoring (to test LangChain)
- Salesforce API calls are completely avoided in test mode
- All 15 LangChain tools work with mock data

## Troubleshooting

**Issue**: OpenAI quota exceeded
**Solution**: Add credits to your OpenAI account or use a different API key

**Issue**: Import errors
**Solution**: Run tests from project root directory or ensure Python path is set correctly

**Issue**: Unicode encoding errors on Windows
**Solution**: All emojis have been replaced with text markers for Windows compatibility

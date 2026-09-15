# Fake Satellite API Tests

This directory contains test scripts for validating the fake-sat API endpoints.

## Running Tests

### Basic Usage

```bash
# Run all tests against default URL (http://localhost:8000)
python tests/test_endpoints.py

# Run tests against a custom URL
python tests/test_endpoints.py --url http://192.168.1.100:8000
```

### Requirements

Install dependencies:
```bash
pip install requests
```

## Test Suite

The test suite includes the following test categories:

1. **Health Checks** - Basic status endpoints
   - `/api/status`
   - `/katello/api/status`
   - `/apidoc/v2.json`

2. **List Endpoints** - Retrieve all resources
   - All 22 resource types (organizations, hosts, domains, users, etc.)

3. **Get by ID** - Retrieve specific resources
   - Sample retrieval of common resources

4. **Create Endpoints** - POST operations
   - Create organizations, locations, domains, subnets, users, products

5. **Update Endpoints** - PUT operations
   - Update organizations, locations, users

6. **Search/Filter** - Query with parameters
   - Test name-based searches
   - Test substring matches

7. **Pagination** - Test pagination parameters
   - page and per_page query parameters

8. **Sync Operations** - Repository and product sync
   - POST `/katello/api/repositories/{id}/sync`
   - POST `/katello/api/products/{id}/sync`

9. **Associations** - Relationship endpoints
   - Add/remove hosts from hostgroups
   - Assign hosts to organizations
   - Assign hosts to locations

## Test Output

The test suite provides detailed output showing:
- Test status (✓ passed, ✗ failed)
- HTTP status codes
- Summary with pass/fail counts
- Success percentage

Example output:
```
======================================================================
FAKE SATELLITE API TEST SUITE
======================================================================
Base URL: http://localhost:8000

======================================================================
HEALTH CHECKS
======================================================================
  ✓ [200] Foreman API Status
  ✓ [200] Katello API Status
  ✓ [200] API Documentation

======================================================================
TEST SUMMARY
======================================================================
Total:  75
Passed: 73 ✓
Failed: 2 ✗
Success Rate: 97.3%
======================================================================
```

## Integration with CI/CD

Use in CI/CD pipelines:
```bash
python tests/test_endpoints.py --url $FAKE_SAT_URL || exit 1
```

The script exits with:
- `0` if all tests pass
- `1` if any tests fail

# FastAPI Testing Plan

This document outlines the plan for improving test coverage of the FastAPI application. The current test coverage is 54%, with 302 out of 654 statements not covered. We'll work through this plan systematically, checking off items as they're completed.

## Current Coverage Status
- **Overall coverage**: 54%
- **Statements**: 654 total
- **Missed**: 302 statements
- **Covered**: 352 statements

## Already Tested Endpoints
- ✅ Health check endpoint (`/health`)
- ✅ User authentication (`/token`)
- ✅ User permissions (`/me/permissions`)
- ✅ User creation (`/users`)
- ✅ User listing (`/users`)
- ✅ User deletion (`/users/{username}`)
- ✅ Data provider creation (`/providers`)
- ✅ Data provider listing (`/providers`)
- ✅ Dataset creation (`/providers/{provider_id}/datasets`)
- ✅ XML archive creation (`/providers/{provider_id}/datasets/{dataset_id}/xml-archives`)
- ✅ Useful link creation (`/providers/{provider_id}/datasets/{dataset_id}/useful-links`)
- ✅ Harvest datasets endpoint (`/harvest/datasets`)

## Testing Plan

### 1. Authentication & User Management
- [x] Test user update endpoint (`PUT /users/{username}`)
- [x] Test get single user endpoint (`GET /users/{username}`)
- [x] Test provider association endpoints:
  - [x] Add provider association (`POST /users/{username}/providers`)
  - [x] Update provider association (`PUT /users/{username}/providers/{provider_id}`)
  - [x] Remove provider association (`DELETE /users/{username}/providers/{provider_id}`)
- [x] Test authentication failure scenarios:
  - [x] Expired token
  - [x] Invalid token format
  - [x] Non-existent user

### 2. Provider Management
- [x] Test get single provider endpoint (`GET /providers/{provider_id}`)
- [x] Test update provider endpoint (`PUT /providers/{provider_id}`)
- [x] Test delete provider endpoint (`DELETE /providers/{provider_id}`)
- [x] Test provider permission checks:
  - [x] Admin can access any provider
  - [x] User with provider role can access their provider
  - [x] User without provider role cannot access provider

### 3. Dataset Management
- [x] Test get datasets endpoint (`GET /providers/{provider_id}/datasets`)
- [x] Test get single dataset endpoint (`GET /providers/{provider_id}/datasets/{dataset_id}`)
- [x] Test update dataset endpoint (`PUT /providers/{provider_id}/datasets/{dataset_id}`)
- [x] Test delete dataset endpoint (`DELETE /providers/{provider_id}/datasets/{dataset_id}`)

### 4. XML Archive Management
- [x] Test get XML archives endpoint (`GET /providers/{provider_id}/datasets/{dataset_id}/xml-archives`)
- [x] Test XML archive permission checks

### 5. Useful Link Management
- [x] Test get useful links endpoint (`GET /providers/{provider_id}/datasets/{dataset_id}/useful-links`)
- [x] Test useful link permission checks

### 6. Error Handling & Edge Cases
- [x] Test handling of non-existent resources:
  - [x] Non-existent provider
  - [x] Non-existent dataset
  - [x] Non-existent XML archive
  - [x] Non-existent useful link
- [x] Test validation errors:
  - [x] Invalid provider data
  - [x] Invalid dataset data
  - [x] Invalid XML archive data
  - [x] Invalid useful link data
- [x] Test permission denied scenarios for all endpoints

### 7. Helper Functions
- [x] Test normalize_provider_roles function
- [x] Test password hashing and verification
- [x] Test token creation and validation

## Coverage Analysis and Improvement Strategy

After completing our initial testing plan, we've achieved 54% coverage (352 out of 654 statements). Let's analyze the remaining uncovered code and create a strategy to improve coverage further.

### 1. Uncovered Code Categories

Based on the coverage report, the following areas remain untested:

1. **Environment Setup and Configuration** (Lines 19-24):
   - Loading environment variables from different file locations

2. **Database Session Management** (Lines 40-42):
   - The actual database session creation and yielding

3. **Startup Event Handler** (Lines 238-240):
   - Database table creation at application startup

4. **Authentication Edge Cases** (Lines 307-316, 348-353):
   - User not found during authentication
   - Invalid password during authentication
   - Token expiration handling

5. **Permission Checks** (Lines 340-343):
   - Delete operation permission checks

6. **Error Handling in Endpoints** (Lines 813-817, 849-852, etc.):
   - Handling of non-existent resources in various endpoints
   - Error recovery paths

7. **Database Operations in Endpoints** (Lines 1079-1092, etc.):
   - Creating and updating records
   - Transaction handling

### 2. Improvement Strategy

Let's tackle these areas in order of priority:

#### Phase 1: Authentication and Permission Testing (Target: +5% coverage)

1. **Test Authentication Edge Cases**:
   - [x] Test authentication with non-existent user
   - [x] Test authentication with invalid password format
   - [x] Test detailed error handling in authentication

2. **Test Permission Check Edge Cases**:
   - [x] Test delete operation permission checks
   - [x] Test permission checks with malformed provider roles

#### Phase 2: Error Handling and Recovery (Target: +10% coverage)

1. **Test Error Handling in Endpoints**:
   - [ ] Test database connection errors
   - [ ] Test transaction rollback scenarios
   - [ ] Test concurrent modification scenarios

2. **Test Resource Not Found Scenarios**:
   - [ ] Test detailed error responses for missing resources
   - [ ] Test cascading deletes and their effects

#### Phase 3: Database Operations (Target: +8% coverage)

1. **Test Database Operations**:
   - [ ] Test complex query scenarios
   - [ ] Test database constraints and validation
   - [ ] Test database session management

#### Phase 4: Environment and Configuration (Target: +3% coverage)

1. **Test Environment Setup**:
   - [ ] Test environment variable loading from different locations
   - [ ] Test application behavior with missing environment variables
   - [ ] Test startup event handler

### 3. Implementation Approach

For each phase:

1. **Create Mock Tests**: Use mocking to simulate database interactions where appropriate
2. **Use Parameterized Tests**: Create parameterized tests for similar scenarios
3. **Focus on Edge Cases**: Specifically target error conditions and edge cases
4. **Measure Progress**: Run coverage after each test implementation to track progress

### 4. Specific Test Ideas

1. **Authentication Tests**:
   ```python
   def test_authentication_with_nonexistent_user():
       # Test authenticating with a username that doesn't exist

   def test_authentication_with_invalid_password():
       # Test authenticating with an invalid password format
   ```

2. **Permission Tests**:
   ```python
   def test_delete_permission_checks():
       # Test delete operations with different user roles

   def test_malformed_provider_roles():
       # Test behavior with malformed provider roles
   ```

3. **Error Handling Tests**:
   ```python
   def test_database_connection_error():
       # Test behavior when database connection fails

   def test_transaction_rollback():
       # Test transaction rollback on error
   ```

By following this strategy, we aim to increase the test coverage from 54% to at least 75% in manageable increments.

## Implementation Strategy

1. Start with high-priority endpoints that are completely untested
2. Focus on error handling scenarios next
3. Add tests for helper functions
4. Finally, add edge case tests

After each test implementation:
1. Run the test to ensure it passes
2. Check coverage to confirm improvement
3. Mark the item as completed in this plan

## Future Improvements

Now that we've completed all the planned tests, here are some ideas for further improving test coverage:

1. **Add more edge cases**: Test with different types of input data, including boundary values and special characters.
2. **Test database interactions**: Add tests that specifically focus on database operations, including transaction handling and error recovery.
3. **Test concurrency**: Add tests for concurrent requests to ensure thread safety.
4. **Test performance under load**: Add load tests to ensure the API performs well under heavy usage.
5. **Address deprecation warnings**: Update the codebase to address the Pydantic and FastAPI deprecation warnings.
6. **Parameterized tests**: Convert some of the repetitive tests to parameterized tests to improve maintainability.
7. **Test for specific business rules**: Add tests that verify specific business rules and domain logic.

## Notes
- Use unique identifiers for all test data to avoid unique constraint violations
- Ensure proper authentication headers are included for all protected endpoints
- Clean up test data after each test to avoid side effects

## Summary
All tests in the original testing plan have been successfully implemented, increasing the coverage from 43% to 54%. The tests now cover:

1. **Authentication and User Management**: Including user creation, update, deletion, and authentication with various error scenarios.
2. **Provider Management**: Including CRUD operations and permission checks.
3. **Dataset Management**: Including CRUD operations and permission checks.
4. **XML Archive Management**: Including retrieval and permission checks.
5. **Useful Link Management**: Including retrieval and permission checks.
6. **Error Handling**: Including validation errors and handling of non-existent resources.
7. **Helper Functions**: Including password hashing, token creation/validation, and provider role normalization.

The remaining uncovered code (46%) likely includes:
- Error handling branches that are difficult to trigger in tests
- Startup and shutdown code
- Database migration code
- Utility functions that are only used in specific scenarios
- Complex conditional logic with many branches

To further improve coverage, we can focus on the suggestions in the "Future Improvements" section.

# Ruff Linting Issues - Baseline Report

**Date:** 2026-02-04
**Total Issues:** 462
**Files Needing Reformatting:** 42

## Issue Categories (by frequency)

### Auto-Fixable Issues (315 total)

1. **W293 (256)**: Blank line contains whitespace
   - Auto-fix: `poetry run ruff format app/`
   - Tracked: aggregator-fdz

2. **I001 (47)**: Import block is un-sorted or un-formatted
   - Auto-fix: `poetry run ruff check --fix --select I app/`
   - Tracked: aggregator-dd4

3. **W291 (9)**: Trailing whitespace
   - Auto-fix: `poetry run ruff format app/`
   - Tracked: aggregator-fdz

4. **W292 (4)**: No newline at end of file
   - Auto-fix: `poetry run ruff format app/`
   - Tracked: aggregator-fdz

### Manual Review Required (147 total)

5. **B008 (71)**: Do not perform function call `Depends` in argument defaults
   - **Fix:** Refactor to modern `Annotated` pattern (FastAPI 0.95+)
   - Old: `db: AsyncSession = Depends(get_db)`
   - New: `db: Annotated[AsyncSession, Depends(get_db)]`
   - Benefits: Fixes B008 warning + improves type safety
   - Tracked: aggregator-53o

6. **F401 (28)**: Unused imports
   - Manual review required (may be used dynamically)
   - Tracked: aggregator-q9p

7. **B904 (24)**: Within `except`, raise exceptions with `raise ... from err`
   - Manual fix: Add `from err` to preserve stack traces
   - Tracked: aggregator-2hc

8. **E712 (11)**: Comparison to True/False should use `is`/`is not`
   - Manual fix: Change `== True` to `is True`

9. **E402 (5)**: Module level import not at top of file
   - Manual review: Reorganize imports

10. **F541 (3)**: f-string without any placeholders
    - Manual fix: Remove `f` prefix from plain strings

11. **B007 (3)**: Loop control variable not used
    - Manual fix: Use `_` for unused loop variables

12. **E722 (1)**: Bare except
    - Manual fix: Catch specific exceptions

## Phase 1 Approach

**Current state:** Documentation only, no enforcement

- Ruff configuration added to `pyproject.toml`
- All issues documented and tracked in bd
- CI runs `ruff check` and `ruff format --check` with `allow_failure: true`
- **Phase 2 will enforce:** After auto-fixable issues resolved, make CI checks blocking

## Running Ruff

```bash
# Check all issues
poetry run ruff check app/

# Check specific rule
poetry run ruff check --select I001 app/

# Auto-fix safe issues
poetry run ruff check --fix app/

# Format code
poetry run ruff format app/

# Check formatting (dry-run)
poetry run ruff format --check app/
```

## Related bd Tasks

- aggregator-fdz: Fix Ruff formatting issues (42 files) - P1
- aggregator-dd4: Fix Ruff import sorting (I001 - 47 issues) - P1
- aggregator-q9p: Fix unused imports (F401 - 28 issues) - P2
- aggregator-2hc: Improve exception handling (B904 - 24 issues) - P2
- aggregator-53o: Review B008 warnings (71 Depends() in defaults) - P3

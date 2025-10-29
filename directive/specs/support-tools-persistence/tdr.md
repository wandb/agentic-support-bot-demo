# Technical Design Review (TDR) — Support Tools Persistence

**Author**: AI Agent  
**Date**: 2025-10-29  
**Links**: Spec (`/directive/specs/support-tools-persistence/spec.md`), Impact (`/directive/specs/support-tools-persistence/impact.md`)

---

## 1. Summary

We are replacing the mocked `create_issue` and `get_issue` tool implementations with TinyDB-backed persistence to enable realistic evaluations and demos. Currently, created tickets are ephemeral and `get_issue` returns hardcoded mock data, making it impossible to test realistic workflows where users create a ticket and later check its status.

The solution uses TinyDB, a lightweight pure-Python JSON database library, to persist ticket data at the project root. The repo will ship with clean sample data (`db/tickets.sample.json`, committed) containing realistic demo tickets. Users manually copy this to a working database (`db/tickets.json`, gitignored) as a setup step, preventing test data from showing up as git changes. Users can reset to clean state anytime by re-copying the sample file.

Both the starter tools (step-2) and polished tools (step-3) will share the same database implementation, with only their docstrings differing. This enables evaluation scripts to work with pre-seeded tickets and verify that the agent correctly retrieves and presents ticket information.

## 2. Decision Drivers & Non‑Goals

**Drivers:**
- **Evaluation reliability**: Step 4 evaluations need tools that actually work end-to-end
- **Demo credibility**: Support bot should demonstrate real state tracking
- **Simplicity**: Must be trivial to set up (no external database servers)
- **Debuggability**: Database should be human-readable for troubleshooting

**Non‑Goals:**
- Production-ready concurrency (file locking, race conditions)
- Ticket updates/PATCH operations (only create + get for now)
- Advanced querying (search, filter, list all tickets)
- Database migrations or schema versioning
- Performance optimization for 1000+ tickets
- Multi-tenancy or user isolation

## 3. Current State — Codebase Map (concise)

**Key modules:**
- `examples/step-2/part-b/tools.py` — Starter tools with basic structure
- `examples/step-3/tools.py` — Polished tools with comprehensive docstrings
- Both files export `create_issue()` and `get_issue()` functions
- Both use Weave for observability (already initialized)

**Current implementation:**
- `create_issue()`: Generates UUID, creates dict, returns it (ephemeral)
- `get_issue()`: Returns hardcoded mock data regardless of ID

**Data models:**
- Ticket dict with fields: `id`, `title`, `description`, `status`, `priority`, `created_at`, `updated_at`
- No persistence, no schema validation

**External contracts:**
- Slide framework expects `TOOLS` list with `definition` and `implementation`
- Tool signatures are already established (cannot change)

**Observability:**
- Weave already traces all tool calls automatically
- No custom logging currently implemented

## 4. Proposed Design (high level, implementation‑agnostic)

### Overall Approach

1. **Sample data**: Repo ships with `db/tickets.sample.json` containing pre-populated realistic demo tickets (committed)
2. **User setup**: Users manually run `cp db/tickets.sample.json db/tickets.json` as a required setup step
3. **Database initialization**: Tools module checks for `db/tickets.json`, raises clear error if missing
4. **Working copy**: Tools module imports TinyDB and opens `db/tickets.json` (the gitignored working copy)
5. **Create operation**: `create_issue()` generates ticket dict, inserts into TinyDB, returns the dict
6. **Read operation**: `get_issue()` queries TinyDB by ID, returns ticket or error dict if not found
7. **Shared database**: All tools (step-2, step-3, step-4) reference the same `db/tickets.json` file
8. **Reset mechanism**: Users can manually reset by copying `tickets.sample.json` → `tickets.json`

### Component Responsibilities

**Module initialization** (runs on first import):
- Check if `db/` directory exists, create if needed
- Check if `db/tickets.json` exists
- If not found, raise FileNotFoundError with helpful message showing copy command
- Initialize TinyDB instance pointing to `db/tickets.json`

**TinyDB instance (module-level)**:
- Manages JSON file I/O
- Handles atomic writes
- Provides query interface

**`create_issue()` function**:
- Input validation (ensure title and description are non-empty strings)
- Generate unique UUID
- Generate timestamp
- Insert into database
- Return complete ticket dict

**`get_issue()` function**:
- Query database for matching ID
- Return ticket if found
- Return error dict if not found: `{"error": "Ticket not found", "id": issue_id}`

### Interfaces & Data Contracts

**TinyDB schema** (enforced by code, not TinyDB):
```python
{
    "id": str,           # UUID4 as string
    "title": str,        # User-provided
    "description": str,  # User-provided
    "status": str,       # Always "open" for new tickets
    "priority": str,     # "low" | "medium" | "high"
    "created_at": str,   # ISO 8601 timestamp
    "updated_at": str    # ISO 8601 timestamp (same as created_at initially)
}
```

**Error contract** (new):
```python
{
    "error": str,   # Human-readable error message
    "id": str       # The requested ID that wasn't found
}
```

### Error Handling

- **Database file missing**: Raise FileNotFoundError with clear message and copy command
- **Database directory missing**: Create `db/` directory if it doesn't exist (check at module load)
- **Ticket not found**: Return error dict, don't raise exception
- **Invalid inputs**: Validate title/description are non-empty, use defaults for optional params
- **Duplicate IDs**: UUID collision is astronomically unlikely, no special handling

### Performance Expectations

- **Create**: O(1) append to JSON array, ~1-10ms for small files
- **Get**: O(n) scan through tickets, acceptable for <1000 tickets
- **File size**: Typical ticket ~500 bytes, 1000 tickets = ~500KB, trivial
- **No caching**: Read from disk on every query (simplicity over performance)

## 5. Alternatives Considered

### Option A: Custom JSON read/write
**Approach**: Use `json.load()` and `json.dump()` directly
**Pros**: Zero dependencies, full control
**Cons**: Need to write file locking, atomic write logic, query logic
**Rejected**: Too much boilerplate for marginal benefit

### Option B: SQLite with Peewee ORM
**Approach**: Use SQLite + Peewee for schema and queries
**Pros**: More "real" database, better query performance
**Cons**: Binary file (not human-readable), need to define ORM models, overkill for 2 operations
**Rejected**: Complexity outweighs benefits, binary format hurts debuggability

### Option C: TinyDB (Chosen)
**Approach**: Use TinyDB library for JSON persistence
**Pros**: 
- One small dependency
- Human-readable JSON
- Simple API (`db.insert()`, `db.search()`)
- Handles file I/O atomically
- Perfect for this use case
**Cons**: One extra dependency
**Chosen**: Best balance of simplicity, readability, and functionality

## 6. Data Model & Contract Changes

### Database Structure

**File: `db/tickets.sample.json`** (committed, clean demo data)
```json
{
  "_default": {
    "1": {
      "id": "abc-123-def",
      "title": "API timeout errors",
      "description": "Getting 504 errors when calling /api/v1/runs",
      "status": "open",
      "priority": "high",
      "created_at": "2025-10-29T10:30:00Z",
      "updated_at": "2025-10-29T10:30:00Z"
    },
    "2": { ... }
  }
}
```

**File: `db/tickets.json`** (gitignored, working copy)
- Auto-created from sample on first run
- Modified by create_issue() calls during demos/tests
- Can be reset by copying from sample

Note: TinyDB auto-generates the `"_default"` table and numeric keys. Our app uses the `id` field within each document.

### API Changes

**No breaking changes** to function signatures or return types.

**Behavioral change**:
- `get_issue()` previously always returned a ticket (mock)
- `get_issue()` now returns error dict if ticket doesn't exist

### Backward Compatibility

**Existing code**: Any code calling these tools gets the same interface
**Migration**: None needed (no existing database to migrate)
**Deprecation**: None (replacing mock implementation, not changing API)

## 7. Security, Privacy, Compliance

### AuthN/AuthZ
- **Not applicable**: Demo tooling, no user authentication
- **Future consideration**: If this becomes multi-user, need to add user_id to tickets and filter queries

### Secrets Management
- **Not applicable**: No secrets stored in tickets
- **Risk**: User-provided text (title/description) is stored as-is
- **Mitigation**: This is demo data, not production PII

### PII Handling
- **Risk**: Ticket descriptions may contain user data in demos
- **Mitigation**: 
  - Add `db/tickets.json` to `.gitignore` so test data isn't committed
  - `db/tickets.sample.json` is committed (contains only sanitized demo data)
  - Document that users can reset to clean state with `cp db/tickets.sample.json db/tickets.json`

### Threat Model
- **File injection**: Not applicable (we control all write operations)
- **Path traversal**: Database path is hardcoded, no user input
- **DoS**: User could create many tickets, but this is demo tooling (acceptable risk)

## 8. Observability & Operations

### Logs
**Add**:
- `print(f"Using ticket database at {db_path}")` on successful module load
- `print(f"Ticket not found: {issue_id}")` when get_issue fails

**Errors**:
- Raise FileNotFoundError with helpful setup message if database file missing

**Existing**:
- Weave traces all tool calls (params, results, latency)

### Metrics
**Not needed**: Weave already tracks:
- Tool call counts
- Success/failure rates
- Latency percentiles

### Dashboards
**Not needed**: Demo tooling, can view in Weave UI

### Runbooks
**Not needed**: For production issues, solution is:
1. Check if `db/tickets.json` exists
2. Verify file is valid JSON
3. Re-seed with sample data if corrupted

### SLOs
**Not applicable**: Demo tooling, no uptime requirements

## 9. Rollout & Migration

### Feature Flags
**Not needed**: This is a one-time replacement of mock code

### Data Backfill
**Not needed**: No existing production data

### Deployment Plan
1. Create `db/tickets.sample.json` with realistic demo tickets
2. Implement TinyDB integration (raise error if database missing)
3. Add `db/tickets.json` to `.gitignore` (but NOT `tickets.sample.json`)
4. Update README with required manual copy step and reset instructions
5. Merge PR with TinyDB implementation + sample data

### Revert Plan
**Simple**: Revert git commit, tools go back to mocks

**Blast Radius**: 
- Only affects developers running the demo
- No production impact
- Tests may fail if they depend on persistence

## 10. Test Strategy & Spec Coverage (TDD)

### TDD Commitment
All tests will be written **before** implementation:
1. Write failing test
2. Confirm test fails
3. Implement minimal code to pass
4. Refactor
5. Repeat

### Spec → Test Mapping

| Acceptance Criterion | Test ID | Test Type |
|---------------------|---------|-----------|
| AC1: Create ticket saves to tickets.json | `test_create_issue_persists` | Unit |
| AC2: Get ticket returns exact created data | `test_get_issue_returns_created_ticket` | Integration |
| AC3: Get non-existent ticket returns error | `test_get_issue_not_found` | Unit |
| AC4: Pre-seeded tickets are retrievable | `test_get_preseeded_tickets` | Integration |
| AC5: Multiple tickets don't cross-contaminate | `test_multiple_tickets_isolated` | Integration |
| AC6: DB auto-initializes if missing | `test_db_auto_creates` | Unit |

### Test Tiers

**Unit Tests** (`tests/test_tools.py`):
- `test_create_issue_generates_valid_id`
- `test_create_issue_persists`
- `test_get_issue_not_found`
- `test_db_auto_creates`
- `test_input_validation`

**Integration Tests** (`tests/test_tools.py`):
- `test_get_issue_returns_created_ticket` (create then get)
- `test_multiple_tickets_isolated` (create 3, get each)
- `test_get_preseeded_tickets` (seed DB, then query)

**Fixtures** (`tests/conftest.py`):
- `temp_db_path`: Pytest fixture for isolated test database
- `seeded_db`: Fixture with 5 pre-populated tickets

### Negative & Edge Cases

- Empty title/description (validation error)
- Non-existent ticket ID
- Malformed ticket ID (still returns error, doesn't crash)
- Database file corrupted (TinyDB handles gracefully or we catch)
- Very long title/description (should work, but maybe add length limits)

### Performance Tests
**Not needed**: Demo tooling, no performance SLOs

### CI Requirements
- All tests run in CI (GitHub Actions already configured)
- Tests must pass before merge
- Use pytest with coverage reporting

## 11. Risks & Open Questions

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|---------|------------|
| DB file corruption | Low | Medium | Document backup/restore, provide seed script |
| Accidentally commit test data | Medium | Low | Add `db/` to `.gitignore` |
| Tests interfere with each other | Medium | Medium | Use temp DB paths in test fixtures |
| File path issues on Windows | Low | Low | Use `pathlib.Path` for cross-platform paths |

### Open Questions

1. **Q**: Should we add a `list_issues()` function for future?
   **A**: Out of scope for this PR. Add to non-goals.

2. **Q**: Should tickets have `updated_at` separate from `created_at`?
   **A**: Yes, keep the field for future PATCH operations, set equal to `created_at` for now.

3. **Q**: Should we validate priority enum server-side?
   **A**: Yes, validate in `create_issue()` to ensure only "low", "medium", "high" are stored.

## 12. Milestones / Plan (post‑approval)

### Task 1: Add TinyDB Dependency
**DoD**: 
- [ ] TinyDB added to `pyproject.toml`
- [ ] `uv lock` updated
- [ ] Dependency installs successfully in CI

### Task 2: Create Test Infrastructure
**DoD**:
- [ ] `temp_db_path` fixture in `tests/conftest.py`
- [ ] `seeded_db` fixture with 5 sample tickets
- [ ] Tests can run in isolation without interfering

### Task 3: Write Failing Tests (TDD)
**DoD**:
- [ ] All 6 acceptance criteria have corresponding test IDs
- [ ] All tests written and confirmed failing
- [ ] Negative tests written (not found, validation errors)

### Task 4: Create Sample Data
**DoD**:
- [ ] `db/tickets.sample.json` created with 10-15 realistic demo tickets
- [ ] Varied priorities (low, medium, high)
- [ ] Varied statuses (open, in_progress, resolved)
- [ ] Realistic W&B-related issues (API errors, auth issues, trace problems, etc.)
- [ ] File committed to git

### Task 5: Implement TinyDB Integration
**DoD**:
- [ ] `db/` directory auto-created on module load if missing
- [ ] Module init raises FileNotFoundError if `tickets.json` not found, with helpful setup message
- [ ] TinyDB instance initialized at module level pointing to `db/tickets.json`
- [ ] `create_issue()` inserts to database
- [ ] `get_issue()` queries database
- [ ] Input validation for priority enum
- [ ] All tests passing

### Task 6: Update Both Tools Files
**DoD**:
- [ ] `examples/step-2/part-b/tools.py` updated with TinyDB integration
- [ ] `examples/step-3/tools.py` updated with TinyDB integration
- [ ] Both use identical DB logic
- [ ] Tests pass for both versions

### Task 7: Update Documentation & .gitignore
**DoD**:
- [ ] `db/tickets.json` added to `.gitignore` (but NOT `db/tickets.sample.json`)
- [ ] README updated with manual setup step: `cp db/tickets.sample.json db/tickets.json`
- [ ] Document reset mechanism: `cp db/tickets.sample.json db/tickets.json`
- [ ] Example usage documented
- [ ] Troubleshooting section added

### Dependencies
- No external dependencies (all self-contained)
- Owner: Agent + Engineer review

---

**Approval Gate**: Do not start coding until this TDR is reviewed and approved.


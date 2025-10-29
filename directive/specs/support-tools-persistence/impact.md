# Impact Analysis — Support Tools Persistence

## Modules/packages likely touched
- `examples/step-2/part-b/tools.py` — Update `create_issue` and `get_issue` implementations to use TinyDB (starter version without descriptions)
- `examples/step-3/tools.py` — Update `create_issue` and `get_issue` implementations to use TinyDB (polished version with full descriptions)
- `examples/step-4/` — May need to add tools.py or update existing files to use persistent tools
- `pyproject.toml` — Add TinyDB as a dependency
- `tests/test_*.py` — Any existing tests for tools may need updates to handle persistence
- `db/` (new) — New directory at project root for database files
- `db/tickets.sample.json` (new) — Clean sample data, committed to git, pre-populated with realistic demo tickets
- `db/tickets.json` (new) — Working database copy, created by users via manual copy, gitignored
- `.gitignore` — Add `db/tickets.json` to avoid committing test/demo data changes (but NOT `db/tickets.sample.json`)

**Note:** Both step-2 and step-3 tools.py files need identical TinyDB implementation; the only difference is step-3 has better docstrings and tool descriptions for agent use. Both will reference the same shared `db/tickets.json` database file. Users manually copy `tickets.sample.json` → `tickets.json` to set up sample data.

## Contracts to update (APIs, events, schemas, migrations)

### No Breaking Changes
- `create_issue(title, description, priority)` signature remains unchanged
- `get_issue(issue_id)` signature remains unchanged
- Return types remain the same dictionary structure

### Behavioral Changes
- `create_issue`: Now persists to database instead of returning ephemeral data
- `get_issue`: Now returns actual stored tickets instead of mock data
- `get_issue`: Will return error/None for non-existent ticket IDs (new behavior)

### New Contract
- Both functions now depend on `tickets.json` file being accessible
- Database file location will likely be configurable via environment variable or default to workspace root

## Risks

### Security
- **Low risk**: TinyDB uses JSON file storage, no SQL injection vectors
- **File permissions**: Database file should be readable/writable by application
- **Input validation**: Ticket data fields should be validated (title/description length limits)
- **Mitigation**: Add basic validation for ticket fields, ensure file is not exposed publicly

### Performance/Availability
- **Low risk for demo scale**: File I/O on every operation
- **Potential bottleneck**: Large number of tickets (100+) could slow queries, but out of scope
- **File locking**: No concurrent write protection, but single-threaded usage is acceptable for demo
- **Mitigation**: Document that this is not production-ready for high concurrency

### Data integrity
- **Medium risk**: File corruption if process crashes during write
- **No transactions**: TinyDB doesn't have ACID guarantees
- **Lost tickets**: If `tickets.json` is deleted, all data is lost
- **Mitigation**: 
  - TinyDB handles atomic writes reasonably well
  - Document backup/restore approach for important evaluations
  - Consider adding `tickets.json` to `.gitignore` to avoid accidental commits of test data
  - Provide seed script to easily regenerate test tickets

## Observability needs

### Logs
- **Existing**: Weave already traces tool calls, so create/get operations will be logged automatically
- **Add**: Log database initialization (when `tickets.json` is created)
- **Add**: Log when ticket retrieval fails (ID not found) for debugging
- **Nice-to-have**: Log database file path on startup for clarity

### Metrics
- **Not needed**: This is demo/evaluation tooling, not production
- **Existing Weave tracing** captures:
  - Tool call frequency
  - Tool success/failure rates
  - Latency per operation

### Alerts
- **Not needed**: No production SLAs for demo tooling
- **Manual monitoring**: Developers can inspect `tickets.json` directly or check Weave traces


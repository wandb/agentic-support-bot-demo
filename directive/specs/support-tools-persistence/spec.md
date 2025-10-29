# Spec (per PR)

**Feature name**: Support Tools Persistence  
**One-line summary**: Replace mocked support ticket tools with TinyDB-backed persistence to enable realistic evaluations and demos

---

## Problem
The current support bot tools (`create_issue` and `get_issue`) use mocked data that doesn't persist between calls. This creates significant problems:
- **Evaluations are unreliable**: The agent can create a ticket but can't retrieve it, making it impossible to test realistic workflows where users ask about previously created tickets
- **Junk data**: `get_issue` returns hardcoded mock data that has no relationship to actually created tickets
- **Unrealistic demo experience**: The bot appears to work but doesn't actually track state, which undermines credibility

This needs to be fixed now because we're building evaluations (Step 4) that depend on realistic tool behavior.

## Goal
Support ticket tools should maintain state using TinyDB (a lightweight, pure-Python JSON database) that:
- Stores tickets created via `create_issue`
- Returns actual ticket data via `get_issue`
- Can be pre-seeded with sample tickets for evaluation scenarios
- Is simple enough to understand, debug, and modify (human-readable JSON)

## Success Criteria
- [ ] Agent can create a ticket and successfully retrieve it in the same conversation
- [ ] Evaluation runs can be seeded with pre-existing tickets that the agent can query
- [ ] Database file is human-readable JSON that can be manually inspected/edited
- [ ] Minimal dependencies (only TinyDB added to pyproject.toml)

## User Story
As a **demo user or evaluation script**, I want **support ticket operations to actually persist and retrieve real data**, so that **I can test realistic support workflows where users create tickets and later check their status**.

## Flow / States

**Happy Path:**
1. User says "Create a ticket for my API timeout issue"
2. Agent calls `create_issue`, which generates an ID and saves to `tickets.json`
3. Agent returns ticket ID to user
4. Later, user asks "What's the status of ticket XYZ?"
5. Agent calls `get_issue` with that ID, reads from `tickets.json`
6. Agent returns actual stored ticket details

**Edge Case:**
1. User asks for status of non-existent ticket ID
2. Agent calls `get_issue` with invalid ID
3. Function returns clear error message
4. Agent communicates that ticket wasn't found

## UX Links
- N/A (internal tooling, no UI changes)

## Requirements
**Must:**
- Use TinyDB to persist all ticket data to a single JSON file
- Store all fields from current mock: `id`, `title`, `description`, `status`, `priority`, `created_at`, `updated_at`
- Support `create_issue` to write new tickets
- Support `get_issue` to retrieve existing tickets by ID
- Return meaningful error for non-existent ticket IDs
- Include ability to seed database with sample tickets for evaluations
- Add TinyDB to pyproject.toml dependencies

**Must not:**
- Require external database servers (PostgreSQL, MySQL, etc.)
- Require complex setup or configuration
- Break existing tool interfaces (keep same parameters and return shapes)
- Introduce concurrency complexity (single-threaded access is fine)

## Acceptance Criteria
1. **Given** no existing tickets, **when** `create_issue` is called with title "Test Issue", **then** a new ticket is saved to `tickets.json` with all required fields
2. **Given** a ticket was created with ID "abc-123", **when** `get_issue("abc-123")` is called, **then** it returns the exact ticket data that was created
3. **Given** a ticket with ID "abc-123" exists, **when** `get_issue("xyz-999")` is called, **then** it returns an error indicating the ticket was not found
4. **Given** `tickets.json` is pre-seeded with 5 sample tickets, **when** `get_issue` is called with any of those IDs, **then** it returns the correct ticket data
5. **Given** multiple tickets are created in sequence, **when** each is retrieved by ID, **then** each returns its own unique data (no cross-contamination)
6. **Given** the database file doesn't exist yet, **when** `create_issue` is called, **then** it initializes a new file and creates the ticket successfully

## Non-Goals
- Multi-user concurrency support (file locking, race conditions)
- Ticket updates or status changes (out of scope for now)
- Advanced querying (searching, filtering, listing all tickets)
- Database migrations or schema versioning
- Performance optimization for large datasets (100+ tickets is fine)
- Additional CRUD operations beyond create and get


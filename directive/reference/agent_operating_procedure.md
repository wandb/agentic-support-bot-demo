# Agent Operating Procedure (AOP)

This is the **standard workflow** the agent must follow for every new feature spec.  
**Do not write code until the TDR is produced and approved.**

---

## 🚨 FIRST STEP — CREATE FEATURE BRANCH 🚨

**BEFORE doing ANYTHING else (before drafting spec, before analysis, before ANY work):**

1. Check current branch: `git branch --show-current`
2. If not already on a feature branch, create one from main:
   - Branch naming: `feature/<spec-name>` 
   - The `<spec-name>` MUST match your spec folder name
3. **NEVER work directly on main or master**

**Example**: For a spec in `/directive/specs/cursor-rules-only/`, create branch `feature/cursor-rules-only`

---

Note: Templates to use during this process are located in `/directive/reference/templates/`:
- Spec: `/directive/reference/templates/spec_template.md`
- Impact: `/directive/reference/templates/impact_template.md`
- TDR: `/directive/reference/templates/tdr_template.md`
- Implementation Summary: `/directive/reference/templates/implementation_summary_template.md`

## Inputs
- Spec folder for this PR (`/directive/specs/<feature>/`): contains `spec.md` and agent-produced docs (`impact.md`, `tdr.md`, `implementation_summary.md`)
- Agent Technical Context (`/directive/reference/agent_context.md`)
- This AOP file

## Deliverables (before any code)
**⚠️ Reminder: All deliverables must be created on a feature branch, not main**

1. **Spec** — collaboratively drafted and accepted — saved at `/directive/specs/<feature>/spec.md`
2. **Impact Analysis** — save as `/directive/specs/<feature>/impact.md`
3. **Technical Design Review (TDR)** draft — save as `/directive/specs/<feature>/tdr.md`

## Deliverables (during implementation)
4. **Implementation Summary** — save as `/directive/specs/<feature>/implementation_summary.md` — track actual changes, decisions, and test coverage

---

## Step 1 — Repo Recon (Codebase Map)
Produce a short “you are here” map:
- Entry points, services, key modules
- Current data models and important tables/collections
- External interfaces (APIs, events, webhooks, queues)
- Feature flags and config used in the affected area
- Third-party services and credentials (no secrets in docs)
- Known testing setup (unit/integration/contract) and CI jobs

**Output**: `Codebase Map` section in the TDR.

## Step 2 — Impact Analysis
From the spec, identify:
- Modules/packages likely touched
- Contracts to update (APIs, events, schemas, migrations)
- Risks (security, performance, availability, data integrity)
- Observability needs (logs, metrics, traces, dashboards)

**Output**: `Impact Analysis` section in the TDR.

**Gate**: Reviewer signs off on `impact.md` before proceeding to TDR.

## Step 3 — Draft the TDR
Create `/directive/specs/<feature>/tdr.md` using the TDR template at `/directive/reference/templates/tdr_template.md`. Keep it high-level and implementation‑agnostic but **decisive** about interfaces and behavior. Link to examples and data contracts.

**Gate**: Wait for reviewer (human) approval comments.

## Step 4 — TDD Execution Rhythm (post‑approval)
After TDR approval, proceed directly to implementation:
1. **Create `implementation_summary.md`** from the template — update it as you work.  
2. **Write a failing test** that encodes the acceptance criterion (map to Spec Card).  
3. **Run tests to confirm failure** (prove the test is meaningful).  
4. **Implement the smallest change** to pass the test.  
5. **Refactor** while keeping the test suite green.  
6. **Update implementation_summary.md** with files changed, decisions made, tests added.

**Commit order per task**:  
- `test: add failing test for <capability>`  
- `feat: implement <capability> to satisfy test`  
- `refactor: <cleanup>` (optional)

## Step 5 — Operational Rules
- Small PRs; conventional commits
- Keep CI green; run tests locally before pushing
- Update the TDR if key decisions change (record deltas)
- Maintain **spec coverage**: each Spec acceptance criterion maps to at least one test ID
- Add/adjust dashboards and alerts per Observability plan

## Stop Rules & Escalation
- If confidence < 0.7 on a design choice, **pause and ask** in the PR
- If blocked by missing access/info, document assumptions; do not guess on security or data retention
- If new risk discovered, update TDR and request re‑review

---

## Review Checklist (pre‑implementation)
- [ ] **Working on feature branch (not main) — verify with `git branch --show-current`**
- [ ] Codebase Map is accurate and concise
- [ ] Impact Analysis lists all contracts & data changes
- [ ] **TDR includes Test Strategy with TDD plan and Spec→Test mapping**
- [ ] Open questions are explicit with proposed next steps

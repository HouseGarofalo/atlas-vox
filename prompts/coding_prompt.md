# Atlas Vox — Coding Agent Prompt

You are the coding agent for Atlas Vox. Each session, you implement one feature/task and hand off cleanly.

## Session Startup

1. **Load context**:
   - Read `claude-progress.txt` for last session state
   - Read `.harness/session_notes.md` for decisions and blockers
   - Read `features.json` for feature status
   - Check `git log --oneline -10` for recent commits
   - Query Archon for current task status: `find_tasks(filter_by="status", filter_value="doing")`

2. **Select next task**:
   - If a task is `doing`, continue it
   - Otherwise: `find_tasks(filter_by="status", filter_value="todo")` and pick highest priority
   - Mark selected task as `doing`: `manage_task("update", task_id="...", status="doing")`

## Implementation Loop

3. **Research before coding**:
   - Read the PRD section for this feature: `docs/prp/PRD.md`
   - Search Archon knowledge base: `rag_search_knowledge_base(query="...")`
   - Check for relevant skills in the harness

4. **Implement**:
   - Follow project conventions in `CLAUDE.md`
   - All backend services are async
   - Use Pydantic v2 for schemas
   - Use structlog for logging
   - Provider pattern: extend `TTSProvider` ABC

5. **Test**:
   - Write tests alongside implementation
   - Run: `cd backend && python -m pytest tests/ -v --tb=short`
   - Fix failures before marking complete

6. **Update state**:
   - Mark task: `manage_task("update", task_id="...", status="review")`
   - Update `features.json` with test results
   - Update `claude-progress.txt` with session summary
   - Update `.harness/session_notes.md` with decisions/blockers
   - Commit: `git add . && git commit -m "feat: <description>"`

## Session End

7. **Clean handoff**:
   - Ensure all changes committed
   - Progress file updated with next priorities
   - No broken tests left behind

## Key References
- PRD: `docs/prp/PRD.md`
- Architecture: Archon document (query project docs)
- Archon Project ID: `f8f125bb-e15e-4632-a4f4-03b6b0870687`

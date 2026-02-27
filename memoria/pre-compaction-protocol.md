# Pre-Compaction Protocol

When context reaches **65%** (gentle reminder) or **75%** (urgent):

---

## 1. Commit Outstanding Work

```bash
git status
git add <files>
git commit -m "Description"
git push
```

## 2. Loose Ends Check

Before writing the handoff, verify:
- [ ] All code changes committed and pushed?
- [ ] Pending tasks mentioned but not done? (note them in handoff)
- [ ] Files discussed but not read/modified? (note if relevant)
- [ ] User questions fully answered?
- [ ] Any errors or bugs left unresolved? (note in handoff)
- [ ] Artifacts in `current/artifacts/` — are they all from THIS session?

## 3. Check Timestamps

```bash
cat memoria/current/.session-start   # session start (hook-written)
date '+%Y-%m-%d %H:%M:%S %Z'        # current time (use as session end)
```

Use these values in the session log below. Do not guess the time.

## 4. Write Session Log

Write `memoria/current/session-log.md` — the comprehensive record of this session:

**Template:**
```markdown
# Session Log: [Brief Description]
**Start:** YYYY-MM-DD HH:MM TZ (from step 3)
**End:** YYYY-MM-DD HH:MM TZ (from step 3)
**Context Used:** ~X%

## Summary
[2-3 sentences]

## Key Accomplishments
- [Major task 1]
- [Major task 2]

## Files Created / Modified / Removed
- `path/to/file` — [what changed]

## Commits Made
- `[hash]` — [commit message]

## Open Threads
- [Anything discussed but not completed]
```

## 5. Write Handoff

Write `memoria/current/handoff.md` — actionable notes for your next self:
- Immediate context (what was happening)
- What's in progress / left to do
- Key files to know
- Recent decisions
- Watch-out-fors and gotchas

**Safety net:** If you forget this step, the PreCompact hook will auto-generate minimal context from git activity. But a hand-written handoff is always better.

## 6. Update Orientation (if needed)

If significant new systems or patterns were established, update `memoria/orientation.md`.

## 7. Check Nuntiarium

Dismiss stale notifications so your post-compaction self starts clean:
```bash
python3 nuntiarium/nuntiarium.py check
python3 nuntiarium/nuntiarium.py dismiss <id>
```

## 8. Inform the Pilot

Before archiving, tell the user:
- Current context percentage
- What was accomplished this session
- Handoff has been written
- Ready to archive when confirmed

## 9. Archive Session Workspace

```bash
ca Expiscator -archive descriptive-topic-name
```

This will:
- Create `memoria/sessions/YYYY-MM-DD_HHMMx_descriptive-topic-name/`
- Move all contents from `current/` to the archive
- Recreate a clean `current/` workspace
- Print a summary of what was archived

Add `--commit` to auto-commit:
```bash
ca Expiscator -archive descriptive-topic-name --commit
```

## 10. Final Commit (if not using --commit)

```bash
git add memoria/sessions/ memoria/current/
git commit -m "Archive session: topic"
git push
```

---

*This protocol ensures continuity across compaction events.*

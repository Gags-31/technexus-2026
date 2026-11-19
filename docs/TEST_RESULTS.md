# TECHNEXUS 2026 — Local Test Results

## Environment

- Date: 2026-11-19
- OS: Windows (win32)
- Python: 3.12.10 (backend virtualenv `backend/.venv`)
- Node: v26.13.0, npm 12.0.2
- Database: isolated temporary SQLite database created by the test harness
- Command: `.\.venv\Scripts\python.exe -m pytest tests -q --tb=short`

## Result

```text
...........................                                              [100%]
27 passed, 1 warning in 12.68s
```

The single warning is a Starlette/TestClient `DeprecationWarning` about the `anyio.abc.BlockingPortal` alias. It does not affect application behaviour.

## Frontend build

```text
npm run build
✓ 1951 modules transformed
✓ built in 10.66s
index.html 0.97 kB │ gzip 0.52 kB
CSS 32.42 kB │ gzip 7.34 kB
JS 398.16 kB │ gzip 118.48 kB
```

## Test coverage

### Core and security (tests 1–14)

1. Health endpoint and public event identity (name, tagline, subtitle, organiser, schedule and four rounds).
2. Question bank integrity: 120 unique questions, 30 per domain, 10/8/7/5 per round per domain, four options, one correct answer, explanation and hint; 22 riddles; 12 memes.
3. Two administrator accounts with protected temp passwords and forced change gate (HTTP 428 on admin APIs).
4. Both administrators change temporary passwords and gain full access.
5. Registration rejects one-member teams, three-member teams and identical member emails.
6. Registration rejects duplicate emails across teams.
7. Two complete teams register successfully with unique IDs and `TNX-...` codes.
8. Separate participant logins for all four members with correct roles and team IDs.
9. Approval is blocked until both members confirm.
10. Both approved teams become eligible.
11. Team code validation is correct, rejects wrong codes and is scoped to the owning team.
12. Code revocation invalidates the old code; regeneration issues a new valid code.
13. Participant state never contains correct answers, correct options or explanations.
14. Participants cannot reach any administrator API by URL manipulation (HTTP 404).

### Synchronised competition (tests 15–27)

15. Rounds cannot be skipped (R2 start before R1 ends returns 409).
16. R1 start is identical for all eligible teams: same question IDs and same authoritative server timestamps; R2 remains locked.
17. Hints are participant-controlled, configurable, charged correctly and limited to once.
18. Answers autosave, synchronise between both members, and a submitted answer is locked against further changes.
19. Scores are calculated server-side with hint cost; private scoreboard is admin-only.
20. Browser violations are logged, counted and reviewable by an organiser.
21. Global pause/resume/end works and auto-completes sessions.
22. Break content serves a riddle with answer hidden until reveal and records guesses.
23. Final round is restricted to shortlisted teams only.
24. Results stay hidden until published, then become visible to participants.
25. CSV/PDF exports work for scoreboard and answer key and remain admin-only; audit log contains expected actions.
26. WebSocket tokens require an authenticated session and work for both participants and admins.
27. Logout revokes the server-side session.

## Bugs found and fixed during testing

- `AuditLog.metadata` shadowed SQLAlchemy's declarative metadata; renamed to `details` while preserving the `metadata` DB column and API field.
- `CompetitionSetting` was referenced incorrectly in `set_setting`.
- SQLite datetime round-trips lost timezone information, causing naive/aware comparison errors; introduced a `UTCDateTime` type decorator that always returns timezone-aware UTC values.
- `TeamAnswer.hint_count` was `None` on newly created unsaved answers, causing hint-mode comparison failures; initialised to zero.
- Test fixture scope/collection order initially allowed the competition module to run before registration state existed; fixture is now session-scoped and test files are ordered.
- Test expectation for per-round totals corrected to 40/32/28/20 (10/8/7/5 per domain across four domains).

## Not deployed

No deployment was performed. No public deployment URL is claimed.

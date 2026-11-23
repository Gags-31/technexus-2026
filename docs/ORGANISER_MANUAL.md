# TECHNEXUS 2026 — Organiser Manual

## Login

1. Open <http://localhost:8000/organiser/login>.
2. Use one of the two administrator accounts created by `python -m setup_admins`.
3. At first login you are forced to change the temporary password. Choose a strong password (minimum 10 characters, at least three of lowercase/uppercase/digit/symbol).
4. You will be redirected to `/organiser` after the change. Both administrator accounts have identical full access.

## Dashboard sections

### Overview
Live totals for teams, participants, approvals, active sessions, violations and WebSocket connections; current competition status; event configuration; round snapshot; editable schedule reference.

### Participant Registrations
Review every application. Each team must contain exactly one Leader and one Member and **both must have confirmed** before the Approve button becomes valid. If a participant could not complete confirmation, use **Approve anyway** as the organiser override; it marks both members confirmed, approves the team and records an audit entry. Use Reject with a note where needed. Decisions are audit-logged and broadcast as announcements.

### Team Management
View team IDs, institutions, members and unique `TNX-...` codes. Use:
- **New code** to regenerate a compromised code;
- **Revoke** to invalidate a code immediately;
- **Shortlist** to make a team eligible for the Final NEXUS SHOWDOWN.

Codes are shown to both members in their dashboards but must still be accompanied by each member's own login.

### Question Bank
Search/filter 120 questions by domain, round and difficulty. Read statements, options, marks and non-revealing hints. No correct answers appear here.

### Answer Key and Explanations
Private, organiser-only view with correct indices, correct option text, explanations and hints. Supports search, filters, CSV and printable PDF. **Never expose these exports to participants.**

### Round Management
Start, pause, resume and end R1–R4. Round start records a single server timestamp, creates eligible team sessions, sends identical questions to all eligible teams and locks future rounds. Every action requires confirmation. The server clock auto-ends rounds at the configured deadline and auto-submits saved answers.

### Reset and restart
**Round Management** also has two event-level controls, available at any time, including while a round is active:

- **Reset event** clears every round clock, answer, score, violation, break guess and shortlist flag, locks all four rounds, hides results, and broadcasts the change to connected participants.
- **Reset & restart** performs the same reset and immediately starts Round 1 with a fresh authoritative server clock for every eligible team.

Teams, registrations, team codes, questions, riddles, memes, settings and audit logs are preserved. Both actions require a confirmation dialog and are recorded in Audit Logs.

### Live Competition Monitor
Shows connected teams, member names, saved/submitted counts, violation counts, active status and review flags in real time via WebSocket.

### Live Scoreboard
Private real-time table: rank, team, R1–R4, total, correct, incorrect, unanswered, completion, active status, submission time and pending review. Search by team/college, sort by rank/total/name, filter by round/status, export CSV/PDF. Refreshes every 10 seconds plus WebSocket events. Participants cannot access this API or UI.

### Anti-Cheating Monitor
Lists visibility/focus/fullscreen violations with participant, team, round, action taken and review status. Mark reviewed, reinstate a team where appropriate, or apply the configured policy. All events are also in Audit Logs.

### Riddle and Meme Management
Review 22 original riddles and 12 original text meme templates. One riddle plus memes is served in the break after each of the first three rounds. Guesses are recorded; the answer and explanation reveal only after the countdown expires.

### Results
Publish or unpublish official results. Participant visibility stays off by default; only after publishing do participants see rank and totals. Export final results if required.

### Announcements
Post timed messages to all participants or to a specific audience. Announcements appear instantly in participant dashboards over WebSocket.

### Admin Settings
Edit event date/time, schedule, hint policy (enabled, mark cost, once/multiple, automatic/on-request), scoring (correct/incorrect marks, tie-breakers), break content, result visibility, final shortlist requirement, violation threshold and auto-submit/disqualification policy. Changes are audit-logged.

### Audit Logs
Immutable-style record of registrations, approvals, code changes, settings changes, round transitions, submissions, violations, exports and password changes. Filter by action/actor via the API if needed.

## Recommended event-day sequence

1. Verify **Overview** totals and that all approved teams have both members confirmed.
2. Confirm the event date/time and schedule in **Admin Settings**.
3. Test one browser as a participant: lobby code, fullscreen, answer autosave and hint.
4. Start R1 from **Round Management** only when ready; announce it.
5. Watch **Monitor** and **Scoreboard**; investigate review flags.
6. After R1 ends, confirm the break riddle appears for participants.
7. Repeat for R2/R3. Shortlist teams before R4.
8. End R4, evaluate, then publish results from **Results**.
9. Export CSV/PDF scoreboard and answer key for the official record; store privately.

## Export instructions

- Scoreboard CSV: `GET /api/admin/export/scoreboard.csv` (or the CSV button on the Live Scoreboard panel).
- Scoreboard PDF: `GET /api/admin/export/scoreboard.pdf`.
- Answer key CSV: `GET /api/admin/questions/export.csv`.
- Answer key PDF: `GET /api/admin/questions/export.pdf` (printable, paginated).

All require an authenticated full administrator session.

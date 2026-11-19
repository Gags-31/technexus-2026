# TECHNEXUS 2026 — Participant Manual

## Before the event

1. Register your **two-member** team at <http://localhost:8000/register>. One person is the **Team Leader**, the other is the **Team Member**. A one-person or three-person team is rejected.
2. Each member receives individual login credentials. Both members must log in at <http://localhost:8000/login> and confirm their registration. A team is not approved until **both** confirmations are recorded.
3. After organiser approval, both members see the same unique team code in the format `TNX-XXXXXX` in their dashboards. Keep it confidential. It is required to join the waiting lobby but does not replace your individual login.

## On event day

1. Log in individually at <http://localhost:8000/login>.
2. Open your dashboard at <http://localhost:8000/dashboard> and enter the team access code in the waiting lobby.
3. Enable fullscreen when a round is active. The platform monitors tab visibility, window focus and fullscreen exits using browser APIs. Repeated violations trigger warnings and may cause auto-submission or review under the organiser's disclosed policy.
4. Wait for the organiser to start a round. Future rounds stay locked; you cannot skip ahead or start early.
5. When the round starts, both members see the same questions and the same server-controlled timer. Answers autosave to the server and synchronise between members. Either member can submit; once a question is submitted, it is locked for the team.
6. Use the **Hint** button only when you want to. Hints are participant-controlled; the organiser decides whether they cost marks and whether they can be used once or multiple times.
7. Between rounds, enjoy the riddle and meme break. Submit a riddle guess before the countdown expires; the answer is revealed only when time runs out. Break guesses do not affect quiz scores unless an organiser explicitly enables a bonus.
8. Your score is hidden during competition. After the organiser publishes results, your rank and totals appear in the dashboard.

## Reconnecting

The dashboard reconnects to the server automatically if the network drops. On reload, it restores the current round, timer, saved answers and announcements from the server. Your individual login and the team code are both required to rejoin.

## Rules and fairness

- Exactly two members per team; one Leader and one Member.
- One final answer per question; last saved answer is used if you run out of time.
- No answer keys, explanations or correct indices are ever sent to participant clients during competition.
- Team codes are unique, expiring and revocable. Sharing them outside your team is prohibited.
- Suspected violations are logged and reviewed by organisers; reinstatement is at organiser discretion.

## Support

If your code is rejected, check that your team is approved, that you entered the current `TNX-...` code exactly, and ask an organiser to regenerate it if needed. If your session is disconnected, reload the page and log in again.

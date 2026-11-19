"""End-to-end tests 15-27: synchronised competition, scoring, monitoring and publishing."""
from __future__ import annotations

from sqlalchemy import select

from app.models import Riddle
from tests.harness import STATE, SessionLocal, api


def _team(label: str) -> dict:
    return STATE["teams"][0 if label == "alpha" else 1]


def _participant(label: str, role: str):
    return STATE["participants"][f"{_team(label)['public_id']}:{role}"]


def _admin():
    return STATE["admins"][0]


def test_15_rounds_cannot_be_skipped():
    response = _admin().post("/api/admin/rounds/2/start", json={})
    assert response.status_code == 409
    assert "previous round" in response.json()["detail"].lower()


def test_16_start_round_one_is_identical_for_all_eligible_teams():
    response = _admin().post("/api/admin/rounds/1/start", json={})
    assert response.status_code == 200, response.text
    state = response.json()
    assert state["status"] == "active" and state["question_count"] == 10
    assert state["server_start_at"] and state["ends_at"]

    states = [
        _participant("alpha", "leader").get("/api/participant/state").json(),
        _participant("beta", "member").get("/api/participant/state").json(),
    ]
    for participant_state in states:
        assert participant_state["active_round"]["id"] == 1
        assert [q["id"] for q in participant_state["active_round"]["questions"]] == [
            q["id"] for q in states[0]["active_round"]["questions"]
        ]
        assert participant_state["active_round"]["server_start_at"] == state["server_start_at"]
        assert participant_state["active_round"]["ends_at"] == state["ends_at"]
        assert all("correct_index" not in q for q in participant_state["active_round"]["questions"])
    rounds = _admin().get("/api/admin/rounds").json()
    assert rounds[1]["status"] == "locked"


def test_17_hints_are_participant_controlled_and_configurable():
    admin = _admin()
    settings = admin.patch("/api/admin/settings", json={
        "hints_enabled": True, "hint_cost_marks": 2, "hint_mode": "once",
    })
    assert settings.status_code == 200
    client = _participant("alpha", "leader")
    qid = client.get("/api/participant/state").json()["active_round"]["questions"][0]["id"]
    STATE["first_question_id"] = qid

    first = client.post(f"/api/participant/hints/{qid}", json={})
    assert first.status_code == 200, first.text
    assert first.json()["hint"] and first.json()["hint_cost"] == 2
    second = client.post(f"/api/participant/hints/{qid}", json={})
    assert second.status_code == 409


def test_18_shared_answers_autosave_and_final_answer_is_locked():
    admin = _admin()
    questions = admin.get("/api/admin/questions").json()
    qid = STATE["first_question_id"]
    correct = next(q["correct_index"] for q in questions if q["id"] == qid)
    wrong = (correct + 1) % 4

    leader = _participant("alpha", "leader")
    member = _participant("alpha", "member")
    assert leader.put(f"/api/participant/answers/{qid}", json={"selected_index": wrong}).status_code == 200
    member_state = member.get("/api/participant/state").json()
    member_answer = next(q["answer"] for q in member_state["active_round"]["questions"] if q["id"] == qid)
    assert member_answer["selected_index"] == wrong

    assert member.put(f"/api/participant/answers/{qid}", json={"selected_index": correct}).status_code == 200
    submitted = leader.post(f"/api/participant/answers/{qid}/submit", json={"selected_index": correct})
    assert submitted.status_code == 200, submitted.text
    assert member.post(f"/api/participant/answers/{qid}/submit", json={"selected_index": correct}).status_code == 409
    assert leader.put(f"/api/participant/answers/{qid}", json={"selected_index": wrong}).status_code == 409


def test_19_scoring_is_server_side_and_scoreboard_is_private():
    scoreboard = _admin().get("/api/admin/scoreboard").json()
    row = next(r for r in scoreboard["rows"] if r["team_id"] == _team("alpha")["id"])
    assert row["rounds"]["1"]["score"] == 8  # 10 correct - 2 hint cost
    assert row["correct"] == 1 and row["unanswered"] == 9
    assert scoreboard["rows"]
    # A participant cannot reach the private scoreboard.
    assert _participant("alpha", "leader").get("/api/admin/scoreboard").status_code == 404


def test_20_browser_violations_are_logged_and_reviewable():
    admin = _admin()
    assert admin.patch("/api/admin/settings", json={
        "violation_threshold": 2, "violation_auto_submit": False,
    }).status_code == 200
    client = _participant("beta", "leader")
    first = client.post("/api/participant/violations", json={"kind": "tab_hidden", "detail": "tab switch"})
    second = client.post("/api/participant/violations", json={"kind": "window_blur", "detail": "lost focus"})
    assert first.json()["count"] == 1 and first.json()["action"] == "warning"
    assert second.json()["count"] == 2 and second.json()["action"] == "review"

    violations = admin.get("/api/admin/violations").json()
    assert len(violations) >= 2
    target = next(v for v in violations if v["team_id"] == _team("beta")["id"])
    assert admin.post(f"/api/admin/violations/{target['id']}/review", json={
        "reinstate": True, "note": "Reviewed",
    }).status_code == 200


def test_21_global_pause_resume_and_end():
    admin = _admin()
    assert admin.post("/api/admin/rounds/1/pause", json={}).status_code == 200
    state = _participant("beta", "member").get("/api/participant/state").json()
    assert state["active_round"]["status"] == "paused"
    assert admin.post("/api/admin/rounds/1/resume", json={}).status_code == 200

    ended = admin.post("/api/admin/rounds/1/end", json={})
    assert ended.status_code == 200 and ended.json()["status"] == "ended"
    state = _participant("beta", "member").get("/api/participant/state").json()
    assert "active_round" not in state
    assert state["latest_ended_round"] == 1


def test_22_riddle_break_content_and_guesses():
    client = _participant("alpha", "leader")
    data = client.get("/api/participant/break").json()
    assert data["enabled"] is True
    assert data["riddle"] and data["memes"]
    assert data["riddle"]["answer"] is None  # hidden until reveal

    db = SessionLocal()
    try:
        answer = db.get(Riddle, data["riddle"]["id"]).answer
    finally:
        db.close()
    wrong = "definitely-not-" + answer
    result = client.post(f"/api/participant/riddle/{data['riddle']['id']}/guess", json={"guess": wrong})
    assert result.status_code == 200 and result.json()["correct"] is False


def test_23_final_round_restricted_to_shortlisted_teams():
    admin = _admin()
    assert admin.patch(f"/api/admin/teams/{_team('alpha')['id']}", json={"shortlisted": True}).status_code == 200
    for round_id in (2, 3):
        assert admin.post(f"/api/admin/rounds/{round_id}/start", json={}).status_code == 200
        assert admin.post(f"/api/admin/rounds/{round_id}/end", json={}).status_code == 200

    final = admin.post("/api/admin/rounds/4/start", json={})
    assert final.status_code == 200, final.text
    overview = next(r for r in admin.get("/api/admin/rounds").json() if r["id"] == 4)
    assert overview["registered_teams"] == 1
    assert "active_round" in _participant("alpha", "leader").get("/api/participant/state").json()
    assert "active_round" not in _participant("beta", "leader").get("/api/participant/state").json()


def test_24_results_hidden_until_published():
    client = _participant("alpha", "leader")
    assert client.get("/api/participant/results").json()["available"] is False
    assert _admin().post("/api/admin/results/publish", json={}).status_code == 200
    result = client.get("/api/participant/results").json()
    assert result["available"] is True
    assert result["results"]["team_id"] == _team("alpha")["id"]


def test_25_exports_and_audit_logs_available_to_admins_only():
    admin = _admin()
    csv = admin.get("/api/admin/export/scoreboard.csv")
    pdf = admin.get("/api/admin/export/scoreboard.pdf")
    answers_csv = admin.get("/api/admin/questions/export.csv")
    answers_pdf = admin.get("/api/admin/questions/export.pdf")
    assert csv.status_code == 200 and "csv" in csv.headers["content-type"]
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    assert answers_csv.status_code == 200 and "csv" in answers_csv.headers["content-type"]
    assert answers_pdf.status_code == 200 and answers_pdf.content[:4] == b"%PDF"

    actions = {row["action"] for row in admin.get("/api/admin/audit-logs").json()}
    assert {"registration.approved", "round.1.started", "team.code.revoked", "auth.password.changed"} <= actions
    assert _participant("beta", "member").get("/api/admin/export/scoreboard.csv").status_code == 404


def test_26_websocket_token_requires_an_authenticated_session():
    assert api().get("/api/auth/socket-token").status_code == 401
    participant = _participant("alpha", "member")
    response = participant.get("/api/auth/socket-token")
    assert response.status_code == 200 and response.json()["token"]
    assert _admin().get("/api/auth/socket-token").status_code == 200


def test_27_logout_revokes_the_session():
    client = _participant("beta", "member")
    assert client.get("/api/auth/me").json()["authenticated"] is True
    assert client.post("/api/auth/logout", json={}).status_code == 200
    assert client.get("/api/auth/me").json()["authenticated"] is False

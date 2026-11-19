"""End-to-end tests 1-14: identity, content, authentication, registration and RBAC."""
from __future__ import annotations

from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models import (
    MemeContent, Participant, Question, QuestionCorrectAnswer, QuestionExplanation,
    QuestionHint, QuestionOption, Riddle, Team,
)
from tests.harness import (
    ADMIN1_TEMP, ADMIN2_TEMP, CREDENTIALS_FILE, STATE, SessionLocal,
    api, login_admin, login_participant, team_payload,
)


def test_01_health_and_public_identity():
    root = STATE["root"]
    health = root.get("/api/health")
    assert health.status_code == 200 and health.json()["ok"] is True

    config = root.get("/api/public/config").json()
    assert config["event_name"] == "TECHNEXUS 2026"
    assert config["tagline"] == "CONNECT. THINK. CONQUER."
    assert config["subtitle"] == "THE ULTIMATE TECH QUIZ"
    assert "AWS Student Builder Group" in config["organiser"]
    assert config["team_size"] == 2
    assert len(config["schedule"]) == 12
    assert config["schedule"][0]["start"] == "11:00"
    assert config["schedule"][-1]["end"] == "14:15"
    assert [r["name"] for r in config["rounds"]] == [
        "TECH BLITZ", "DECODE THE DOMAIN", "TECH TROUBLESHOOTER", "NEXUS SHOWDOWN",
    ]


def test_02_question_bank_is_complete_and_original():
    db = SessionLocal()
    try:
        questions = list(db.scalars(select(Question).options(
            selectinload(Question.options), selectinload(Question.correct_answer),
            selectinload(Question.explanation), selectinload(Question.hint),
        )).all())
        assert len(questions) == 120
        domains = Counter(q.domain for q in questions)
        assert domains == {
            "Artificial Intelligence": 30, "Cloud Computing": 30,
            "Operating Systems": 30, "DBMS": 30,
        }
        # Each of the four domains contains 10/8/7/5 questions for R1-R4.
        rounds = Counter(q.round for q in questions)
        assert rounds == {1: 40, 2: 32, 3: 28, 4: 20}
        difficulties = Counter((q.round, q.difficulty) for q in questions)
        assert difficulties[(1, "Basic")] == 40
        assert difficulties[(2, "Intermediate")] == 32
        assert difficulties[(3, "Advanced")] == 28
        assert difficulties[(4, "Expert")] == 20
        assert len({q.id for q in questions}) == 120
        for q in questions:
            assert len(q.options) == 4
            assert q.correct_answer is not None and 0 <= q.correct_answer.option_position <= 3
            assert q.explanation and q.explanation.text.strip()
            assert q.hint and q.hint.text.strip()
        assert db.scalar(select(func.count()).select_from(Riddle)) >= 20
        assert db.scalar(select(func.count()).select_from(MemeContent)) >= 12
    finally:
        db.close()


def test_03_two_admin_accounts_with_protected_temp_passwords():
    text = CREDENTIALS_FILE.read_text(encoding="utf-8")
    assert "KEEP THIS FILE SECRET" in text
    assert "organiser" in text and "coorganiser" in text
    assert ADMIN1_TEMP in text and ADMIN2_TEMP in text

    first = login_admin("organiser", ADMIN1_TEMP)
    second = login_admin("coorganiser", ADMIN2_TEMP)
    assert first.get("/api/auth/me").json()["must_change_password"] is True
    assert second.get("/api/auth/me").json()["must_change_password"] is True
    # Forced reset gate blocks the whole admin surface.
    assert first.get("/api/admin/overview").status_code == 428
    assert second.get("/api/admin/overview").status_code == 428
    STATE["admin_temp_clients"] = [first, second]


def test_04_both_admins_change_temporary_passwords():
    new_passwords = ["NewOrganiserPass!45", "NewCoOrganiserPass!45"]
    clients = []
    for client, old, new in zip(STATE["admin_temp_clients"], [ADMIN1_TEMP, ADMIN2_TEMP], new_passwords):
        response = client.post("/api/auth/change-password", json={
            "current_password": old, "new_password": new,
        })
        assert response.status_code == 200, response.text
        assert client.get("/api/auth/me").json()["must_change_password"] is False
        assert client.get("/api/admin/overview").status_code == 200
        clients.append(client)
    STATE["admins"] = clients
    STATE["admin_passwords"] = new_passwords


def test_05_registration_rejects_wrong_team_sizes_and_same_email():
    root = STATE["root"]
    base = team_payload("Invalid", 1)
    one_member = {k: v for k, v in base.items() if k != "member"}
    assert root.post("/api/registration", json=one_member).status_code == 422

    three_members = dict(base)
    three_members["third_member"] = dict(base["member"])
    assert root.post("/api/registration", json=three_members).status_code == 422

    same_email = team_payload("Invalid", 2)
    same_email["member"]["email"] = same_email["leader"]["email"]
    assert root.post("/api/registration", json=same_email).status_code == 422


def test_06_registration_rejects_duplicate_email_across_teams():
    root = STATE["root"]
    first = team_payload("Duplicate", 1)
    assert root.post("/api/registration", json=first).status_code == 201
    second = team_payload("Duplicate", 2)
    second["leader"]["email"] = first["leader"]["email"]
    response = root.post("/api/registration", json=second)
    assert response.status_code == 409


def test_07_register_two_complete_teams_successfully():
    root = STATE["root"]
    STATE["teams"] = []
    for index, prefix in enumerate(["Alpha", "Beta"], start=1):
        payload = team_payload(prefix, index)
        response = root.post("/api/registration", json=payload)
        assert response.status_code == 201, response.text
        team = response.json()["team"]
        assert team["status"] == "pending"
        assert len(team["members"]) == 2
        assert {m["role"] for m in team["members"]} == {"leader", "member"}
        assert team["public_id"].startswith("TNX-")
        assert team["code"]["value"].startswith("TNX-") and len(team["code"]["value"]) == 10
        STATE["teams"].append({
            "id": team["id"], "public_id": team["public_id"], "code": team["code"]["value"],
            "payload": payload, "team": team,
        })
    assert STATE["teams"][0]["code"] != STATE["teams"][1]["code"]
    assert STATE["teams"][0]["public_id"] != STATE["teams"][1]["public_id"]


def test_08_separate_account_login_for_every_team_member():
    STATE["participants"] = {}
    for team in STATE["teams"]:
        payload = team["payload"]
        for role in ("leader", "member"):
            person = payload[role]
            client = login_participant(person["email"], person["password"])
            me = client.get("/api/auth/me").json()
            assert me["authenticated"] and me["kind"] == "participant"
            assert me["team_role"] == role and me["team_id"] == team["id"]
            STATE["participants"][f"{team['public_id']}:{role}"] = client


def test_09_approval_blocked_until_both_members_confirm():
    admin = STATE["admins"][0]
    team = STATE["teams"][0]
    response = admin.post(f"/api/admin/registrations/{team['id']}/approve", json={"notes": ""})
    assert response.status_code == 409

    for role in ("leader", "member"):
        client = STATE["participants"][f"{team['public_id']}:{role}"]
        assert client.post("/api/registration/confirm").status_code == 200
    me = STATE["participants"][f"{team['public_id']}:leader"].get("/api/participant/me").json()
    assert me["team"]["status"] == "confirmed"


def test_10_admin_approves_both_teams():
    admin = STATE["admins"][1]
    for team in STATE["teams"]:
        for role in ("leader", "member"):
            STATE["participants"][f"{team['public_id']}:{role}"].post("/api/registration/confirm")
        response = admin.post(f"/api/admin/registrations/{team['id']}/approve", json={"notes": "Verified"})
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "approved"


def test_11_team_code_validation_is_scoped_and_server_side():
    first = STATE["teams"][0]
    second = STATE["teams"][1]
    first_client = STATE["participants"][f"{first['public_id']}:leader"]
    second_client = STATE["participants"][f"{second['public_id']}:member"]

    assert first_client.post("/api/participant/lobby", json={"code": "TNX-WRONG"}).status_code == 403
    ok = first_client.post("/api/participant/lobby", json={"code": first["code"]})
    assert ok.status_code == 200 and ok.json()["joined"] is True
    assert second_client.post("/api/participant/lobby", json={"code": first["code"]}).status_code == 403


def test_12_access_code_can_be_revoked_and_regenerated():
    admin = STATE["admins"][0]
    team = STATE["teams"][0]
    client = STATE["participants"][f"{team['public_id']}:leader"]
    old_code = team["code"]

    assert admin.post(f"/api/admin/teams/{team['id']}/revoke-code", json={}).status_code == 200
    assert client.post("/api/participant/lobby", json={"code": old_code}).status_code == 403

    regenerated = admin.post(f"/api/admin/teams/{team['id']}/regenerate-code", json={})
    assert regenerated.status_code == 200
    new_code = regenerated.json()["code"]
    assert new_code != old_code and new_code.startswith("TNX-")
    team["code"] = new_code
    assert client.post("/api/participant/lobby", json={"code": new_code}).status_code == 200


def test_13_participant_state_never_contains_answers_or_explanations():
    client = STATE["participants"][f"{STATE['teams'][0]['public_id']}:leader"]
    state = client.get("/api/participant/state").json()
    serialised = str(state).lower()
    for forbidden in ("correct_index", "correct_option", "explanation"):
        assert forbidden not in serialised
    assert state["hints_enabled"] is True
    assert state["violation_threshold"] == 3


def test_14_participants_cannot_reach_administrator_surface_by_url():
    participant = STATE["participants"][f"{STATE['teams'][0]['public_id']}:leader"]
    for path in ("/api/admin/overview", "/api/admin/scoreboard", "/api/admin/questions", "/api/admin/settings"):
        assert participant.get(path).status_code == 404
    assert STATE["admins"][0].get("/api/admin/scoreboard").status_code == 200

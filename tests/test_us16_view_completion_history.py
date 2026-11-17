"""
US-16: View Completion History
Owner: Aryan Gupta

As a user, I want to see every day I completed a habit so that I can look back
at my progress over time.
"""

import json
from datetime import date

from extensions import db
from models import Habit


def add_habit(completed=(), **fields):
    habit = Habit(name="Drink water", completed_dates=json.dumps(list(completed)), **fields)
    db.session.add(habit)
    db.session.commit()
    return habit


def history(client, habit_id, **params):
    return client.get(f"/habit-tracker/habits/{habit_id}/history", query_string=params)


def test_us16_history_lists_all_completions_newest_first(client):
    """AC: I can see every day I completed the habit, most recent first."""
    habit = add_habit(["2026-11-01", "2026-11-05", "2026-11-03"])

    response = history(client, habit.id)

    assert response.status_code == 200
    data = response.get_json()
    assert data["name"] == "Drink water"
    assert data["completions"] == ["2026-11-05", "2026-11-03", "2026-11-01"]
    assert data["total_completions"] == 3


def test_us16_habit_with_no_completions_has_empty_history(client):
    """AC: A habit I haven't completed yet shows an empty history, not an error."""
    habit = add_habit()

    data = history(client, habit.id).get_json()

    assert data["completions"] == []
    assert data["total_completions"] == 0


def test_us16_history_includes_completions_from_the_complete_button(client):
    """AC: Days recorded with "mark complete" show up in the history."""
    habit = add_habit()

    client.post(f"/habit-tracker/{habit.id}/complete")

    assert history(client, habit.id).get_json()["completions"] == [date.today().isoformat()]


def test_us16_history_reads_legacy_comma_separated_dates(client):
    habit = Habit(name="Old habit", completed_dates="2026-10-01,2026-10-02")
    db.session.add(habit)
    db.session.commit()

    assert history(client, habit.id).get_json()["completions"] == ["2026-10-02", "2026-10-01"]


def test_us16_history_can_be_limited_to_a_date_range(client):
    """AC: I can narrow the history to a range of dates."""
    habit = add_habit(["2026-10-30", "2026-11-02", "2026-11-04", "2026-11-09"])

    data = history(client, habit.id, start="2026-11-01", end="2026-11-08").get_json()

    assert data["completions"] == ["2026-11-04", "2026-11-02"]
    assert data["total_completions"] == 2


def test_us16_invalid_date_range_is_rejected(client):
    habit = add_habit()

    assert history(client, habit.id, start="not-a-date").status_code == 400
    assert history(client, habit.id, start="2026-11-10", end="2026-11-01").status_code == 400


def test_us16_history_for_missing_habit_returns_404(client):
    """AC: Asking for a habit that doesn't exist returns Not Found, not a crash."""
    assert history(client, 999).status_code == 404


def test_us16_viewing_history_does_not_change_it(client):
    """AC: Viewing history is read-only."""
    stored = json.dumps(["2026-11-01", "2026-11-02"])
    habit = add_habit(["2026-11-01", "2026-11-02"])

    history(client, habit.id)

    assert db.session.get(Habit, habit.id).completed_dates == stored

"""
US-02: Add a Habit Schedule

As a user, I want to choose which days I plan to complete a habit so that I
can track habits that are not daily.
"""

from extensions import db
from models import Habit


def test_us02_schedule_is_saved_and_shown_on_dashboard(client):
    """AC: Selecting specific days and saving schedules the habit for only those days."""
    habit = Habit(name="Go to the gym")
    db.session.add(habit)
    db.session.commit()

    response = client.post(
        f"/habit-tracker/{habit.id}/schedule",
        data={"days": ["Mon", "Wed", "Fri"]},
        follow_redirects=True,
    )

    stored = db.session.get(Habit, habit.id)
    assert response.status_code == 200
    assert stored.scheduled_days_list == ["Mon", "Wed", "Fri"]
    assert b"Scheduled: Mon, Wed, Fri" in response.data


def test_us02_schedule_excludes_unselected_days(client):
    """AC: Days that were not selected are not part of the saved schedule."""
    habit = Habit(name="Journal")
    db.session.add(habit)
    db.session.commit()

    client.post(f"/habit-tracker/{habit.id}/schedule", data={"days": ["Tue", "Thu"]})

    stored = db.session.get(Habit, habit.id)
    assert "Sat" not in stored.scheduled_days_list
    assert "Sun" not in stored.scheduled_days_list
    assert set(stored.scheduled_days_list) == {"Tue", "Thu"}


def test_us02_resaving_schedule_replaces_previous_selection(client):
    """AC: Saving a new set of days replaces the old schedule rather than adding to it."""
    habit = Habit(name="Stretch")
    db.session.add(habit)
    db.session.commit()

    client.post(f"/habit-tracker/{habit.id}/schedule", data={"days": ["Mon"]})
    client.post(f"/habit-tracker/{habit.id}/schedule", data={"days": ["Tue", "Thu"]})

    stored = db.session.get(Habit, habit.id)
    assert stored.scheduled_days_list == ["Tue", "Thu"]


def test_us02_schedule_requires_at_least_one_day(client):
    """DoD: An empty selection is rejected and the existing schedule is left untouched."""
    habit = Habit(name="Read", scheduled_days="Mon")
    db.session.add(habit)
    db.session.commit()

    response = client.post(f"/habit-tracker/{habit.id}/schedule", data={})

    assert response.status_code == 400
    assert db.session.get(Habit, habit.id).scheduled_days == "Mon"


def test_us02_invalid_day_is_rejected(client):
    """AC: Only real weekday values can be scheduled."""
    habit = Habit(name="Walk")
    db.session.add(habit)
    db.session.commit()

    response = client.post(f"/habit-tracker/{habit.id}/schedule", data={"days": ["Funday"]})

    assert response.status_code == 400
    assert db.session.get(Habit, habit.id).scheduled_days is None


def test_us02_schedule_for_missing_habit_returns_404(client):
    """Dependency: scheduling requires an existing habit."""
    response = client.post("/habit-tracker/9999/schedule", data={"days": ["Mon"]})
    assert response.status_code == 404

"""
US-21: Change a Habit Schedule

As a user, I want to change the days a habit is scheduled so that it
continues to fit my routine.
"""

from datetime import date

from extensions import db
from models import Habit


def test_us21_changing_the_schedule_is_saved_and_shown(client):
    """AC: Selecting new days and saving them updates the habit's schedule."""
    habit = Habit(name="Run", scheduled_days="Mon,Wed,Fri")
    db.session.add(habit)
    db.session.commit()

    response = client.post(
        f"/habit-tracker/{habit.id}/schedule",
        data={"days": ["Tue", "Thu"]},
        follow_redirects=True,
    )

    stored = db.session.get(Habit, habit.id)
    assert response.status_code == 200
    assert stored.scheduled_days_list == ["Tue", "Thu"]
    assert b"Scheduled: Tue, Thu" in response.data


def test_us21_future_dates_follow_the_new_schedule(client):
    """AC: Future habit dates follow the new schedule, not the old one."""
    habit = Habit(name="Swim", scheduled_days="Mon,Wed,Fri")
    db.session.add(habit)
    db.session.commit()

    client.post(f"/habit-tracker/{habit.id}/schedule", data={"days": ["Sat", "Sun"]})
    db.session.refresh(habit)

    monday = date(2026, 11, 16)  # a day that was scheduled before the change
    saturday = date(2026, 11, 14)  # a day that is scheduled after the change
    assert not habit.is_scheduled_on(monday)
    assert habit.is_scheduled_on(saturday)

    rejected = client.post(f"/habit-tracker/{habit.id}/check-in",
                            data={"completed_on": monday.isoformat()})
    accepted = client.post(f"/habit-tracker/{habit.id}/check-in",
                            data={"completed_on": saturday.isoformat()})
    assert rejected.status_code == 400
    assert accepted.status_code == 302
    assert habit.completed_dates_list == [saturday]


def test_us21_streak_is_recalculated_against_the_new_schedule(client):
    """Risk: changing a schedule can change the streak, since it is computed
    from the habit's current scheduled days."""
    habit = Habit(name="Stretch", scheduled_days="Mon,Tue,Wed,Thu,Fri",
                  completed_dates='["2026-11-16", "2026-11-17"]')  # Mon, Tue
    db.session.add(habit)
    db.session.commit()
    today = date(2026, 11, 17)  # Tue
    assert habit.current_streak(today) == 2

    client.post(f"/habit-tracker/{habit.id}/schedule", data={"days": ["Mon", "Tue"]})
    db.session.refresh(habit)

    assert habit.current_streak(today) == 2


def test_us21_history_outside_the_new_schedule_is_preserved(client):
    """Dependency: completions recorded under the old schedule stay in history."""
    habit = Habit(name="Journal", scheduled_days="Mon,Wed,Fri",
                  completed_dates='["2026-11-16"]')  # Mon
    db.session.add(habit)
    db.session.commit()

    client.post(f"/habit-tracker/{habit.id}/schedule", data={"days": ["Sat", "Sun"]})
    db.session.refresh(habit)

    assert date(2026, 11, 16) in habit.completion_history()


def test_us21_empty_selection_leaves_the_existing_schedule_unchanged(client):
    """DoD: an invalid (empty) selection does not overwrite the saved schedule."""
    habit = Habit(name="Read", scheduled_days="Mon,Wed,Fri")
    db.session.add(habit)
    db.session.commit()

    response = client.post(f"/habit-tracker/{habit.id}/schedule", data={})

    assert response.status_code == 400
    assert db.session.get(Habit, habit.id).scheduled_days == "Mon,Wed,Fri"

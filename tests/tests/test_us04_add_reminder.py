"""
US-04: Add a Reminder

As a user, I want to add an optional reminder to a habit so that I do not
forget to complete it.
"""

from extensions import db
from models import Habit


def test_us04_add_reminder_to_existing_habit(client):
    """AC: A reminder is stored and displayed for an existing habit."""
    # Arrange
    habit = Habit(name="Go to the gym", description="Workout")
    db.session.add(habit)
    db.session.commit()

    # Act
    response = client.post(
        f"/habit-tracker/{habit.id}/reminder",
        data={"reminder_time": "18:00"},
        follow_redirects=True,
    )

    # Assert
    stored = db.session.get(Habit, habit.id)
    assert stored.reminder_time == "18:00"
    assert response.status_code == 200
    assert b"Reminder set for 18:00" in response.data


def test_us04_reminder_is_optional_and_can_be_removed(client):
    """A blank reminder time removes the reminder without deleting the habit."""
    habit = Habit(name="Read", reminder_time="20:30")
    db.session.add(habit)
    db.session.commit()

    response = client.post(
        f"/habit-tracker/{habit.id}/reminder",
        data={"reminder_time": ""},
        follow_redirects=True,
    )

    stored = db.session.get(Habit, habit.id)
    assert response.status_code == 200
    assert stored is not None
    assert stored.reminder_time is None
    assert b"Reminder set for" not in response.data


def test_us04_rejects_invalid_reminder_time(client):
    """Invalid times are rejected and do not overwrite the saved reminder."""
    habit = Habit(name="Study", reminder_time="17:00")
    db.session.add(habit)
    db.session.commit()

    response = client.post(
        f"/habit-tracker/{habit.id}/reminder",
        data={"reminder_time": "25:99"},
    )

    assert response.status_code == 400
    assert db.session.get(Habit, habit.id).reminder_time == "17:00"

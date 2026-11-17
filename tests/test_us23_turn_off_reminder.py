"""
US-23: Turn Off a Reminder
Owner: Aryan Gupta

As a user, I want to turn off a habit's reminder so that I stop getting
reminded, without deleting the habit or losing the reminder time I chose.
"""

from extensions import db
from models import Habit


def add_habit(**fields):
    habit = Habit(name="Go to the gym", **fields)
    db.session.add(habit)
    db.session.commit()
    return habit


def turn_off(client, habit_id, **kwargs):
    return client.post(f"/habit-tracker/{habit_id}/reminder/off", **kwargs)


def turn_on(client, habit_id, **kwargs):
    return client.post(f"/habit-tracker/{habit_id}/reminder/on", **kwargs)


def test_us23_turning_off_a_reminder_stops_it(client):
    """AC: After I turn a reminder off, the habit no longer has an active reminder."""
    habit = add_habit(reminder_time="18:00")

    response = turn_off(client, habit.id)

    assert response.status_code == 302
    stored = db.session.get(Habit, habit.id)
    assert stored.reminder_time is None
    assert stored.reminder_on is False


def test_us23_turned_off_reminder_is_not_shown_on_dashboard(client):
    habit = add_habit(reminder_time="18:00")

    page = turn_off(client, habit.id, follow_redirects=True)

    assert page.status_code == 200
    assert b"Go to the gym" in page.data
    assert b"Reminder set for 18:00" not in page.data


def test_us23_turning_off_keeps_the_habit_and_its_details(client):
    """AC: Turning off a reminder doesn't delete or change the habit."""
    habit = add_habit(description="Workout", reminder_time="18:00", scheduled_days="Mon,Wed")

    turn_off(client, habit.id)

    stored = db.session.get(Habit, habit.id)
    assert (stored.name, stored.description, stored.scheduled_days) == (
        "Go to the gym", "Workout", "Mon,Wed")
    assert Habit.query.count() == 1


def test_us23_reminder_can_be_turned_back_on_with_the_same_time(client):
    """AC: Turning the reminder back on restores the time I had chosen."""
    habit = add_habit(reminder_time="18:00")
    turn_off(client, habit.id)

    response = turn_on(client, habit.id, follow_redirects=True)

    assert response.status_code == 200
    assert db.session.get(Habit, habit.id).reminder_time == "18:00"
    assert b"Reminder set for 18:00" in response.data


def test_us23_turning_off_twice_is_harmless(client):
    habit = add_habit(reminder_time="07:30")

    turn_off(client, habit.id)
    turn_off(client, habit.id)
    turn_on(client, habit.id)

    assert db.session.get(Habit, habit.id).reminder_time == "07:30"


def test_us23_turning_on_without_a_saved_reminder_is_rejected(client):
    habit = add_habit()

    assert turn_on(client, habit.id).status_code == 400
    assert db.session.get(Habit, habit.id).reminder_time is None


def test_us23_setting_a_new_time_replaces_a_turned_off_reminder(client):
    habit = add_habit(reminder_time="18:00")
    turn_off(client, habit.id)

    client.post(f"/habit-tracker/{habit.id}/reminder", data={"reminder_time": "09:15"})

    stored = db.session.get(Habit, habit.id)
    assert stored.reminder_time == "09:15"
    assert stored.paused_reminder_time is None


def test_us23_reminder_status_is_included_in_habit_details(client):
    habit = add_habit(reminder_time="18:00")
    assert client.get(f"/habit-tracker/habits/{habit.id}").get_json()["reminder_on"] is True

    turn_off(client, habit.id)

    data = client.get(f"/habit-tracker/habits/{habit.id}").get_json()
    assert data["reminder_on"] is False
    assert data["reminder_time"] is None


def test_us23_missing_habit_returns_404(client):
    assert turn_off(client, 999).status_code == 404
    assert turn_on(client, 999).status_code == 404

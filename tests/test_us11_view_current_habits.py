"""
US-11: View Current Habits
Owner: Aryan Gupta

As a user, I want to view my current habits and the full details of any one
of them, so I know exactly what I'm tracking.
"""

from datetime import datetime

from extensions import db
from models import Category, Habit


def add_habit(**fields):
    habit = Habit(**fields)
    db.session.add(habit)
    db.session.commit()
    return habit


def test_us11_lists_all_current_habits(client):
    """AC: Every habit I've created is returned when I view my habits."""
    add_habit(name="Drink water")
    add_habit(name="Read 20 pages", frequency="weekly")

    response = client.get("/habit-tracker/habits")

    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] == 2
    assert {habit["name"] for habit in data["habits"]} == {"Drink water", "Read 20 pages"}


def test_us11_lists_newest_habits_first(client):
    add_habit(name="Older habit", created_at=datetime(2026, 1, 1))
    add_habit(name="Newer habit", created_at=datetime(2026, 2, 1))

    names = [habit["name"] for habit in client.get("/habit-tracker/habits").get_json()["habits"]]

    assert names == ["Newer habit", "Older habit"]


def test_us11_empty_list_when_there_are_no_habits(client):
    """AC: With no habits, I get an empty list instead of an error."""
    response = client.get("/habit-tracker/habits")

    assert response.status_code == 200
    assert response.get_json() == {"count": 0, "habits": []}


def test_us11_view_one_habit_shows_all_details(client):
    """AC: Viewing a habit shows its name, description, category, frequency,
    reminder and schedule."""
    health = Category(name="Health")
    db.session.add(health)
    habit = add_habit(name="Drink water", description="8 glasses a day", category=health,
                      frequency="daily", reminder_time="08:00", scheduled_days="Mon,Wed")

    response = client.get(f"/habit-tracker/habits/{habit.id}")

    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == habit.id
    assert data["name"] == "Drink water"
    assert data["description"] == "8 glasses a day"
    assert data["category"] == "Health"
    assert data["frequency"] == "daily"
    assert data["reminder_time"] == "08:00"
    assert data["scheduled_days"] == ["Mon", "Wed"]


def test_us11_view_habit_without_optional_details(client):
    habit = add_habit(name="Stretch")

    data = client.get(f"/habit-tracker/habits/{habit.id}").get_json()

    assert data["description"] is None
    assert data["category"] is None
    assert data["reminder_time"] is None
    assert data["scheduled_days"] == []


def test_us11_viewing_a_missing_habit_returns_404(client):
    """AC: Asking for a habit that doesn't exist returns Not Found, not a crash."""
    assert client.get("/habit-tracker/habits/999").status_code == 404


def test_us11_viewing_habits_does_not_change_them(client):
    """AC: Viewing is read-only."""
    habit = add_habit(name="Meditate", description="10 minutes")

    client.get("/habit-tracker/habits")
    client.get(f"/habit-tracker/habits/{habit.id}")

    stored = db.session.get(Habit, habit.id)
    assert (stored.name, stored.description) == ("Meditate", "10 minutes")
    assert Habit.query.count() == 1

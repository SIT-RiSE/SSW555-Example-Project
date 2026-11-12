"""
US-03: Set Habit Frequency

As a user, I want to choose how frequently I complete a habit so that the
habit matches my actual routine.
"""

from sqlalchemy import text

from app import init_db
from extensions import db
from models import Habit


def test_us03_create_habit_with_frequency(client):
    """AC: The selected frequency is stored when a habit is created."""
    # Act
    response = client.post(
        "/habit-tracker",
        data={
            "name": "Go to the gym",
            "description": "Workout",
            "frequency": "weekly",
        },
        follow_redirects=True,
    )

    # Assert
    stored = Habit.query.filter_by(name="Go to the gym").first()
    assert response.status_code == 200
    assert stored is not None
    assert stored.frequency == "weekly"


def test_us03_edit_habit_frequency(client):
    """AC: The selected frequency is stored when an existing habit is edited."""
    # Arrange
    habit = Habit(name="Read", frequency="daily")
    db.session.add(habit)
    db.session.commit()

    # Act
    response = client.post(
        f"/habit-tracker/{habit.id}/edit",
        data={"name": "Read", "frequency": "monthly"},
        follow_redirects=True,
    )

    # Assert
    stored = db.session.get(Habit, habit.id)
    assert response.status_code == 200
    assert stored.frequency == "monthly"


def test_us03_frequency_is_displayed_with_habit(client):
    """The saved frequency is shown to the user alongside the habit."""
    habit = Habit(name="Meditate", frequency="weekly")
    db.session.add(habit)
    db.session.commit()

    response = client.get("/habit-tracker")

    assert response.status_code == 200
    assert b"Meditate" in response.data
    assert b"Weekly" in response.data


def test_us03_defaults_to_daily_when_not_selected(client):
    """A habit created without a frequency falls back to daily."""
    client.post(
        "/habit-tracker",
        data={"name": "Drink water"},
        follow_redirects=True,
    )

    stored = Habit.query.filter_by(name="Drink water").first()
    assert stored is not None
    assert stored.frequency == "daily"


def test_us03_rejects_invalid_frequency(client):
    """Invalid frequencies are rejected and do not overwrite the saved value."""
    habit = Habit(name="Study", frequency="daily")
    db.session.add(habit)
    db.session.commit()

    response = client.post(
        f"/habit-tracker/{habit.id}/edit",
        data={"name": "Study", "frequency": "every-other-blue-moon"},
    )

    assert response.status_code == 400
    assert db.session.get(Habit, habit.id).frequency == "daily"


def test_us03_rejects_invalid_frequency_on_create(client):
    """A habit is not created with an unsupported frequency."""
    response = client.post(
        "/habit-tracker",
        data={"name": "Stretch", "frequency": "hourly"},
    )

    assert response.status_code == 400
    assert Habit.query.count() == 0


def test_us03_streak_and_progress_use_frequency_period(client):
    """Streak and progress labels follow the habit's frequency."""
    db.session.add(Habit(name="Call family", frequency="monthly"))
    db.session.commit()

    response = client.get("/habit-tracker")

    assert b"0 month streak" in response.data
    assert b"0% this month" in response.data


def test_us03_upgrade_adds_frequency_to_existing_habits(app):
    """Existing databases gain the frequency column with habits defaulting to daily."""
    db.session.remove()
    db.drop_all()
    with db.engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE habit (id INTEGER PRIMARY KEY, name VARCHAR(100) NOT NULL, "
            "description TEXT, reminder_time VARCHAR(5), created_at DATETIME, "
            "completed_dates TEXT)"
        ))
        connection.execute(text("INSERT INTO habit (name) VALUES ('Read')"))

    init_db()
    init_db()

    assert Habit.query.one().frequency == "daily"

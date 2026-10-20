"""
US-01: Create a New Habit
Owner: Aryan Gupta

As a college student trying to build better routines, I want to create a new
habit with a name, category (Health, Work, or Other), and daily goal so that I
can start tracking something specific, like drinking 8 glasses of water or
calling home every day.
"""

from models import Habit


def test_us01_create_habit_saves_and_shows_on_dashboard(client):
    """AC: A new habit is saved and appears on the habit tracker page."""
    # Arrange
    habit_data = {"name": "Drink water", "description": "8 glasses a day"}

    # Act
    response = client.post("/habit-tracker", data=habit_data)
    page = client.get("/habit-tracker")

    # Assert
    assert response.status_code == 302
    stored = Habit.query.filter_by(name="Drink water").first()
    assert stored is not None
    assert stored.description == "8 glasses a day"
    assert b"Drink water" in page.data


def test_us01_habit_without_name_is_not_created(client):
    """AC: If I try to save

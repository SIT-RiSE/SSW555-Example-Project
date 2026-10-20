"""
US-01: Mark Habit as Complete

As a busy student, I want to mark a habit as done for the day so that I
can see my progress and stay motivated to keep my streak going.
"""

import pytest

from models import Habit


@pytest.mark.xfail(reason="US-01: marking a habit as complete is not implemented yet")
def test_us01_mark_habit_as_complete(client):
    """AC: Marking a habit done increments its streak count."""
    # Arrange
    habit = Habit(name="Drink water", description="Hydration", streak=0)
    from extensions import db
    db.session.add(habit)
    db.session.commit()

    # Act
    client.post(f"/habit-tracker/{habit.id}/complete")

    # Assert
    stored = Habit.query.get(habit.id)
    assert stored.streak == 1
    assert stored.completed_today is True

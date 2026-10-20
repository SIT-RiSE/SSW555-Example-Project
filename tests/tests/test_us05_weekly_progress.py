"""
US-05: View Weekly Progress Chart

As a student, I want to view a chart of my habit completion over the past
week so that I can spot patterns in when I'm most consistent.
"""

import pytest


@pytest.mark.xfail(reason="US-05: weekly progress chart is not implemented yet")
def test_us05_view_weekly_progress(client):
    """AC: The weekly summary endpoint returns completion counts per day."""
    # Arrange
    from extensions import db
    from models import Habit, HabitCompletion

    habit = Habit(name="Meditate", description="10 min mindfulness")
    db.session.add(habit)
    db.session.commit()

    db.session.add(HabitCompletion(habit_id=habit.id, date="2026-09-28"))
    db.session.add(HabitCompletion(habit_id=habit.id, date="2026-09-30"))
    db.session.commit()

    # Act
    response = client.get(f"/habit-tracker/{habit.id}/weekly-summary")

    # Assert
    assert response.status_code == 200
    data = response.get_json()
    assert data["total_completions"] == 2
    assert "2026-09-28" in data["completed_dates"]

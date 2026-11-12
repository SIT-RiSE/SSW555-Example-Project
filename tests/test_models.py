from extensions import db
from models import Habit

# === Habit Model Tests ===


def test_habit_create_and_persist(app):
    """Test that Habit model can be created and persisted to the database."""
    # Arrange
    habit = Habit(name="Exercise", description="Morning routine")

    # Act
    db.session.add(habit)
    db.session.commit()

    # Assert
    stored = Habit.query.first()
    assert stored is not None
    assert stored.name == "Exercise"
    assert stored.description == "Morning routine"


def test_habit_allows_optional_description(app):
    """Test that Habit model allows description to be None."""
    # Arrange
    habit = Habit(name="Meditate", description=None)

    # Act
    db.session.add(habit)
    db.session.commit()

    # Assert
    stored = Habit.query.first()
    assert stored is not None
    assert stored.description is None

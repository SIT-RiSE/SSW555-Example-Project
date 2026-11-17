from extensions import db
from models import Category, Habit


def test_category_selected_during_creation_is_saved_and_displayed(client):
    category = Category(name='Fitness')
    db.session.add(category)
    db.session.commit()

    response = client.post(
        '/habit-tracker',
        data={'name': 'Morning run', 'category_id': str(category.id)},
        follow_redirects=True,
    )

    assert response.status_code == 200
    habit = Habit.query.filter_by(name='Morning run').one()
    assert habit.category == category
    assert b'data-testid="habit-category"' in response.data
    assert b'Category: Fitness' in response.data


def test_category_selected_for_existing_habit_is_saved_and_displayed(client):
    category = Category(name='Learning')
    habit = Habit(name='Read a chapter')
    db.session.add_all([category, habit])
    db.session.commit()

    response = client.post(
        f'/habit-tracker/{habit.id}/category',
        data={'category_id': str(category.id)},
        follow_redirects=True,
    )

    assert response.status_code == 200
    db.session.refresh(habit)
    assert habit.category == category
    assert b'data-testid="habit-category"' in response.data
    assert b'Category: Learning' in response.data


def test_uncategorized_habit_does_not_show_category_badge(client):
    db.session.add(Habit(name='Drink water'))
    db.session.commit()

    response = client.get('/habit-tracker')

    assert response.status_code == 200
    assert b'data-testid="habit-category"' not in response.data

"""US-20: Changes to an existing habit are saved and displayed."""

import pytest

from extensions import db
from models import Category, Habit


@pytest.fixture
def habit(app):
    category = Category(name='Learning')
    habit = Habit(name='Read', description='Ten pages', frequency='weekly',
                  category=category, reminder_time='09:00', scheduled_days='Mon,Fri',
                  completed_dates='["2026-11-01"]')
    db.session.add(habit)
    db.session.commit()
    return habit


def test_edit_saves_and_displays_changes_without_losing_history(client, habit):
    habit_id, created_at, category_id = habit.id, habit.created_at, habit.category_id
    response = client.post(f'/habit-tracker/{habit_id}/edit', data={
        'name': '  Evening reading  ', 'description': '  Twenty pages  ',
        'frequency': 'monthly',
    }, follow_redirects=True)
    assert response.status_code == 200
    db.session.remove()
    stored = db.session.get(Habit, habit_id)
    assert (stored.name, stored.description, stored.frequency) == (
        'Evening reading', 'Twenty pages', 'monthly')
    assert stored.created_at == created_at
    assert stored.category_id == category_id
    assert stored.reminder_time == '09:00'
    assert stored.scheduled_days == 'Mon,Fri'
    assert stored.completed_dates == '["2026-11-01"]'
    assert Habit.query.count() == 1
    page = client.get('/habit-tracker').data
    assert b'Evening reading' in page and b'Twenty pages' in page and b'Monthly' in page


def test_edit_form_contains_current_description_and_frequency(client, habit):
    page = client.get('/habit-tracker').data
    assert f'id="habit-description-{habit.id}" name="description"'.encode() in page
    assert b'>Ten pages</textarea>' in page
    assert b'value="weekly" selected' in page
    assert b'Save changes' in page


def test_description_can_be_cleared_and_omitted_frequency_is_preserved(client, habit):
    client.post(f'/habit-tracker/{habit.id}/edit', data={'name': 'Read', 'description': '  '})
    db.session.refresh(habit)
    assert habit.description is None
    assert habit.frequency == 'weekly'


@pytest.mark.parametrize('data', [
    {'name': ''}, {'name': '   '}, {'name': 'x' * 101},
    {'name': 'Changed', 'description': 'Changed', 'frequency': 'hourly'},
])
def test_invalid_edits_leave_saved_information_unchanged(client, habit, data):
    assert client.post(f'/habit-tracker/{habit.id}/edit', data=data).status_code == 400
    db.session.remove()
    stored = db.session.get(Habit, habit.id)
    assert (stored.name, stored.description, stored.frequency) == ('Read', 'Ten pages', 'weekly')


def test_edit_missing_habit_returns_404(client):
    assert client.post('/habit-tracker/9999/edit', data={'name': 'Read'}).status_code == 404

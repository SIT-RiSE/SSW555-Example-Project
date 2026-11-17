"""A habit is removed only after explicit confirmation."""

import pytest

from extensions import db
from models import Category, Habit


@pytest.fixture
def habits(app):
    category = Category(name='Wellness')
    target = Habit(name='Old goal', category=category, reminder_time='09:00',
                   paused_reminder_time='08:00', completed_dates='["2026-11-02"]')
    other = Habit(name='Keep this goal', category=category,
                  reminder_time='10:00', completed_dates='["2026-11-03"]')
    db.session.add_all([target, other])
    db.session.commit()
    return target.id, other.id, category.id


def test_confirmed_delete_removes_habit_from_all_views(client, habits):
    target_id, other_id, category_id = habits
    response = client.post(f'/habit-tracker/{target_id}/delete',
                           data={'confirm': 'delete'}, follow_redirects=True)
    assert response.status_code == 200
    assert b'Old goal' not in response.data
    assert b'Keep this goal' in response.data
    db.session.remove()
    assert db.session.get(Habit, target_id) is None
    other = db.session.get(Habit, other_id)
    assert other.completed_dates == '["2026-11-03"]'
    assert other.reminder_time == '10:00'
    assert db.session.get(Category, category_id) is not None
    assert client.get(f'/habit-tracker/habits/{target_id}').status_code == 404
    assert client.get(f'/habit-tracker/habits/{target_id}/history').status_code == 404
    assert [habit['id'] for habit in client.get('/habit-tracker/habits').get_json()['habits']] == [other_id]
    assert b'Old goal' not in client.get('/habit-tracker?view=today').data
    assert client.post(f'/habit-tracker/{target_id}/reminder/on').status_code == 404


def test_confirmation_page_and_cancel_preserve_habit(client, habits):
    target_id, _, _ = habits
    path = f'/habit-tracker/{target_id}/delete'
    assert path.encode() in client.get('/habit-tracker').data
    page = client.get(path)
    assert page.status_code == 200
    assert b'Delete Old goal?' in page.data
    assert b'completion history' in page.data and b'paused reminder' in page.data
    assert b'name="confirm" value="delete"' in page.data
    assert b'href="/habit-tracker"' in page.data and b'Cancel' in page.data
    client.get('/habit-tracker')  # Follow Cancel without submitting deletion.
    db.session.remove()
    stored = db.session.get(Habit, target_id)
    assert stored.completed_dates == '["2026-11-02"]'
    assert stored.reminder_time == '09:00'
    assert stored.paused_reminder_time == '08:00'


@pytest.mark.parametrize('data', [{}, {'confirm': 'cancel'}, {'confirm': ''}])
def test_unconfirmed_post_does_not_delete(client, habits, data):
    target_id, _, _ = habits
    assert client.post(f'/habit-tracker/{target_id}/delete', data=data).status_code == 400
    db.session.remove()
    assert db.session.get(Habit, target_id) is not None


def test_missing_or_already_deleted_habit_returns_404(client, habits):
    target_id, _, _ = habits
    path = f'/habit-tracker/{target_id}/delete'
    assert client.post(path, data={'confirm': 'delete'}).status_code == 302
    assert client.get(path).status_code == 404
    assert client.post(path, data={'confirm': 'delete'}).status_code == 404

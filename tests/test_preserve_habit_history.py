"""Habit detail edits preserve recorded progress, including legacy history."""

from datetime import date

import pytest

from extensions import db
from models import Category, Habit


@pytest.fixture(params=[
    '["2026-11-02", "2026-11-04", "2026-11-06"]',
    '2026-11-02,2026-11-04,2026-11-06',
])
def recorded_habit(app, request):
    habit = Habit(name='Read', scheduled_days='Mon,Wed,Fri',
                  reminder_time='09:00', completed_dates=request.param)
    db.session.add_all([habit, Category(name='Learning')])
    db.session.commit()
    return habit


@pytest.mark.parametrize('edit', ['name', 'frequency', 'schedule', 'category', 'reminder'])
def test_each_edit_preserves_stored_and_available_history(client, recorded_habit, edit):
    habit_id = recorded_habit.id
    original_history = recorded_habit.completed_dates
    created_at = recorded_habit.created_at
    category_id = Category.query.one().id
    route, payload, field, expected = {
        'name': ('edit', {'name': 'Evening reading'}, 'name', 'Evening reading'),
        'frequency': ('edit', {'name': 'Read', 'frequency': 'weekly'}, 'frequency', 'weekly'),
        'schedule': ('schedule', {'days': ['Tue', 'Thu']}, 'scheduled_days', 'Tue,Thu'),
        'category': ('category', {'category_id': str(category_id)}, 'category_id', category_id),
        'reminder': ('reminder', {'reminder_time': '20:30'}, 'reminder_time', '20:30'),
    }[edit]

    response = client.post(f'/habit-tracker/{habit_id}/{route}', data=payload)

    assert response.status_code == 302
    db.session.remove()
    stored = db.session.get(Habit, habit_id)
    assert getattr(stored, field) == expected
    assert stored.completed_dates == original_history
    assert stored.created_at == created_at
    assert Habit.query.count() == 1
    history = client.get(f'/habit-tracker/habits/{habit_id}/history')
    assert history.status_code == 200
    assert history.get_json()['completions'] == ['2026-11-06', '2026-11-04', '2026-11-02']
    assert history.get_json()['total_completions'] == 3


def test_schedule_change_keeps_old_days_and_subsequent_progress(client, recorded_habit):
    habit_id = recorded_habit.id
    # The old Monday/Wednesday/Friday completions are outside the new schedule.
    assert client.post(f'/habit-tracker/{habit_id}/schedule',
                       data={'days': ['Tue', 'Thu']}).status_code == 302
    assert client.post(f'/habit-tracker/{habit_id}/check-in',
                       data={'completed_on': '2026-11-10'}).status_code == 302
    db.session.remove()
    stored = db.session.get(Habit, habit_id)
    assert stored.completion_history() == [
        date(2026, 11, 10), date(2026, 11, 6), date(2026, 11, 4), date(2026, 11, 2),
    ]
    filtered = client.get(f'/habit-tracker/habits/{habit_id}/history', query_string={
        'start': '2026-11-02', 'end': '2026-11-06',
    }).get_json()
    assert filtered['completions'] == ['2026-11-06', '2026-11-04', '2026-11-02']
    page = client.get('/habit-tracker')
    assert b'Nov 06' in page.data and b'Nov 10' in page.data

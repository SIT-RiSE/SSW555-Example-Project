"""US-12: the Today dashboard shows only habits due on the current weekday."""

from datetime import date, timedelta
from html import unescape

import pytest

import app as app_module
from extensions import db
from models import WEEKDAYS, Habit


def set_today(monkeypatch, day):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return day

    monkeypatch.setattr(app_module, 'date', FixedDate)


@pytest.mark.parametrize('weekday', range(7))
def test_today_filters_each_weekday_and_preserves_all_habits(client, monkeypatch, weekday):
    today = date(2026, 11, 2) + timedelta(days=weekday)
    set_today(monkeypatch, today)
    for day in WEEKDAYS:
        db.session.add(Habit(name=f'Only-{day}-habit', scheduled_days=day))
    db.session.add(Habit(name='Unscheduled daily habit'))
    db.session.add(Habit(name='Multi-day habit', scheduled_days='Mon,Wed,Fri'))
    db.session.commit()

    response = client.get('/habit-tracker?view=today')

    assert response.status_code == 200
    assert "Today's habits" in unescape(response.get_data(as_text=True))
    assert today.strftime('%A, %B %d, %Y').encode() in response.data
    assert b'Unscheduled daily habit' in response.data
    for day in WEEKDAYS:
        assert (f'Only-{day}-habit'.encode() in response.data) == (day == WEEKDAYS[weekday])
    assert (b'Multi-day habit' in response.data) == (weekday in (0, 2, 4))
    all_habits = client.get('/habit-tracker?view=all')
    for day in WEEKDAYS:
        assert f'Only-{day}-habit'.encode() in all_habits.data
    assert Habit.query.count() == 9


def test_today_has_empty_state_when_no_habits_are_due(client, monkeypatch):
    set_today(monkeypatch, date(2026, 11, 3))
    db.session.add(Habit(name='Monday run', scheduled_days='Mon'))
    db.session.commit()

    response = client.get('/habit-tracker?view=today')

    assert b'No habits due today' in response.data
    assert b'Monday run' not in response.data
    assert b'view=all' in response.data
    assert b'No habits yet' not in response.data


def test_today_works_without_any_habits(client):
    response = client.get('/habit-tracker?view=today')
    assert response.status_code == 200
    assert b'No habits due today' in response.data


def test_today_recalculates_after_day_rollover(client, monkeypatch):
    db.session.add_all([
        Habit(name='Monday run', scheduled_days='Mon'),
        Habit(name='Tuesday swim', scheduled_days='Tue'),
    ])
    db.session.commit()
    set_today(monkeypatch, date(2026, 11, 2))
    monday = client.get('/habit-tracker?view=today')
    set_today(monkeypatch, date(2026, 11, 3))
    tuesday = client.get('/habit-tracker?view=today')

    assert b'Monday run' in monday.data and b'Tuesday swim' not in monday.data
    assert b'Tuesday swim' in tuesday.data and b'Monday run' not in tuesday.data


def test_today_uses_latest_saved_schedule(client, monkeypatch):
    set_today(monkeypatch, date(2026, 11, 3))
    habit = Habit(name='Read on Tuesday', scheduled_days='Mon')
    db.session.add(habit)
    db.session.commit()
    assert b'Read on Tuesday' not in client.get('/habit-tracker?view=today').data

    client.post(f'/habit-tracker/{habit.id}/schedule', data={'days': ['Tue']})

    assert b'Read on Tuesday' in client.get('/habit-tracker?view=today').data


def test_invalid_view_is_rejected(client):
    assert client.get('/habit-tracker?view=unknown').status_code == 400

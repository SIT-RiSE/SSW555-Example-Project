"""US-08: a due habit's completion is saved for the current day."""

import json
from datetime import date

import pytest

import app as app_module
import models as models_module
from extensions import db
from models import Habit


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 11, 3)  # Tuesday

    monkeypatch.setattr(app_module, 'date', FixedDate)
    monkeypatch.setattr(models_module, 'date', FixedDate)


def test_completion_is_persisted_for_today_and_shown_after_reload(client):
    habit = Habit(name='Drink water', scheduled_days='Tue,Thu')
    db.session.add(habit)
    db.session.commit()
    habit_id = habit.id

    page = client.get('/habit-tracker')
    assert f'/habit-tracker/{habit_id}/complete'.encode() in page.data
    response = client.post(f'/habit-tracker/{habit_id}/complete', follow_redirects=True)

    assert response.status_code == 200
    assert b'Completed today' in response.data
    db.session.remove()
    stored = db.session.get(Habit, habit_id)
    assert json.loads(stored.completed_dates) == ['2026-11-03']
    assert stored.completed_today is True
    page = client.get('/habit-tracker')
    assert b'Completed today' in page.data
    assert f'/habit-tracker/{habit_id}/complete'.encode() not in page.data


def test_completion_preserves_history_and_records_today_once(client):
    habit = Habit(name='Read', completed_dates='["2026-11-02"]')
    db.session.add(habit)
    db.session.commit()
    habit_id = habit.id

    for _ in range(2):
        assert client.post(f'/habit-tracker/{habit_id}/complete').status_code == 302

    db.session.remove()
    assert json.loads(db.session.get(Habit, habit_id).completed_dates) == [
        '2026-11-02', '2026-11-03',
    ]


def test_habit_not_scheduled_today_cannot_be_completed(client):
    habit = Habit(name='Monday run', scheduled_days='Mon', completed_dates='["2026-11-02"]')
    db.session.add(habit)
    db.session.commit()

    page = client.get('/habit-tracker')
    assert b'Not scheduled for today' in page.data
    assert f'/habit-tracker/{habit.id}/complete'.encode() not in page.data
    response = client.post(f'/habit-tracker/{habit.id}/complete')

    assert response.status_code == 400
    assert json.loads(db.session.get(Habit, habit.id).completed_dates) == ['2026-11-02']


def test_completion_uses_server_today_instead_of_submitted_date(client):
    habit = Habit(name='Journal')
    db.session.add(habit)
    db.session.commit()

    response = client.post(f'/habit-tracker/{habit.id}/complete', data={'date': '2030-01-01'})

    assert response.status_code == 302
    assert json.loads(db.session.get(Habit, habit.id).completed_dates) == ['2026-11-03']


def test_missing_habit_cannot_be_completed(client):
    assert client.post('/habit-tracker/99999/complete').status_code == 404


def test_get_does_not_record_a_completion(client):
    habit = Habit(name='Stretch')
    db.session.add(habit)
    db.session.commit()

    assert client.get(f'/habit-tracker/{habit.id}/complete').status_code == 405
    assert db.session.get(Habit, habit.id).completed_dates is None


def test_yesterday_completion_does_not_hide_today_button(client):
    habit = Habit(name='Meditate', completed_dates='["2026-11-02"]')
    db.session.add(habit)
    db.session.commit()

    page = client.get('/habit-tracker')
    assert f'/habit-tracker/{habit.id}/complete'.encode() in page.data
    assert b'Completed today' not in page.data


@pytest.mark.parametrize('history, expected_previous', [
    ('2026-11-02', ['2026-11-02']),
    ('2026-11-01, 2026-11-02', ['2026-11-01', '2026-11-02']),
])
def test_legacy_history_can_be_viewed_and_extended(client, history, expected_previous):
    habit = Habit(name='Legacy habit', completed_dates=history)
    db.session.add(habit)
    db.session.commit()
    habit_id = habit.id

    assert client.get('/habit-tracker').status_code == 200
    assert db.session.get(Habit, habit_id).completed_dates == history
    assert client.post(f'/habit-tracker/{habit_id}/complete').status_code == 302
    db.session.remove()
    assert json.loads(db.session.get(Habit, habit_id).completed_dates) == [
        *expected_previous, '2026-11-03',
    ]


def test_legacy_completion_today_is_shown_without_rewriting_history(client):
    habit = Habit(name='Already completed', completed_dates='2026-11-02,2026-11-03')
    db.session.add(habit)
    db.session.commit()

    assert b'Completed today' in client.get('/habit-tracker').data
    client.post(f'/habit-tracker/{habit.id}/complete')
    assert db.session.get(Habit, habit.id).completed_dates == '2026-11-02,2026-11-03'

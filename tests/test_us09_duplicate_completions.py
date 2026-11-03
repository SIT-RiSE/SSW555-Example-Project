import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from threading import Barrier

import pytest

from extensions import db
from models import Habit


def create_habit(name='Read', completed_dates=None):
    habit = Habit(name=name, completed_dates=completed_dates)
    db.session.add(habit)
    db.session.commit()
    return habit.id


def test_repeated_completion_only_records_today_once(client):
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    habit_id = create_habit(completed_dates=json.dumps([yesterday]))
    path = f'/habit-tracker/{habit_id}/complete'
    for _ in range(3):
        assert client.post(path).status_code == 302
    db.session.remove()
    assert json.loads(db.session.get(Habit, habit_id).completed_dates) == [
        yesterday, date.today().isoformat(),
    ]
    page = client.get('/habit-tracker').data
    assert b'Completed today' in page
    assert b'disabled' in page


def test_each_habit_can_be_completed_on_multiple_days(app):
    ids = [create_habit('Read'), create_habit('Walk', '[]')]
    today = date.today()
    tomorrow = today + timedelta(days=1)
    for habit_id in ids:
        habit = db.session.get(Habit, habit_id)
        assert habit.mark_complete(today) is True
        assert habit.mark_complete(tomorrow) is True
        assert habit.mark_complete(today) is False
        assert json.loads(habit.completed_dates) == [today.isoformat(), tomorrow.isoformat()]


def test_missing_habit_returns_404(client):
    assert client.post('/habit-tracker/9999/complete').status_code == 404
    assert Habit.query.count() == 0


def test_uncompleted_habit_shows_completion_button(client):
    create_habit()
    assert b'Mark complete' in client.get('/habit-tracker').data


@pytest.mark.parametrize("day_offset", [0, 1])
def test_simultaneous_requests_preserve_unique_days(app, day_offset):
    habit_id = create_habit()
    barrier = Barrier(2)

    def complete(offset):
        with app.app_context():
            habit = db.session.get(Habit, habit_id)
            barrier.wait(timeout=5)
            return habit.mark_complete(date.today() + timedelta(days=offset))

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(complete, [0, day_offset]))
    assert sorted(results) == ([False, True] if day_offset == 0 else [True, True])
    db.session.remove()
    dates = json.loads(db.session.get(Habit, habit_id).completed_dates)
    assert len(dates) == len(set(dates)) == (1 if day_offset == 0 else 2)
    assert set(dates) == {
        date.today().isoformat(),
        (date.today() + timedelta(days=day_offset)).isoformat(),
    }

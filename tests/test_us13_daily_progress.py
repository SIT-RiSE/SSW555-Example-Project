"""
US-13: View Daily Progress

As a user, I want to see my daily progress so that I know how much of my
routine I have completed.
"""

import json
from datetime import date, timedelta

from extensions import db
from models import WEEKDAYS, Habit, daily_progress

TODAY = date(2026, 11, 2)  # a Monday
YESTERDAY = TODAY - timedelta(days=1)


def test_us13_progress_counts_completed_habits_due_today():
    """AC: Daily progress reflects how many of today's habits are completed."""
    habits = [
        Habit(name='Read', completed_dates=TODAY.isoformat()),
        Habit(name='Run', scheduled_days='Mon,Wed', completed_dates=TODAY.isoformat()),
        Habit(name='Stretch'),
    ]

    assert daily_progress(habits, TODAY) == {'done': 2, 'total': 3, 'percent': 67}


def test_us13_habits_not_scheduled_today_are_excluded():
    """Matches the Today view: unscheduled habits count every day, scheduled ones on their days."""
    habits = [
        Habit(name='Read'),
        Habit(name='Swim', scheduled_days='Tue,Thu', completed_dates=TODAY.isoformat()),
        Habit(name='Review budget', frequency='weekly'),
    ]

    assert daily_progress(habits, TODAY) == {'done': 0, 'total': 2, 'percent': 0}


def test_us13_reads_completions_saved_by_mark_complete():
    habits = [Habit(name='Read', completed_dates=json.dumps([TODAY.isoformat()]))]

    assert daily_progress(habits, TODAY) == {'done': 1, 'total': 1, 'percent': 100}


def test_us13_earlier_completions_do_not_count_for_today():
    habits = [Habit(name='Read', completed_dates=YESTERDAY.isoformat())]

    assert daily_progress(habits, TODAY) == {'done': 0, 'total': 1, 'percent': 0}


def test_us13_no_habits_due_gives_zero_progress():
    assert daily_progress([], TODAY) == {'done': 0, 'total': 0, 'percent': 0}


def test_us13_progress_updates_on_page_when_a_habit_is_completed(client):
    """AC: Completing habits updates the displayed daily progress."""
    read = Habit(name='Read')
    write = Habit(name='Write')
    db.session.add_all([read, write])
    db.session.commit()

    before = client.get('/habit-tracker').data.decode()
    client.post(f'/habit-tracker/{read.id}/complete')
    after = client.get('/habit-tracker').data.decode()

    assert '0 of 2 habits done · 0%' in before
    assert '1 of 2 habits done · 50%' in after
    assert after.count('Completed today') == 1


def test_us13_page_shows_message_when_nothing_is_scheduled_today(client):
    tomorrow = WEEKDAYS[(date.today().weekday() + 1) % 7]
    db.session.add(Habit(name='Run', scheduled_days=tomorrow))
    db.session.commit()

    page = client.get('/habit-tracker').data.decode()

    assert 'No habits are scheduled for today.' in page

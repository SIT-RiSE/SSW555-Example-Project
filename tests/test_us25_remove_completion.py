"""
US-25: Remove an Incorrect Completion

As a user, I want to remove a completion that I entered by mistake so that my
progress stays accurate.
"""

import json
from datetime import date, timedelta

from extensions import db
from models import Habit

TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)
TWO_DAYS_AGO = TODAY - timedelta(days=2)


def add_habit(dates=(), **fields):
    habit = Habit(name='Read', completed_dates=json.dumps([d.isoformat() for d in dates]),
                  **fields)
    db.session.add(habit)
    db.session.commit()
    return habit


def remove(client, habit_id, day, **extra):
    value = day.isoformat() if isinstance(day, date) else day
    return client.post(f'/habit-tracker/{habit_id}/completions/remove',
                       data={'completed_on': value, **extra})


def stored_dates(habit_id):
    return set(db.session.get(Habit, habit_id).completed_dates_list)


def test_us25_removing_a_completion_makes_the_day_incomplete_and_recalculates_streak(client):
    """AC: The removed date becomes incomplete and the streak recalculates."""
    habit = add_habit([TWO_DAYS_AGO, YESTERDAY, TODAY])
    assert habit.current_streak() == 3

    response = remove(client, habit.id, YESTERDAY)

    assert response.status_code == 302
    assert stored_dates(habit.id) == {TWO_DAYS_AGO, TODAY}
    assert db.session.get(Habit, habit.id).current_streak() == 1


def test_us25_removing_todays_completion_reopens_mark_complete(client):
    habit = add_habit([TODAY])

    remove(client, habit.id, TODAY)
    page = client.get('/habit-tracker').data.decode()

    assert not db.session.get(Habit, habit.id).completed_today
    assert 'Mark complete' in page
    assert 'Completed today' not in page


def test_us25_other_completions_are_kept(client):
    habit = add_habit([TWO_DAYS_AGO, YESTERDAY])

    remove(client, habit.id, TWO_DAYS_AGO)

    assert stored_dates(habit.id) == {YESTERDAY}


def test_us25_works_with_legacy_comma_separated_history(client):
    habit = Habit(name='Read', completed_dates=f'{TWO_DAYS_AGO},{YESTERDAY}')
    db.session.add(habit)
    db.session.commit()

    assert remove(client, habit.id, TWO_DAYS_AGO).status_code == 302
    assert stored_dates(habit.id) == {YESTERDAY}


def test_us25_removing_a_date_that_is_not_complete_is_rejected(client):
    habit = add_habit([YESTERDAY])

    assert remove(client, habit.id, TWO_DAYS_AGO).status_code == 400
    assert stored_dates(habit.id) == {YESTERDAY}


def test_us25_invalid_date_and_missing_habit_are_rejected(client):
    habit = add_habit([YESTERDAY])

    assert remove(client, habit.id, 'not-a-date').status_code == 400
    assert remove(client, habit.id, '').status_code == 400
    assert remove(client, 9999, YESTERDAY).status_code == 404
    assert stored_dates(habit.id) == {YESTERDAY}


def test_us25_removed_date_disappears_from_page_history(client):
    habit = add_habit([YESTERDAY])
    before = client.get('/habit-tracker').data.decode()

    remove(client, habit.id, YESTERDAY)
    after = client.get('/habit-tracker').data.decode()

    assert 'Remove a completion' in before
    assert YESTERDAY.isoformat() in before
    assert 'Remove a completion' not in after
    assert 'Recent check-ins' not in after


def test_us25_returns_to_today_view_when_removed_from_it(client):
    habit = add_habit([TODAY])

    response = remove(client, habit.id, TODAY, view='today')

    assert response.headers['Location'].endswith('/habit-tracker?view=today')

"""
US-10: Back-Fill a Missed Check-In

As a user, I want to record a past habit completion that I forgot to enter so
that my history matches what I actually completed.
"""

import json
from datetime import date, timedelta

from extensions import db
from models import WEEKDAYS, Habit


def add_habit(**fields):
    habit = Habit(name='Read', **fields)
    db.session.add(habit)
    db.session.commit()
    return habit


def check_in(client, habit_id, day):
    value = day.isoformat() if isinstance(day, date) else day
    return client.post(f'/habit-tracker/{habit_id}/check-in', data={'completed_on': value})


def test_us10_backfilling_a_missed_day_updates_history_and_streak(client):
    """AC: Marking a past incomplete day as complete recalculates history and streak."""
    today = date.today()
    two_days_ago = today - timedelta(days=2)
    habit = add_habit(completed_dates=two_days_ago.isoformat())
    assert habit.current_streak() == 0  # yesterday was missed

    response = check_in(client, habit.id, today - timedelta(days=1))

    assert response.status_code == 302
    stored = db.session.get(Habit, habit.id)
    assert set(stored.completed_dates_list) == {two_days_ago, today - timedelta(days=1)}
    assert stored.current_streak() == 2


def test_us10_backfill_is_shown_in_history_and_streak_on_page(client):
    today = date.today()
    habit = add_habit()

    check_in(client, habit.id, today - timedelta(days=1))
    page = client.get('/habit-tracker').data.decode()

    assert 'Recent check-ins: ' + (today - timedelta(days=1)).strftime('%b %d') in page
    assert '1 day streak' in page


def test_us10_backfilling_the_same_day_twice_records_it_once(client):
    today = date.today()
    habit = add_habit()

    check_in(client, habit.id, today - timedelta(days=3))
    check_in(client, habit.id, today - timedelta(days=3))

    stored = db.session.get(Habit, habit.id)
    assert json.loads(stored.completed_dates) == [(today - timedelta(days=3)).isoformat()]


def test_us10_backfill_works_with_legacy_comma_separated_history(client):
    today = date.today()
    habit = add_habit(completed_dates=(today - timedelta(days=2)).isoformat())

    check_in(client, habit.id, today - timedelta(days=1))

    stored = db.session.get(Habit, habit.id)
    assert set(stored.completed_dates_list) == {today - timedelta(days=2), today - timedelta(days=1)}


def test_us10_backfill_and_mark_complete_share_one_history(client):
    """Back-filled days and today's Mark complete feed the same streak."""
    today = date.today()
    habit = add_habit()

    check_in(client, habit.id, today - timedelta(days=1))
    client.post(f'/habit-tracker/{habit.id}/complete')

    stored = db.session.get(Habit, habit.id)
    assert set(stored.completed_dates_list) == {today - timedelta(days=1), today}
    assert stored.current_streak() == 2


def test_us10_future_dates_are_rejected(client):
    habit = add_habit()

    response = check_in(client, habit.id, date.today() + timedelta(days=1))

    assert response.status_code == 400
    assert db.session.get(Habit, habit.id).completed_dates is None


def test_us10_unscheduled_days_are_rejected(client):
    yesterday = date.today() - timedelta(days=1)
    other_days = [day for day in WEEKDAYS if day != WEEKDAYS[yesterday.weekday()]]
    habit = add_habit(scheduled_days=','.join(other_days))

    response = check_in(client, habit.id, yesterday)

    assert response.status_code == 400
    assert db.session.get(Habit, habit.id).completed_dates is None


def test_us10_scheduled_past_day_is_accepted(client):
    yesterday = date.today() - timedelta(days=1)
    habit = add_habit(scheduled_days=WEEKDAYS[yesterday.weekday()])

    assert check_in(client, habit.id, yesterday).status_code == 302
    assert set(db.session.get(Habit, habit.id).completed_dates_list) == {yesterday}


def test_us10_invalid_date_and_missing_habit_are_rejected(client):
    habit = add_habit()

    assert check_in(client, habit.id, 'not-a-date').status_code == 400
    assert check_in(client, habit.id, '').status_code == 400
    assert check_in(client, 9999, date.today()).status_code == 404


def test_us10_backfill_counts_toward_grace_day_streak(client):
    """A back-filled day also feeds the US-07 grace-day streak."""
    today = date.today()
    habit = add_habit(grace_day_enabled=True)

    check_in(client, habit.id, today - timedelta(days=1))

    assert db.session.get(Habit, habit.id).current_streak() == 1

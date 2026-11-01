from datetime import date, timedelta

import pytest

from extensions import db
from models import Habit


def test_streak_counts_consecutive_scheduled_days_across_calendar_gaps():
    habit = Habit(
        name='Run',
        scheduled_days='Mon,Wed,Fri',
        completed_dates='2026-10-30,2026-11-02,2026-11-04',
    )

    assert habit.calculate_current_streak(as_of=date(2026, 11, 4)) == 3


def test_streak_resets_when_the_latest_finished_scheduled_day_was_missed():
    habit = Habit(
        name='Run',
        scheduled_days='Mon,Wed,Fri',
        completed_dates='2026-10-28,2026-10-30,2026-11-02',
    )

    assert habit.calculate_current_streak(as_of=date(2026, 11, 6)) == 0


def test_streak_is_not_lost_before_todays_scheduled_completion_is_due():
    habit = Habit(
        name='Run',
        scheduled_days='Mon,Wed,Fri',
        completed_dates='2026-10-30,2026-11-02',
    )

    assert habit.calculate_current_streak(as_of=date(2026, 11, 4)) == 2


def test_completions_on_unscheduled_days_do_not_inflate_the_streak():
    habit = Habit(
        name='Run',
        scheduled_days='Mon,Wed,Fri',
        completed_dates='2026-10-30,2026-10-31,2026-11-02',
    )

    assert habit.calculate_current_streak(as_of=date(2026, 11, 3)) == 2


def test_daily_streak_counts_consecutive_calendar_days_without_a_schedule():
    habit = Habit(
        name='Read',
        frequency='daily',
        completed_dates='2026-11-03,2026-11-04,2026-11-05',
    )

    assert habit.calculate_current_streak(as_of=date(2026, 11, 5)) == 3


@pytest.mark.parametrize(
    ('frequency', 'completed_dates', 'as_of'),
    [
        ('weekly', '2026-03-02,2026-03-10,2026-03-18', date(2026, 3, 18)),
        ('monthly', '2026-01-05,2026-02-27,2026-03-01', date(2026, 3, 15)),
    ],
)
def test_streak_groups_unscheduled_completions_by_frequency(
    frequency, completed_dates, as_of
):
    habit = Habit(name='Practice', frequency=frequency, completed_dates=completed_dates)

    assert habit.calculate_current_streak(as_of=as_of) == 3


@pytest.mark.parametrize(
    ('frequency', 'completed_dates', 'as_of'),
    [
        ('weekly', '2026-03-02,2026-03-10', date(2026, 3, 18)),
        ('monthly', '2026-01-05,2026-02-27', date(2026, 3, 15)),
    ],
)
def test_streak_remains_current_during_an_unfinished_frequency_period(
    frequency, completed_dates, as_of
):
    habit = Habit(name='Practice', frequency=frequency, completed_dates=completed_dates)

    assert habit.calculate_current_streak(as_of=as_of) == 2


def test_streak_ignores_duplicate_malformed_and_future_completion_dates():
    habit = Habit(
        name='Read',
        completed_dates='bad-date,2026-11-04,2026-11-04,2026-11-05,2027-01-01',
    )

    assert habit.calculate_current_streak(as_of=date(2026, 11, 5)) == 2


def test_habit_without_completion_history_has_zero_streak():
    assert Habit(name='Read').calculate_current_streak(as_of=date(2026, 11, 5)) == 0


def test_current_streak_is_displayed_on_the_habit_card(client):
    today = date.today()
    completed_dates = f'{(today - timedelta(days=1)).isoformat()},{today.isoformat()}'
    db.session.add(Habit(name='Read', completed_dates=completed_dates))
    db.session.commit()

    response = client.get('/habit-tracker')

    assert response.status_code == 200
    assert b'data-testid="habit-current-streak"' in response.data
    assert b'2 day streak' in response.data

"""
US-07: Add a Weekly Grace Day
Owner: Aryan Gupta

As a student with a busy schedule, I want one grace day per week so that
missing a single day doesn't reset my habit streak.
"""

from datetime import date

from extensions import db
from models import Habit, calculate_streak

# 2026-11-02 is a Monday, so Nov 2-8 is one Monday-to-Sunday week.
THURSDAY = date(2026, 11, 5)


def days(*day_numbers, month=11):
    return [date(2026, month, d) for d in day_numbers]


def make_habit(**fields):
    habit = Habit(name="Drink water", **fields)
    db.session.add(habit)
    db.session.commit()
    return habit


def test_us07_grace_day_can_be_turned_on(client):
    """AC: I can turn on a weekly grace day for a habit."""
    habit = make_habit()

    response = client.post(f"/habit-tracker/{habit.id}/grace-day", data={"enabled": "on"})

    assert response.status_code == 302
    assert db.session.get(Habit, habit.id).grace_day_enabled is True


def test_us07_grace_day_can_be_turned_off(client):
    """AC: Unchecking the box turns the grace day back off."""
    habit = make_habit(grace_day_enabled=True)

    client.post(f"/habit-tracker/{habit.id}/grace-day", data={})

    assert db.session.get(Habit, habit.id).grace_day_enabled is False


def test_us07_grace_day_for_missing_habit_returns_404(client):
    response = client.post("/habit-tracker/999/grace-day", data={"enabled": "on"})
    assert response.status_code == 404


def test_us07_new_habits_have_grace_day_off_by_default(client):
    client.post("/habit-tracker", data={"name": "Read"})
    assert Habit.query.filter_by(name="Read").first().grace_day_enabled is False


def test_us07_one_missed_day_keeps_streak_with_grace_day():
    """AC: Missing one day in a week does not break the streak."""
    completed = days(2, 3, 5)  # missed Wednesday Nov 4

    assert calculate_streak(completed, THURSDAY, grace_day=False) == 1
    assert calculate_streak(completed, THURSDAY, grace_day=True) == 3


def test_us07_second_missed_day_in_same_week_breaks_streak():
    """AC: Only one grace day is allowed per week."""
    completed = days(2, 5)  # missed both Tuesday and Wednesday

    assert calculate_streak(completed, THURSDAY, grace_day=True) == 1


def test_us07_grace_day_resets_each_week():
    """AC: A new grace day is available every Monday."""
    completed = days(29, 30, month=10) + days(1, 2, 4, 5)  # missed Sat Oct 31 and Tue Nov 3

    assert calculate_streak(completed, THURSDAY, grace_day=False) == 2
    assert calculate_streak(completed, THURSDAY, grace_day=True) == 6


def test_us07_not_completing_today_yet_does_not_break_streak():
    completed = days(2, 3, 4, 5)

    assert calculate_streak(completed, date(2026, 11, 6), grace_day=False) == 4


def test_us07_habit_streak_uses_its_grace_day_setting(client):
    habit = make_habit(completed_dates="2026-11-02,2026-11-03,2026-11-05")

    assert habit.current_streak(today=THURSDAY) == 1
    habit.grace_day_enabled = True
    assert habit.current_streak(today=THURSDAY) == 3


def test_unscheduled_days_do_not_consume_grace():
    completed = days(2, 6)
    assert calculate_streak(completed, date(2026, 11, 6), grace_day=True,
                            scheduled_days=['Mon', 'Wed', 'Fri']) == 2
    assert calculate_streak(completed, date(2026, 11, 6), grace_day=False,
                            scheduled_days=['Mon', 'Wed', 'Fri']) == 1


def test_grace_marks_first_miss_and_second_miss_resets_streak(client):
    habit = make_habit(completed_dates='2026-11-02,2026-11-05', grace_day_enabled=True)
    streak, grace_dates = habit.streak_status(THURSDAY)
    assert streak == 1
    assert grace_dates == days(3)
    assert habit.completed_dates == '2026-11-02,2026-11-05'


def test_future_completions_do_not_start_a_streak():
    assert calculate_streak(days(6), THURSDAY, grace_day=True) == 0


def test_schedule_skips_weekend_without_grace():
    assert calculate_streak(days(6, 9), date(2026, 11, 9),
                            scheduled_days=['Mon', 'Fri']) == 2


def test_dashboard_displays_streak_grace_date_and_toggle(client, monkeypatch):

    class FixedDate(date):
        @classmethod
        def today(cls):
            return THURSDAY

    monkeypatch.setattr('app.date', FixedDate)
    habit = make_habit(completed_dates='2026-11-02,2026-11-05',
                       scheduled_days='Mon,Wed,Thu', grace_day_enabled=True)
    response = client.get('/habit-tracker')
    assert response.status_code == 200
    assert b'2 day streak' in response.data
    assert b'Grace days: 2026-11-04' in response.data
    assert b'name="enabled" checked' in response.data
    client.post(f'/habit-tracker/{habit.id}/grace-day', data={})
    assert b'data-testid="grace-days"' not in client.get('/habit-tracker').data

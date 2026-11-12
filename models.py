import json
from datetime import date, datetime, timedelta

from sqlalchemy import select, update

from extensions import db


def _parse_completion_dates(history):
    """Read JSON history and legacy comma-separated dates without rewriting it."""
    history = history or ''
    try:
        dates = json.loads(history)
    except json.JSONDecodeError:
        dates = None
    if isinstance(dates, list):
        return dates
    return [day.strip() for day in history.split(',') if day.strip()]


class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100, collation='NOCASE'), nullable=False, unique=True)


#: Canonical order used whenever scheduled days are saved or displayed.
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# How often a habit is meant to be completed, mapped to the period used for
# streak and progress calculations.
HABIT_FREQUENCIES = {'daily': 'day', 'weekly': 'week', 'monthly': 'month'}
DEFAULT_FREQUENCY = 'daily'


class Habit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=True)
    category = db.relationship("Category")
    # Stored in 24-hour HH:MM format so it can be used directly by time inputs.
    reminder_time = db.Column(db.String(5), nullable=True)
    frequency = db.Column(db.String(10), nullable=False, default=DEFAULT_FREQUENCY,
                          server_default=DEFAULT_FREQUENCY)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_dates = db.Column(db.Text)
    # Comma-separated subset of WEEKDAYS. Empty/None means no schedule has been set yet.
    scheduled_days = db.Column(db.Text)
    # US-07: when on, one missed day per calendar week (Mon-Sun) does not break
    # the habit's streak.
    grace_day_enabled = db.Column(db.Boolean, nullable=False, default=False,
                                  server_default='0')

    @property
    def scheduled_days_list(self):
        if not self.scheduled_days:
            return []
        return self.scheduled_days.split(",")

    def to_dict(self):
        """US-11: this habit's current details as plain data for the view endpoints."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.name if self.category else None,
            "frequency": self.frequency,
            "reminder_time": self.reminder_time,
            "scheduled_days": self.scheduled_days_list,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @property
    def frequency_period(self):
        """The period a single completion covers, e.g. 'week' for a weekly habit."""
        return HABIT_FREQUENCIES.get(self.frequency or DEFAULT_FREQUENCY, 'day')


    @property
    def completed_today(self):
        return date.today().isoformat() in _parse_completion_dates(self.completed_dates)

    def mark_complete(self, day):
        """Record a day once, retrying if another request changes the history.

        Comparing the stored value in the UPDATE prevents concurrent requests
        from adding duplicates or overwriting another day's completion.
        """
        day_string = day.isoformat()
        while True:
            previous = db.session.execute(
                select(Habit.completed_dates).where(Habit.id == self.id)
            ).scalar_one()
            dates = _parse_completion_dates(previous)
            if day_string in dates:
                return False
            result = db.session.execute(
                update(Habit)
                .where(Habit.id == self.id, Habit.completed_dates == previous)
                .values(completed_dates=json.dumps([*dates, day_string]))
                .execution_options(synchronize_session=False)
            )
            if result.rowcount == 1:
                db.session.commit()
                db.session.expire(self, ['completed_dates'])
                return True
            db.session.rollback()

    @property
    def completed_dates_list(self):
        """Completion dates as date objects (JSON or legacy comma-separated history)."""
        return [date.fromisoformat(value)
                for value in _parse_completion_dates(self.completed_dates)]

    def streak_status(self, today=None):
        """Return the current streak and dates covered by weekly grace."""
        return calculate_streak_status(
            self.completed_dates_list, today or date.today(),
            grace_day=self.grace_day_enabled, scheduled_days=self.scheduled_days_list)

    def current_streak(self, today=None):
        return self.streak_status(today)[0]

    def is_scheduled_on(self, day):
        """True if ``day`` is one of the habit's scheduled weekdays (any day when unscheduled)."""
        scheduled = self.scheduled_days_list
        return not scheduled or WEEKDAYS[day.weekday()] in scheduled

    @property
    def recent_completions(self):
        """The five most recent completion dates, newest first."""
        return sorted(set(self.completed_dates_list), reverse=True)[:5]


def calculate_streak_status(completed_dates, today, grace_day=False, scheduled_days=None):
    """Use one grace day per Mon-Sun week, considering only scheduled days.

    Grace covers the earliest missed scheduled day in each week. Today is not
    missed until it has ended. Grace preserves a streak without increasing it.
    Future completions are ignored and history is never changed.
    """
    scheduled = set(scheduled_days or WEEKDAYS)
    done = {day for day in completed_dates
            if day <= today and WEEKDAYS[day.weekday()] in scheduled}
    if not done:
        return 0, []
    day = min(done)
    streak = 0
    used_weeks = set()
    grace_dates = []
    while day <= today:
        if WEEKDAYS[day.weekday()] in scheduled:
            if day in done:
                streak += 1
            elif day < today:
                week = tuple(day.isocalendar())[:2]
                if grace_day and week not in used_weeks:
                    used_weeks.add(week)
                    grace_dates.append(day)
                else:
                    streak = 0
        day += timedelta(days=1)
    return streak, grace_dates


def calculate_streak(completed_dates, today, grace_day=False, scheduled_days=None):
    """Count completed scheduled days in the current streak."""
    return calculate_streak_status(completed_dates, today, grace_day, scheduled_days)[0]


def daily_progress(habits, day):
    """Summarise how many of the habits due on ``day`` have been completed."""
    due = [habit for habit in habits if habit.is_scheduled_on(day)]
    done = sum(1 for habit in due if day in habit.completed_dates_list)
    percent = round(100 * done / len(due)) if due else 0
    return {'done': done, 'total': len(due), 'percent': percent}

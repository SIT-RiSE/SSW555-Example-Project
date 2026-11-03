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

    def current_streak(self, today=None):
        """Current streak: US-07's grace-day count when enabled, otherwise the
        schedule- and frequency-aware count from US-14."""
        today = today or date.today()
        if self.grace_day_enabled:
            return calculate_streak(self.completed_dates_list, today, grace_day=True)
        return self.calculate_current_streak(as_of=today)

    @property
    def completion_dates(self):
        """Return the valid, unique ISO dates stored in the completion history."""
        parsed_dates = set()
        for value in _parse_completion_dates(self.completed_dates):
            try:
                parsed_dates.add(date.fromisoformat(str(value).strip()))
            except ValueError:
                # Ignore malformed legacy entries rather than breaking the dashboard.
                continue
        return parsed_dates

    def calculate_current_streak(self, as_of=None):
        """Count consecutive due periods completed through ``as_of``.

        An incomplete current day/week/month does not end a streak while that
        period is still in progress. A missed earlier scheduled period does.
        """
        as_of = as_of or date.today()
        completions = {completed for completed in self.completion_dates if completed <= as_of}
        if not completions:
            return 0

        scheduled_weekdays = {
            WEEKDAYS.index(day) for day in self.scheduled_days_list if day in WEEKDAYS
        }
        if scheduled_weekdays:
            return self._scheduled_day_streak(completions, scheduled_weekdays, as_of)
        if self.frequency == 'weekly':
            return self._weekly_streak(completions, as_of)
        if self.frequency == 'monthly':
            return self._monthly_streak(completions, as_of)
        return self._scheduled_day_streak(completions, set(range(7)), as_of)

    @staticmethod
    def _scheduled_day_streak(completions, scheduled_weekdays, as_of):
        def previous_scheduled_day(current):
            candidate = current - timedelta(days=1)
            while candidate.weekday() not in scheduled_weekdays:
                candidate -= timedelta(days=1)
            return candidate

        current = as_of
        while current.weekday() not in scheduled_weekdays:
            current -= timedelta(days=1)

        # Today's scheduled completion can still be completed before the day ends.
        if current == as_of and current not in completions:
            current = previous_scheduled_day(current)

        streak = 0
        while current in completions:
            streak += 1
            current = previous_scheduled_day(current)
        return streak

    @staticmethod
    def _weekly_streak(completions, as_of):
        completed_weeks = {
            completed - timedelta(days=completed.weekday()) for completed in completions
        }
        current_week = as_of - timedelta(days=as_of.weekday())
        if current_week not in completed_weeks:
            current_week -= timedelta(weeks=1)

        streak = 0
        while current_week in completed_weeks:
            streak += 1
            current_week -= timedelta(weeks=1)
        return streak

    @staticmethod
    def _monthly_streak(completions, as_of):
        completed_months = {date(completed.year, completed.month, 1) for completed in completions}
        current_month = date(as_of.year, as_of.month, 1)

        def previous_month(month):
            if month.month == 1:
                return date(month.year - 1, 12, 1)
            return date(month.year, month.month - 1, 1)

        if current_month not in completed_months:
            current_month = previous_month(current_month)

        streak = 0
        while current_month in completed_months:
            streak += 1
            current_month = previous_month(current_month)
        return streak

    def is_scheduled_on(self, day):
        """True if ``day`` is one of the habit's scheduled weekdays (any day when unscheduled)."""
        scheduled = self.scheduled_days_list
        return not scheduled or WEEKDAYS[day.weekday()] in scheduled

    @property
    def recent_completions(self):
        """The five most recent completion dates, newest first."""
        return sorted(self.completion_dates, reverse=True)[:5]


def daily_progress(habits, day):
    """Summarise how many of the habits due on ``day`` have been completed."""
    due = [habit for habit in habits if habit.is_scheduled_on(day)]
    done = sum(1 for habit in due if day in habit.completion_dates)
    percent = round(100 * done / len(due)) if due else 0
    return {'done': done, 'total': len(due), 'percent': percent}


def calculate_streak(completed_dates, today, grace_day=False):
    """Count consecutive completed days ending today (or yesterday).

    Today not being completed yet does not break the streak. With ``grace_day``
    on, the first missed day in each Monday-to-Sunday week is skipped instead of
    ending the streak; a grace day keeps the streak alive but does not add to it.
    """
    done = set(completed_dates)
    if not done:
        return 0

    day = today if today in done else today - timedelta(days=1)
    earliest = min(done)
    weeks_with_grace_used = set()
    streak = 0
    while day >= earliest:
        if day in done:
            streak += 1
        else:
            week = tuple(day.isocalendar())[:2]
            if not grace_day or week in weeks_with_grace_used:
                break
            weeks_with_grace_used.add(week)
        day -= timedelta(days=1)
    return streak

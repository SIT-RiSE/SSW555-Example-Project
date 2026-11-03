from datetime import date, datetime, timedelta

from extensions import db


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

    @property
    def scheduled_days_list(self):
        if not self.scheduled_days:
            return []
        return self.scheduled_days.split(",")

    @property
    def frequency_period(self):
        """The period a single completion covers, e.g. 'week' for a weekly habit."""
        return HABIT_FREQUENCIES.get(self.frequency or DEFAULT_FREQUENCY, 'day')

    @property
    def completion_dates(self):
        """Return the valid, unique ISO dates stored in the completion history."""
        parsed_dates = set()
        for value in (self.completed_dates or '').split(','):
            try:
                parsed_dates.add(date.fromisoformat(value.strip()))
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

    @property
    def current_streak(self):
        return self.calculate_current_streak()

    def is_scheduled_on(self, day):
        """True if ``day`` is one of the habit's scheduled weekdays (any day when unscheduled)."""
        scheduled = self.scheduled_days_list
        return not scheduled or WEEKDAYS[day.weekday()] in scheduled

    def add_completion(self, day):
        """Record ``day`` in the completion history, keeping it sorted and unique."""
        dates = self.completion_dates | {day}
        self.completed_dates = ','.join(d.isoformat() for d in sorted(dates))

    def is_due_on(self, day):
        """True if the habit is expected to be completed on ``day``.

        A weekday schedule decides when one is set; otherwise only daily habits
        are due every day.
        """
        if self.scheduled_days_list:
            return self.is_scheduled_on(day)
        return (self.frequency or DEFAULT_FREQUENCY) == 'daily'

    @property
    def recent_completions(self):
        """The five most recent completion dates, newest first."""
        return sorted(self.completion_dates, reverse=True)[:5]


def daily_progress(habits, day):
    """Summarise how many of the habits due on ``day`` have been completed."""
    due = [habit for habit in habits if habit.is_due_on(day)]
    done = sum(1 for habit in due if day in habit.completion_dates)
    percent = round(100 * done / len(due)) if due else 0
    return {'done': done, 'total': len(due), 'percent': percent}

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
    # US-07: when on, one missed day per calendar week (Mon-Sun) does not break
    # the habit's streak.
    grace_day_enabled = db.Column(db.Boolean, nullable=False, default=False,
                                  server_default='0')

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
    def completed_dates_list(self):
        """Completion dates parsed from the comma-separated ISO dates column."""
        if not self.completed_dates:
            return []
        return [date.fromisoformat(value.strip())
                for value in self.completed_dates.split(",") if value.strip()]

    def current_streak(self, today=None):
        """Consecutive completed days, honoring the weekly grace day if enabled."""
        return calculate_streak(self.completed_dates_list, today or date.today(),
                                grace_day=self.grace_day_enabled)


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

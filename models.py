import json
from datetime import date, datetime

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

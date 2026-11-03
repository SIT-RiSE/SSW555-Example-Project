from datetime import date, datetime

from flask import Flask, abort, jsonify, redirect, render_template, request, url_for
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from extensions import db

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

from models import DEFAULT_FREQUENCY, HABIT_FREQUENCIES, WEEKDAYS, Category, Habit  # noqa: E402


@app.route('/')
def home():
    return render_template('home/index.html', page_id='home')

@app.route('/habit-tracker', methods=['GET', 'POST'])
def habit_tracker():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()

        if name:
            habit = Habit(name=name, description=description or None,
                          category=selected_category(), frequency=selected_frequency())
            db.session.add(habit)
            db.session.commit()

        return redirect(url_for('habit_tracker'))

    habits = Habit.query.order_by(Habit.created_at.desc()).all()
    dashboard_view = request.args.get('view', 'all')
    if dashboard_view not in ('all', 'today'):
        abort(400, description='View must be all or today.')
    today = date.today()
    if dashboard_view == 'today':
        weekday = WEEKDAYS[today.weekday()]
        habits = [habit for habit in habits
                  if not habit.scheduled_days_list or weekday in habit.scheduled_days_list]
    return render_template('apps/habit_tracker/index.html', page_id='habit-tracker', habits=habits,
                           dashboard_view=dashboard_view, today=today,
                           categories=Category.query.order_by(Category.name).all(),
                           frequencies=HABIT_FREQUENCIES,
                           due_today_ids={habit.id for habit in habits
                                          if not habit.scheduled_days_list
                                          or WEEKDAYS[date.today().weekday()]
                                          in habit.scheduled_days_list})


@app.route('/habit-tracker/<int:habit_id>/complete', methods=['POST'])
def complete_habit(habit_id):
    """Record a due habit's completion for today and return to the dashboard."""
    habit = db.session.get(Habit, habit_id)
    if habit is None:
        abort(404)
    today = date.today()
    if habit.scheduled_days_list and WEEKDAYS[today.weekday()] not in habit.scheduled_days_list:
        abort(400, description='This habit is not scheduled for today.')
    habit.mark_complete(today)
    if request.form.get('view') == 'today':
        return redirect(url_for('habit_tracker', view='today'))
    return redirect(url_for('habit_tracker'))


@app.route('/habit-tracker/habits')
def list_current_habits():
    """US-11: all current habits, newest first."""
    habits = Habit.query.order_by(Habit.created_at.desc()).all()
    return jsonify(count=len(habits), habits=[habit.to_dict() for habit in habits])


@app.route('/habit-tracker/habits/<int:habit_id>')
def view_habit(habit_id):
    """US-11: the full details of one current habit."""
    habit = db.session.get(Habit, habit_id)
    if habit is None:
        abort(404)
    return jsonify(habit.to_dict())



def selected_frequency():
    frequency = request.form.get('frequency', '').strip().lower() or DEFAULT_FREQUENCY
    if frequency not in HABIT_FREQUENCIES:
        abort(400, description='Frequency must be daily, weekly, or monthly.')
    return frequency


def selected_category():
    category_id = request.form.get('category_id', '').strip()
    if not category_id:
        return None
    try:
        category = db.session.get(Category, int(category_id))
    except ValueError:
        abort(400, description='Select an existing category.')
    if category is None:
        abort(400, description='Select an existing category.')
    return category


@app.route('/habit-tracker/categories', methods=['POST'])
def create_category():
    name = request.form.get('name', '').strip()
    if not name or len(name) > 100:
        abort(400, description='Category name must contain 1 to 100 characters.')
    db.session.add(Category(name=name))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        abort(400, description='A category with that name already exists.')
    return redirect(url_for('habit_tracker'))


@app.route('/habit-tracker/<int:habit_id>/edit', methods=['POST'])
def edit_habit(habit_id):
    """Update an existing habit's name, description, and frequency."""
    habit = db.session.get(Habit, habit_id)
    if habit is None:
        abort(404)

    name = request.form.get('name', '').strip()
    if not name or len(name) > 100:
        abort(400, description='Habit name must contain 1 to 100 characters.')
    frequency = selected_frequency() if 'frequency' in request.form else habit.frequency

    habit.name = name
    if 'description' in request.form:
        habit.description = request.form['description'].strip() or None
    habit.frequency = frequency
    db.session.commit()
    return redirect(url_for('habit_tracker'))


@app.route('/habit-tracker/<int:habit_id>/category', methods=['POST'])
def update_habit_category(habit_id):
    habit = db.session.get(Habit, habit_id)
    if habit is None:
        abort(404)
    habit.category = selected_category()
    db.session.commit()
    return redirect(url_for('habit_tracker'))


@app.route('/habit-tracker/<int:habit_id>/reminder', methods=['POST'])
def update_habit_reminder(habit_id):
    """Attach, update, or remove an optional reminder from an existing habit."""
    habit = db.session.get(Habit, habit_id)
    if habit is None:
        abort(404)

    reminder_time = request.form.get('reminder_time', '').strip()
    if reminder_time:
        try:
            datetime.strptime(reminder_time, '%H:%M')
        except ValueError:
            abort(400, description='Reminder time must use the HH:MM format.')

    habit.reminder_time = reminder_time or None
    db.session.commit()
    return redirect(url_for('habit_tracker'))


@app.route('/habit-tracker/<int:habit_id>/schedule', methods=['POST'])
def update_habit_schedule(habit_id):
    """Set which days of the week an existing habit is scheduled for."""
    habit = db.session.get(Habit, habit_id)
    if habit is None:
        abort(404)

    selected_days = request.form.getlist('days')
    if not selected_days or any(day not in WEEKDAYS for day in selected_days):
        abort(400, description='Select at least one valid day of the week.')

    habit.scheduled_days = ','.join(day for day in WEEKDAYS if day in selected_days)
    db.session.commit()
    return redirect(url_for('habit_tracker'))

@app.route('/habit-tracker/<int:habit_id>/check-in', methods=['POST'])
def log_check_in(habit_id):
    """Record a completion for today or back-fill one for a missed past date."""
    habit = db.session.get(Habit, habit_id)
    if habit is None:
        abort(404)

    try:
        completed_on = date.fromisoformat(request.form.get('completed_on', '').strip())
    except ValueError:
        abort(400, description='Check-in date must use the YYYY-MM-DD format.')
    if completed_on > date.today():
        abort(400, description='Check-ins cannot be logged for future dates.')
    if not habit.is_scheduled_on(completed_on):
        abort(400, description='Check-ins can only be logged for scheduled days.')

    habit.mark_complete(completed_on)
    return redirect(url_for('habit_tracker'))


@app.route('/habit-tracker/<int:habit_id>/grace-day', methods=['POST'])
def update_habit_grace_day(habit_id):
    """Turn the weekly grace day on or off for an existing habit."""
    habit = db.session.get(Habit, habit_id)
    if habit is None:
        abort(404)
    habit.grace_day_enabled = request.form.get('enabled') == 'on'
    db.session.commit()
    return redirect(url_for('habit_tracker'))


def init_db():
    with app.app_context():
        db.create_all()
        # create_all does not add columns to existing SQLite tables.
        habit_columns = {column['name'] for column in inspect(db.engine).get_columns('habit')}
        with db.engine.begin() as connection:
            if 'category_id' not in habit_columns:
                connection.execute(text(
                    'ALTER TABLE habit ADD COLUMN category_id INTEGER REFERENCES category(id)'
                ))
            if 'frequency' not in habit_columns:
                connection.execute(text(
                    "ALTER TABLE habit ADD COLUMN frequency VARCHAR(10) NOT NULL DEFAULT 'daily'"
                ))
            if 'scheduled_days' not in habit_columns:
                connection.execute(text('ALTER TABLE habit ADD COLUMN scheduled_days TEXT'))
            if 'grace_day_enabled' not in habit_columns:
                connection.execute(text(
                    'ALTER TABLE habit ADD COLUMN grace_day_enabled BOOLEAN NOT NULL DEFAULT 0'
                ))

# Called at import time so the schema exists under `flask run` too, not just
# `python app.py` — `flask run` imports this module without ever reaching
# the __main__ block below.
init_db()

if __name__ == '__main__':
    app.run(debug=True)

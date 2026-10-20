from datetime import datetime

from flask import Flask, abort, redirect, render_template, request, url_for
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from extensions import db

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

from models import Category, Expense, Habit, MoodEntry, Recipe  # noqa: E402


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
                          category=selected_category())
            db.session.add(habit)
            db.session.commit()

        return redirect(url_for('habit_tracker'))

    habits = Habit.query.order_by(Habit.created_at.desc()).all()
    return render_template('apps/habit_tracker/index.html', page_id='habit-tracker', habits=habits,
                           categories=Category.query.order_by(Category.name).all())


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

@app.route('/mood-journal', methods=['GET', 'POST'])
def mood_journal():
    if request.method == 'POST':
        mood = request.form.get('mood', '').strip()
        notes = request.form.get('notes', '').strip()

        if mood:
            entry = MoodEntry(mood=mood, notes=notes or None)
            db.session.add(entry)
            db.session.commit()

        return redirect(url_for('mood_journal'))

    entries = MoodEntry.query.order_by(MoodEntry.created_at.desc()).all()
    return render_template('apps/mood_journal/index.html', page_id='mood-journal', entries=entries)

@app.route('/expense-splitter', methods=['GET', 'POST'])
def expense_splitter():
    if request.method == 'POST':
        description = request.form.get('description', '').strip()
        amount_raw = request.form.get('amount', '').strip()
        payer = request.form.get('payer', '').strip()
        participants = request.form.get('participants', '').strip()

        try:
            amount = float(amount_raw)
        except ValueError:
            amount = None

        if description and amount is not None and payer:
            expense = Expense(
                description=description,
                amount=amount,
                payer=payer,
                participants=participants or None
            )
            db.session.add(expense)
            db.session.commit()

        return redirect(url_for('expense_splitter'))

    expenses = Expense.query.order_by(Expense.created_at.desc()).all()
    expense_views = []
    for expense in expenses:
        people = [p.strip() for p in (expense.participants or '').split(',') if p.strip()]
        share = expense.amount / len(people) if people else None
        expense_views.append({
            'model': expense,
            'participants': people,
            'share': share
        })

    return render_template(
        'apps/expense_splitter/index.html',
        page_id='expense-splitter',
        expenses=expense_views
    )

@app.route('/recipe-assistant', methods=['GET', 'POST'])
def recipe_assistant():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        ingredients = request.form.get('ingredients', '').strip()
        instructions = request.form.get('instructions', '').strip()
        prep_time_raw = request.form.get('prep_time', '').strip()

        try:
            prep_time = int(prep_time_raw)
            if prep_time < 0:
                prep_time = None
        except ValueError:
            prep_time = None

        if name and ingredients and instructions:
            recipe = Recipe(
                name=name,
                ingredients=ingredients,
                instructions=instructions,
                prep_time=prep_time
            )
            db.session.add(recipe)
            db.session.commit()

        return redirect(url_for('recipe_assistant'))

    recipes = Recipe.query.order_by(Recipe.created_at.desc()).all()
    return render_template(
        'apps/recipe_assistant/index.html',
        page_id='recipe-assistant',
        recipes=recipes
    )

def init_db():
    with app.app_context():
        db.create_all()
        # create_all does not add columns to existing SQLite tables.
        if 'category_id' not in {column['name'] for column in inspect(db.engine).get_columns('habit')}:
            with db.engine.begin() as connection:
                connection.execute(text(
                    'ALTER TABLE habit ADD COLUMN category_id INTEGER REFERENCES category(id)'
                ))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)

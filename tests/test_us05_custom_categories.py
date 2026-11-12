import pytest
from sqlalchemy import text

from app import init_db
from extensions import db
from models import Category, Habit


def test_category_is_saved_and_available_for_creation_and_editing(client):
    client.post('/habit-tracker', data={'name': 'Read'})
    response = client.post('/habit-tracker/categories', data={'name': '  Learning  '})
    assert response.status_code == 302
    db.session.remove()
    category = Category.query.one()
    assert category.name == 'Learning'
    page = client.get('/habit-tracker').data
    assert page.count(b'>Learning</option>') == 2
    client.post('/habit-tracker', data={'name': 'Study', 'category_id': category.id})
    habit = Habit.query.filter_by(name='Study').one()
    assert habit.category_id == category.id
    existing_id = Habit.query.filter_by(name='Read').one().id
    response = client.post(f'/habit-tracker/{existing_id}/category', data={'category_id': category.id})
    assert response.status_code == 302
    db.session.remove()
    assert db.session.get(Habit, existing_id).category.name == 'Learning'
    assert b' selected>Learning</option>' in client.get('/habit-tracker').data


@pytest.mark.parametrize('name', ['', '   ', 'x' * 101])
def test_invalid_category_names_are_rejected(client, name):
    assert client.post('/habit-tracker/categories', data={'name': name}).status_code == 400
    assert Category.query.count() == 0


def test_duplicate_category_is_rejected_case_insensitively(client):
    client.post('/habit-tracker/categories', data={'name': 'Health'})
    assert client.post('/habit-tracker/categories', data={'name': ' health '}).status_code == 400
    assert Category.query.count() == 1


@pytest.mark.parametrize('category_id', ['9999', 'invalid'])
def test_invalid_category_does_not_create_habit(client, category_id):
    assert client.post('/habit-tracker', data={'name': 'Read', 'category_id': category_id}).status_code == 400
    assert Habit.query.count() == 0


def test_category_can_be_changed_and_cleared_without_affecting_reminder(client):
    category = Category(name='Wellness')
    habit = Habit(name='Walk', reminder_time='09:00')
    db.session.add_all([category, habit])
    db.session.commit()
    path = f'/habit-tracker/{habit.id}/category'
    client.post(path, data={'category_id': category.id})
    assert habit.category == category
    assert client.post(path, data={'category_id': '9999'}).status_code == 400
    assert habit.category == category
    client.post(path, data={'category_id': ''})
    assert habit.category is None
    assert habit.reminder_time == '09:00'
    assert client.post('/habit-tracker/9999/category', data={}).status_code == 404


def test_upgrade_preserves_existing_habits_and_is_repeatable(app):
    db.session.remove()
    db.drop_all()
    with db.engine.begin() as connection:
        connection.execute(text('CREATE TABLE habit (id INTEGER PRIMARY KEY, name VARCHAR(100) NOT NULL, description TEXT, reminder_time VARCHAR(5), created_at DATETIME, completed_dates TEXT)'))
        connection.execute(text("INSERT INTO habit (name, reminder_time) VALUES ('Read', '09:00')"))
    init_db()
    init_db()
    habit = Habit.query.one()
    assert habit.name == 'Read'
    assert habit.reminder_time == '09:00'
    assert habit.category is None
    assert Category.query.count() == 0

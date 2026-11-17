"""
US-27: Create an Account

As a new user, I want to create an account so that my habits and progress can
be saved.
"""

import pytest

from extensions import db
from models import User

PASSWORD = 'correct-horse-9'


def register(client, username='neil', password=PASSWORD, confirm=None, **kwargs):
    return client.post('/register', data={
        'username': username,
        'password': password,
        'confirm_password': password if confirm is None else confirm,
    }, **kwargs)


def test_us27_registration_page_is_available(client):
    response = client.get('/register')

    assert response.status_code == 200
    assert b'Create an account' in response.data


def test_us27_valid_registration_creates_an_account(client):
    """AC: Valid account information creates the account."""
    response = register(client, follow_redirects=True)

    assert response.status_code == 200
    assert b'Account created for neil.' in response.data
    user = User.query.filter_by(username='neil').one()
    assert user.created_at is not None


def test_us27_password_is_stored_securely(client):
    """Risk: credentials must be stored securely (salted hash, never plaintext)."""
    register(client)
    register(client, username='second')

    first, second = User.query.order_by(User.id).all()
    assert PASSWORD not in first.password_hash
    assert first.password_hash != second.password_hash  # salted
    assert first.check_password(PASSWORD)
    assert not first.check_password('wrong-password')


def test_us27_username_is_trimmed(client):
    register(client, username='  neil  ')

    assert User.query.one().username == 'neil'


def test_us27_duplicate_username_is_rejected_case_insensitively(client):
    register(client, username='Neil')

    response = register(client, username='neil')

    assert response.status_code == 400
    assert b'That username is already taken.' in response.data
    assert User.query.count() == 1


@pytest.mark.parametrize('username', ['', 'ab', 'x' * 31, 'has space', 'bad!name'])
def test_us27_invalid_usernames_are_rejected(client, username):
    response = register(client, username=username)

    assert response.status_code == 400
    assert User.query.count() == 0


@pytest.mark.parametrize('password', ['', 'short', 'x' * 129])
def test_us27_invalid_passwords_are_rejected(client, password):
    response = register(client, password=password)

    assert response.status_code == 400
    assert User.query.count() == 0


def test_us27_mismatched_confirmation_is_rejected(client):
    response = register(client, confirm='something-else')

    assert response.status_code == 400
    assert b'Passwords do not match.' in response.data
    assert User.query.count() == 0


def test_us27_failed_registration_keeps_username_but_not_password(client):
    response = register(client, username='neil', confirm='something-else')
    page = response.data.decode()

    assert 'value="neil"' in page
    assert PASSWORD not in page


def test_us27_create_account_link_is_in_navigation(client):
    page = client.get('/habit-tracker').data.decode()

    assert 'href="/register"' in page


def test_us27_init_db_adds_user_table_to_existing_database(app):
    from sqlalchemy import inspect

    from app import init_db

    db.session.remove()
    User.__table__.drop(db.engine)
    init_db()

    assert 'user' in inspect(db.engine).get_table_names()

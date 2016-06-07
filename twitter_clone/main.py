import os

from flask import Flask

app = Flask(__name__)
app.config['SECRET_KEY'] = "kljasdno9asud89uy981uoaisjdoiajsdm89uas980d"

"""
/login
GET: show login form
POST: authenticate

/:user-handle
GET: see all user tweets and new tweet form
POST (auth): write a new tweet

/profile
GET (auth): see user profile data
POST (auth): update user profile data

/tweets/:tweet-id
GET: see one tweet detail
DELETE: remove tweet
"""

import sqlite3
from hashlib import md5
from functools import wraps
from flask import (g, request, session, redirect, render_template, flash,
                   abort, jsonify, Response, url_for)

from twitter_clone import settings


def connect_db():
    return sqlite3.connect(settings.DATABASE_NAME)


@app.before_request
def before_request():
    g.db = connect_db()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/login', methods=['GET', 'POST'])
def login():
    next = request.args.get('next', '/')

    if 'username' in session:
        flash('You are actually logged in, there is no need to login again', 'warning')
        return redirect(next)

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = g.db.execute(
            'SELECT password FROM user WHERE username=:username;', {'username': username})
        user = cursor.fetchone()
        if user and user[0] == md5(password).hexdigest():
            session['username'] = username
            flash('You were correctly logged in', 'success')
            return redirect(next)

        # authentication faild
        flash('Invalid username or password', 'danger')

    return render_template('login.html', next=next)


@app.route('/logout')
@login_required
def logout():
    next = request.args.get('next', '/')
    session.pop('username', None)
    flash('You were correctly logged out', 'info')
    return redirect(next)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        query = 'UPDATE user SET first_name=:first_name, last_name=:last_name, birth_date=:birth_date WHERE username=:username;'
        params = {
            'first_name': request.form.get('first_name'),
            'last_name': request.form.get('last_name'),
            'birth_date': request.form.get('birth_date'),
            'username': session['username']
        }
        try:
            g.db.execute(query, params)
            g.db.commit()
        except sqlite3.IntegrityError:
            flash('Something went wrong while updating your profile', 'danger')
        else:
            flash('Your profile was correctly updated', 'success')

    cursor = g.db.execute(
        'SELECT username, first_name, last_name, birth_date FROM user WHERE username=:username;',
        {'username': session['username']})
    username, first_name, last_name, birth_date = cursor.fetchone()
    return render_template('profile.html', username=username, first_name=first_name,
                           last_name=last_name, birth_date=birth_date)

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
from flask import (g, request, session, redirect, render_template, flash,
                   abort, jsonify, Response)

from twitter_clone import settings


def connect_db():
    return sqlite3.connect(settings.DATABASE_NAME)


@app.before_request
def before_request():
    g.db = connect_db()


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
def logout():
    next = request.args.get('next', '/')
    session.pop('username', None)
    flash('You were correctly logged out', 'info')
    return redirect(next)


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

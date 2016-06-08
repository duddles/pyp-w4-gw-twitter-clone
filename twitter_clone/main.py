import sqlite3
import jinja2
import os
from hashlib import md5
from functools import wraps
from flask import Flask
from flask import (g, request, session, redirect, render_template,
                   flash, url_for)

app = Flask(__name__)

#creates a jinja env...no idea what this does
'''JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)'''
    
def connect_db(db_name):
    return sqlite3.connect(db_name)


@app.before_request
def before_request():
    #session.pop('username', None) # do we need to erase session when start?
    g.db = connect_db(app.config['DATABASE'][1])


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session: # session['username']
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function
    
@app.route('/login', methods=['GET', 'POST'])
def login():
    #print 'url = {}'.format(request.url_root)
    # check if already logged in
    # if already logged in send them to user feed page
    if 'username' in session:
          return redirect('/')
          
    #print session['username']
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password = md5(password).hexdigest()
        cursor = g.db.execute('SELECT id, username, password FROM user;')
        user_data = cursor.fetchall() # list of tuples 
        for user_tuple in user_data:
            if username == user_tuple[1] and password == user_tuple[2]:
                # check password (http://pythoncentral.io/hashing-strings-with-python/)
                #hash_object = md5()
                #print(hash_object.hexdigest())
                session['username'] = username
                session['user_id'] = user_tuple[0]
                # redirect to the users logged in feed
                #return redirect(next)
                return redirect('/') # doing this because the test login_redirects_next seems to require it
                #return redirect('/{}'.format(session['username']))
        
        # Username was not found in database
        flash('Invalid username or password') 
        # "user" ("id", "username", "password", "birth_date") VALUES (10, "martinzugnoni", "81dc9bdb52d04dc20036dbd8313ed055", "2016-01-26")
        #print app.config['DATABASE']
        #print(user_data)
    return render_template('login.html')
    
@app.route('/profile', methods = ['GET','POST'])
#@login_required
def profile():
    # get the user info from the db
    if 'username' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        try:
            new_username = request.form['username']
            new_firstname = request.form['first_name']
            new_lastname = request.form['last_name']
            new_birthdate = request.form['birth_date']
            sql_command = 'UPDATE user SET username = ?, first_name = ?, \
            last_name = ?, birth_date = ? WHERE id = ?'
            sql_args = [new_username, new_firstname, new_lastname, new_birthdate, session['user_id']]
            g.db.execute(sql_command, sql_args)
            g.db.commit()
            
            flash('Your profile was correctly updated')
        except:
            flash('Your profile was not updated')
        
    #print 'we are in profile with session user name = {}'.format(session['username'])
    sql_command = 'SELECT first_name, last_name, birth_date FROM user WHERE id = ?;'
    cursor = g.db.execute(sql_command, [session['user_id']])
    first_name, last_name, birth_date = cursor.fetchone()
    return render_template('dynamic_profile.html', username = session['username'],
    firstname = first_name, lastname = last_name, birthdate = birth_date, urlroot = request.url_root)

@app.route('/<username>', methods=['GET', 'POST'])
#@app.route('/own_feed', methods=['GET', 'POST'])
#def own_feed():
def feed(username):
    #print 'We are entering feed with username = {}'.format(username)
    
    # strange bug where at the end of profile it was doing a GET request on styles.css
    # which was leading to /favicon.ico so it was coming here with 
    # username = favicon.ico ... how do we avoid this?
    if username == 'favicon.ico': 
        #print 'got here'
        return redirect(url_for('profile'))
    #if 'username' not in session:
        #print 'no username'
    #else:
        #print 'has username = {}'.format(session['username'])
        #print 'has userid = {}'.format(session['user_id'])
    if request.method == 'POST': # submitting a tweet
        if 'username' not in session:
            return redirect('/'), 403
        tweet = request.form.get('tweet') # in own_feed.html line 45 it is named 'tweet'
        
        sql_command = "INSERT INTO tweet ('user_id', 'content') VALUES (?, ?)"
        g.db.execute(sql_command, (session['user_id'], tweet))
        g.db.commit()
        # write tweet to database
        
        flash('Tweet was added')

        #return redirect(url_for('own_feed'))
    
    # We want all the tweets from the session username
    all_tweets = feed_data(username)
    #for tweet in all_tweets:
    #    print tweet['content']
    if 'username' in session and session['username'] == username:
        return render_template('dynamic_own_feed.html', tweets=all_tweets[::-1], username=session['username'])
    else:
        return render_template('dynamic_other_feed.html', tweets=all_tweets[::-1], username=username)
    #return render_template('own_feed.html')
    

def feed_data(user_name):
    #print 'Feed_data was called with user_name {}'.format(user_name)
    template_data = []
    # actually I stored session[user_id] so we could could skip next line
    tweet_id = g.db.execute('select id from user where username = ?',
                [user_name])
    tweet_id = tweet_id.fetchone()[0]
    feed_output = g.db.execute('SELECT user_id, created, content, id FROM tweet WHERE user_id = ?;',[tweet_id])
    for row in feed_output:
        dict_keys = ("user_id", "created", "content", "tweet_id")
        row_dict = dict(zip(dict_keys, row))
        template_data.append(row_dict)

    return template_data
    #passing a list of dictionaries and the user name
    # template needs: user_name, created, content
    #generate variables to pass to feed templates
    # if the url is not the current user's personal feed:
    #    given the username in the url, get the user_id
    #    query the tweet table for the user_id and corresponding content
    # for user_id, content in tweet Table - 
    #     pass to other_feed.html template
@app.route('/tweets/<int:tweet_id>/delete', methods=['POST'])
@login_required
def tweet(tweet_id):
    '''
    When click on delete the form action is:
    form action="/tweets/{{tweet.tweet_id}}/delete?next={{urlroot}}{{username}}"
    '''
    next = request.args.get('next', '/')
    sql_command = 'DELETE FROM tweet WHERE id = ?'
    g.db.execute(sql_command, [tweet_id])
    g.db.commit()
    flash('Tweet was deleted')
    return redirect(next)

# logout
@app.route('/logout')
@login_required
def logout():
   # remove the username from the session if it is there
   session.pop('username', None)
   session.pop('user_id', None)
   
   #return redirect(url_for('feed'))
   # but if they logout from another page do we want to return them to that page?
   return redirect('/')
   
@app.route('/', methods=['GET'])
@login_required
def index():
    if 'username' in session:
        return redirect('/{}'.format(session['username']))

# user feed
# different things depending on if logged in as user

# user profile

app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT' # not sure about 


# what exactly is next, the info after ? in url ?next=login

# how would it work with multiple submit buttons on one page, how 
# does methods know which post is which?

# It seems like the CURRENT_TIMESTAMP is being added automatically by sqlite3? yes it is
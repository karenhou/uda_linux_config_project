from flask import Flask, render_template, request, redirect, jsonify, url_for, flash
from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, EquipmentItem, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import func

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('/var/www/catalog/catalog/oauth/client_secret_google.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Sports Category Application"

# Connect to Database and create database session
#engine = create_engine('sqlite:///sportscategory.db')
engine = create_engine('postgresql://catalog:catalog@localhost/catalog')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# Create a state token to prevent request forgery
# Store it in the session for later validation
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.
                                  digits) for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session['email'],
                   picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).first()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

# login to FB account
@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token

    app_id = json.loads(open('/var/www/catalog/catalog/oauth/fbclientsecrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('/var/www/catalog/catalog/oauth/fbclientsecrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (
        app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.8/me"
    '''
        Due to the formatting for the result from the server token exchange we have to
        split the token first on commas and select the first index which gives us the key : value
        for the server access token then we split it on colons to pull out the actual token value
        and replace the remaining quotes with nothing so that it can be used directly in the graph
        api calls
    '''
    token = result.split(',')[0].split(':')[1].replace('"', '')

    url = 'https://graph.facebook.com/v2.8/me?access_token=%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly logout
    login_session['access_token'] = token

    # Get user picture
    url = 'https://graph.facebook.com/v2.8/me/picture?access_token=%s&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    flash("Now logged in as %s" % login_session['username'])
    return output

# log off from Facebook
@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (
        facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"


# log in to Google
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets(
            '/var/www/catalog/catalog/oauth/client_secret_google.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    login_session['provider'] = 'google'

    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

# log off from Google
@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps(
            'Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: '
    print login_session['username']
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % login_session[
        'access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps(
            'Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# JSON APIs to view Category Information
@app.route('/catalog/<int:category_id>/equipments.json')
def EquipmentJSON(category_id):
    items = session.query(EquipmentItem).filter_by(
        category_id=category_id).all()
    return jsonify(Items=[i.serialize for i in items])

@app.route('/catalog/all_equips.json')
def allEquipsJSON():
    equip = session.query(EquipmentItem).all()
    return jsonify(Item=[e.serialize for e in equip])

@app.route('/catalog.json')
def categoryJSON():
    categories = session.query(Category).all()
    items = session.query(EquipmentItem).all()
    return jsonify(categories=[r.serialize for r in categories], items = [i.serialize for i in items])


# Show all categories
@app.route('/')
@app.route('/catalog/')
def showCategories():
    #categories = session.query(Category).order_by(asc(Category.name))
    categories = session.query(Category).all()
    latest_add = session.query(EquipmentItem).order_by(desc(EquipmentItem.time_updated)).limit(9).all()
    if 'username' not in login_session:
        return render_template('publicCategory.html', categories=categories, latest_add=latest_add)
    else:
        return render_template('categories.html', categories=categories, latest_add=latest_add)

# Create a new category
@app.route('/catalog/new/', methods=['GET', 'POST'])
def newCategory():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newCategory = Category(name=request.form['name'],
                               user_id=login_session['user_id'])
        session.add(newCategory)
        session.commit()
        return redirect(url_for('showCategories'))
    else:
        return render_template('newCategory.html')

# Edit a category
'''@app.route('/catalog/<category_name>/edit/', methods=['GET','POST'])
def editCategory(category_name):
    if 'username' not in login_session:
        return redirect('/login')
    editCategory = session.query(Category).filter_by(name = category_name).one()
    if editCategory.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to edit"
        " this category. Please create your own category in order to edit.')"
        ";}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        if request.form['name']:
            editCategory.name = request.form['name']
            session.add(editCategory)
            session.commit()
            flash('Category Successfully Edited %s' % editCategory.name)
            return redirect(url_for('showCategories'))
    else:
        return render_template('editCategory.html', category_name=category_name, editCategory = editCategory)

#Delete a category
@app.route('/catalog/<category_name>/delete/', methods=['GET','POST'])
def deleteCategory(category_name):
  if 'username' not in login_session:
    return redirect('/login')
  categoryToDelete = session.query(Category).filter_by(name = category_name).one()
  if categoryToDelete.user_id != login_session['user_id']:
    return "<script>function myFunction() {alert('You are not authorized to delete"
    " this category. Please create your own category in order to delete.')"
    ";}</script><body onload='myFunction()''>"
  if request.method == 'POST':
    session.delete(categoryToDelete)
    flash('%s Successfully Deleted' % categoryToDelete.name)
    session.commit()
    return redirect(url_for('showCategories', category_name = category_name))
  else:
    return render_template('deleteCategory.html',category = categoryToDelete)'''

# List all equipment under specific category
@app.route('/catalog/<category_name>/')
@app.route('/catalog/<category_name>/items')
def showItem(category_name):
    count = 0
    categories = session.query(Category).all()
    category = session.query(Category).filter_by(name=category_name).one()
    creator = getUserInfo(category.user_id)
    items = session.query(EquipmentItem).all()
    for item in items:
        if item.category_id == category.id:
            count = count + 1
    # if 'username' not in login_session or creator.id !=
    # login_session['user_id']:
    if 'username' not in login_session:
        return render_template('publicItems.html', items=items, category=category,
                               creator=creator, categories=categories, count=count)
    else:
        return render_template('items.html', items=items, category=category,
                               creator=creator, categories=categories, count=count)

# Show particular equipment with description
@app.route('/catalog/<category_name>/<item_name>')
def showEquip(category_name, item_name):
    category = session.query(Category).filter_by(name=category_name).one()
    creator = getUserInfo(category.user_id)
    items = session.query(EquipmentItem).all()
    equipment = session.query(EquipmentItem).filter_by(name=item_name).first()
    # if 'username' not in login_session or creator.id !=
    # login_session['user_id']:
    if 'username' not in login_session:
        return render_template('publicEquip.html', creator=creator,
                               equipment=equipment, items=items, category_name=category.name)
    else:
        return render_template('equipment.html', creator=creator,
                               equipment=equipment, items=items, category_name=category.name)

# Create a new equipment in particular category
@app.route('/catalog/<category_name>/item/new/', methods=['GET', 'POST'])
def newEquip(category_name):
    if 'username' not in login_session:
        return redirect('/login')
    category = session.query(Category).filter_by(name=category_name).one()
    if request.method == 'POST':
        equip = EquipmentItem(name=request.form['name'], description=request.form['description'],
                              category_id=category.id, user_id=login_session['user_id'])
        session.add(equip)
        session.commit()
        flash('New Item %s Successfully Created' % (equip.name))
        return redirect(url_for('showItem', category_name=category_name))
    else:
        return render_template('newEquip.html', category_name=category_name)

# Edit an equipment in particular category
@app.route('/catalog/<equipment_name>/edit', methods=['GET', 'POST'])
def editEquip(equipment_name):
    if 'username' not in login_session:
        return redirect('/login')
    editedEquip = session.query(EquipmentItem).filter_by(
        name=equipment_name).first()
    category = session.query(Category).filter(
        Category.id == editedEquip.category_id).one()
    category_all = session.query(Category.name).all()
    '''if login_session['user_id'] != editedEquip.user_id:
        return "<script>function myFunction() {alert('You are not authorized to edit"
        " items to this category. Please create your own category in order"
        " to edit items.');}</script><body onload='myFunction()''>"'''
    if request.method == 'POST':
        if request.form['name']:
            editedEquip.name = request.form['name']
        if request.form['description']:
            editedEquip.description = request.form['description']
        if request.form['category_name']:
            convertCatId = session.query(Category).filter(
                Category.name == request.form['category_name']).one()
            editedEquip.category_id = convertCatId.id
        session.add(editedEquip)
        session.commit()
        flash('Equip Successfully Edited')
        return redirect(url_for('showItem', category_name=category.name))
    else:
        return render_template('editEquip.html', equipment_name=equipment_name, editedEquip=editedEquip, category=category, category_all=category_all)

# Delete an equipment in particular category
@app.route('/catalog/<equipment_name>/delete', methods=['GET', 'POST'])
def deleteEquip(equipment_name):
    if 'username' not in login_session:
        return redirect('/login')
    equipToDelete = session.query(
        EquipmentItem).filter_by(name=equipment_name).first()
    category = session.query(Category).filter(
        Category.id == equipToDelete.category_id).first()
    '''if login_session['user_id'] != equipToDelete.user_id:
        return "<script>function myFunction() {alert('You are not authorized to delete"
        " items to this equipment. Please create your own equipment in order"
        " to delete items.');}</script><body onload='myFunction()''>"'''
    if request.method == 'POST':
        session.delete(equipToDelete)
        session.commit()
        flash('Equip Successfully Deleted')
        return redirect(url_for('showItem', category_name=category.name))
    else:
        return render_template('deleteEquip.html', equipment_name=equipment_name, category=category, equipToDelete=equipToDelete)

# Disconnect based on provide
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            #del login_session['gplus_id']
            #del login_session['credentials']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showCategories'))
    else:
        flash("You were not logged in")
        return redirect(url_for('showCategories'))

if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)

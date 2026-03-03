from . import app, db
from .modules_db import Users
from flask import render_template, request, redirect, url_for, flash
from .forms import LoginForm, CreateUserForm
from .app_stock import *
from flask_login import LoginManager, login_user, login_required, logout_user

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "home"
@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

@app.route('/')
@app.route('/home', methods=["GET", "POST"])
def home():

    # This function loads the home page and validates the log in.    
    form = LoginForm()
    if form.validate_on_submit():
        if check_user(form.username.data, form.password.data , form.role.data):
            user = Users.query.filter_by(first_name=form.username.data).first()
            login_user(user)
            if form.role.data == "Employee":
                flash('You were successfully logged in')
                return redirect(url_for('stock'))  
            else: 
                flash('Welcome Manager!')
                return redirect(url_for('create'))
    return render_template('loginUser.html', title = 'Home', form = form)

@app.route('/create', methods=["GET", "POST"])
@login_required  # To enter for the first time comment this line "@login_required", access the create page and register a new user like:
def create():  # admin, admin, 123, 123. Then uncomment this and access login page using credentials you just created.
    
    # This function loads the create page and validates the creation of a new user.
    form = CreateUserForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(first_name=form.first_name.data).first()
        if user:
            flash('Something went wrong!')
            return redirect(url_for('create'))
        else:
            register_user(form.first_name.data, form.last_name.data, 
                          form.password.data, form.role.data)
            flash('New user has been created!')
            logout_user()
            return redirect(url_for('home'))
    return render_template('createAccount.html', title = 'Create Account', form = form)      

@app.route('/stock', methods=["GET", "POST"])
@login_required
def stock():
    
    # This function loads the stock menu page, and activates the function chosen by the user.
    if request.method == "POST":
        main_functions = {'Add': add, 'Update': update, 'Delete': delete}
        button_func = request.form['submit_button']

        if request.form['submit_button'] in main_functions:
            productName = request.form['product_name'].strip().capitalize()
            productPrice = request.form['product_price']
            productQuantity = request.form['product_quantity']  
            minimumQuantity = request.form['minimum_quantity']  
            result = main_functions[button_func](productName, productPrice, productQuantity, minimumQuantity)
            return render_template('stockInterface.html', display_result = result)
        else:
            return redirect(url_for(request.form['submit_button'].lower()))
    return render_template('stockInterface.html', title = 'StockMenu')
    
@app.route('/show', methods=["GET", "POST"])
@login_required
def show():

    # This function retrieves all products from the Products table.  
    # It then navigates to the stock menu or the home page, depending on the button chosen by the user.
    if request.method == "POST":
        return redirect(url_for(request.form['submit_button'].lower()))
    result = read()
    return render_template('showProducts.html', title = 'ShowProducts', showItem = result)

@app.route('/exit')
def exit():
    
    # This function returns to the home page.
    logout_user()
    return redirect(url_for('home'))
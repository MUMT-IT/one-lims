from . import auth_blueprint as auth
from app import db, login_manager
from flask_login import login_required, login_user,  logout_user, current_user
from flask import render_template, request, flash, redirect, url_for
from .forms import LoginForm, RegistrationForm
from .models import User


@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))


@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            email = request.form.get('email')
            password = request.form.get('password')
            existing_user = User.query.filter_by(email=email).first()
            if not existing_user:
                flash('The email is not registered. Please register the email.', 'danger')
                return redirect(url_for('auth.register'))
            else:
                if existing_user.check_password(password) and existing_user.is_active:
                    login_user(existing_user)
                    flash('You have logged in.', 'success')
                    return redirect(request.args.get('next') or url_for('main.index'))
                else:
                    flash('Wrong password or your account is not active.', 'danger')
        else:
            flash(form.errors, 'danger')
    return render_template('/auth/login.html', form=form)


@auth.route('/logout')
def logout():
    if current_user.is_authenticated:
        logout_user()
        flash('You have logged out.', 'success')
    return redirect(url_for('main.index'))


@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            firstname = request.form.get('firstname')
            lastname = request.form.get('lastname')
            license_id = request.form.get('license_id')
            email = request.form.get('email')
            password = request.form.get('password')
            existing_username = User.query.filter_by(email=email).first()
            if existing_username:
                flash('This email has been registered.', 'warning')
            else:
                user = User(firstname=firstname,
                            lastname=lastname,
                            email=email,
                            license_id=license_id,
                            password=password)
                db.session.add(user)
                db.session.commit()
                flash('The account has been registered. Please log in.')
                return redirect(url_for('auth.login'))
        else:
            flash(form.errors, 'danger')

    return render_template('/auth/register.html', form=form)

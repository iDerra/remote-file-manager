from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin_user = current_app.config.get('ADMIN_USERNAME')
        admin_pass = current_app.config.get('ADMIN_PASSWORD')
        
        if username and password and username == admin_user and password == admin_pass:
            session['logged_in'] = True
            return redirect(url_for('browse.browse_directory'))
        else:
            flash("Usuario o contraseña incorrectos.", "danger")

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash("Has cerrado sesión.", "info")
    return redirect(url_for('auth.login'))
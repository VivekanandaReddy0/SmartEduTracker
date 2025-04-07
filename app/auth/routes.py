from flask import Blueprint, render_template, url_for, flash, redirect, request, jsonify
from flask_login import login_user, current_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app.models import User, Student, Admin
from app.auth.forms import LoginForm, RegistrationForm
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import datetime

auth_bp = Blueprint('auth', __name__, url_prefix='/auth', template_folder='templates')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            
            # Create JWT token
            expiration = datetime.timedelta(hours=1)
            access_token = create_access_token(
                identity={'id': user.id, 'role': user.role},
                expires_delta=expiration
            )
            
            # Store token in session
            request.session = {'jwt_token': access_token}
            
            if next_page:
                return redirect(next_page)
            else:
                return redirect(url_for('dashboard.index'))
        else:
            flash('Login unsuccessful. Please check username and password.', 'danger')
    
    return render_template('login.html', title='Login', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = RegistrationForm()
    
    if form.validate_on_submit():
        # Create user
        user = User(
            username=form.username.data,
            email=form.email.data,
            role='student'  # Default role is student
        )
        user.set_password(form.password.data)
        
        # Create student profile
        student = Student(
            student_id=form.student_id.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            semester=form.semester.data,
            program=form.program.data
        )
        
        # Link student to user
        user.student = student
        
        # Save to database
        db.session.add(user)
        db.session.commit()
        
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html', title='Register', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# API routes for JWT authentication
@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
    
    user = User.query.filter_by(username=username).first()
    
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid username or password'}), 401
    
    # Create JWT token
    expiration = datetime.timedelta(hours=1)
    access_token = create_access_token(
        identity={'id': user.id, 'role': user.role},
        expires_delta=expiration
    )
    
    return jsonify({
        'token': access_token,
        'user_id': user.id,
        'role': user.role
    }), 200

@auth_bp.route('/api/verify_token', methods=['GET'])
@jwt_required()
def verify_token():
    current_user_id = get_jwt_identity().get('id')
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'user_id': user.id,
        'username': user.username,
        'role': user.role
    }), 200

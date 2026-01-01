from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message
from app import db, mail
from app.models import User
from app.forms import LoginForm, RegistrationForm, ForgotPasswordForm, ResetPasswordForm
import secrets
import requests

bp = Blueprint('auth', __name__, url_prefix='/auth')


def send_reset_email(user):
    """Send password reset email to user"""
    token = user.get_reset_token()
    reset_url = url_for('auth.reset_password', token=token, _external=True)
    
    msg = Message(
        'Password Reset Request - Dotar Drug Shop',
        recipients=[user.email]
    )
    msg.body = f'''Hello {user.full_name},

You requested a password reset for your Dotar Drug Shop account.

Click the link below to reset your password:
{reset_url}

This link will expire in 30 minutes.

If you did not request this, please ignore this email.

Best regards,
Dotar Drug Shop Team
'''
    msg.html = f'''
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #0d6efd; color: white; padding: 20px; text-align: center;">
            <h1 style="margin: 0;">Dotar Drug Shop</h1>
        </div>
        <div style="padding: 30px; background: #f8f9fa;">
            <h2>Password Reset Request</h2>
            <p>Hello <strong>{user.full_name}</strong>,</p>
            <p>You requested a password reset for your account.</p>
            <p style="text-align: center; margin: 30px 0;">
                <a href="{reset_url}" style="background: #0d6efd; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    Reset Password
                </a>
            </p>
            <p style="color: #666; font-size: 14px;">This link will expire in 30 minutes.</p>
            <p style="color: #666; font-size: 14px;">If you did not request this, please ignore this email.</p>
        </div>
        <div style="background: #e9ecef; padding: 15px; text-align: center; font-size: 12px; color: #666;">
            &copy; Dotar Drug Shop - Quality Healthcare, Quality Life
        </div>
    </div>
    '''
    
    try:
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f'Failed to send email: {e}')
        return False


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_staff():
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('patient.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password', 'error')
            return redirect(url_for('auth.login'))
        
        if not user.is_active:
            flash('Your account has been deactivated. Please contact admin.', 'error')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=True)
        flash(f'Welcome back, {user.full_name}!', 'success')
        
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        
        if user.is_staff():
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('patient.dashboard'))
    
    return render_template('auth/login.html', form=form)


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            full_name=form.full_name.data,
            phone=form.phone.data,
            role='patient'
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', form=form)


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))


@bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            if send_reset_email(user):
                flash('A password reset link has been sent to your email.', 'success')
            else:
                flash('Failed to send email. Please try again later.', 'error')
        else:
            flash('A password reset link has been sent to your email if it exists.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/forgot_password.html', form=form)


@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    user = User.verify_reset_token(token)
    if not user:
        flash('Invalid or expired reset link.', 'error')
        return redirect(url_for('auth.forgot_password'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset! You can now log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', form=form)


# Google OAuth Routes
@bp.route('/google/login')
def google_login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    google_client_id = current_app.config.get('GOOGLE_CLIENT_ID')
    if not google_client_id:
        flash('Google login is not configured.', 'error')
        return redirect(url_for('auth.login'))
    
    redirect_uri = url_for('auth.google_callback', _external=True)
    
    google_auth_url = (
        'https://accounts.google.com/o/oauth2/v2/auth?'
        f'client_id={google_client_id}&'
        f'redirect_uri={redirect_uri}&'
        'response_type=code&'
        'scope=openid%20email%20profile&'
        'access_type=offline&'
        'prompt=consent'
    )
    
    return redirect(google_auth_url)


@bp.route('/google/callback')
def google_callback():
    code = request.args.get('code')
    if not code:
        flash('Google login failed.', 'error')
        return redirect(url_for('auth.login'))
    
    google_client_id = current_app.config.get('GOOGLE_CLIENT_ID')
    google_client_secret = current_app.config.get('GOOGLE_CLIENT_SECRET')
    redirect_uri = url_for('auth.google_callback', _external=True)
    
    # Exchange code for tokens
    token_url = 'https://oauth2.googleapis.com/token'
    token_data = {
        'code': code,
        'client_id': google_client_id,
        'client_secret': google_client_secret,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code'
    }
    
    try:
        token_response = requests.post(token_url, data=token_data)
        token_json = token_response.json()
        
        if 'access_token' not in token_json:
            flash('Google login failed.', 'error')
            return redirect(url_for('auth.login'))
        
        access_token = token_json['access_token']
        
        # Get user info from Google
        userinfo_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
        headers = {'Authorization': f'Bearer {access_token}'}
        userinfo_response = requests.get(userinfo_url, headers=headers)
        userinfo = userinfo_response.json()
        
        google_id = userinfo.get('id')
        email = userinfo.get('email')
        name = userinfo.get('name')
        picture = userinfo.get('picture')
        
        if not email:
            flash('Could not get email from Google.', 'error')
            return redirect(url_for('auth.login'))
        
        # Check if user exists by Google ID
        user = User.query.filter_by(google_id=google_id).first()
        
        if not user:
            # Check if user exists by email
            user = User.query.filter_by(email=email).first()
            
            if user:
                # Link Google account to existing user
                user.google_id = google_id
                if picture:
                    user.profile_pic = picture
                db.session.commit()
            else:
                # Create new user
                username = email.split('@')[0]
                base_username = username
                counter = 1
                while User.query.filter_by(username=username).first():
                    username = f'{base_username}{counter}'
                    counter += 1
                
                user = User(
                    username=username,
                    email=email,
                    full_name=name or email.split('@')[0],
                    google_id=google_id,
                    profile_pic=picture,
                    role='patient'
                )
                db.session.add(user)
                db.session.commit()
        
        if not user.is_active:
            flash('Your account has been deactivated. Please contact admin.', 'error')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=True)
        flash(f'Welcome, {user.full_name}!', 'success')
        
        if user.is_staff():
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('patient.dashboard'))
        
    except Exception as e:
        current_app.logger.error(f'Google OAuth error: {e}')
        flash('Google login failed. Please try again.', 'error')
        return redirect(url_for('auth.login'))

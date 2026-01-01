from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
mail = Mail()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    from app.routes import auth, admin, patient, main
    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(patient.bp)
    
    with app.app_context():
        db.create_all()
        
        # Add new columns if they don't exist (for existing databases)
        from sqlalchemy import text, inspect
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('users')]
        
        if 'google_id' not in columns:
            try:
                db.session.execute(text('ALTER TABLE users ADD COLUMN google_id VARCHAR(100) UNIQUE'))
                db.session.commit()
            except Exception:
                db.session.rollback()
        
        if 'profile_pic' not in columns:
            try:
                db.session.execute(text('ALTER TABLE users ADD COLUMN profile_pic VARCHAR(500)'))
                db.session.commit()
            except Exception:
                db.session.rollback()
        
        # Add shop_logo column to shop_settings if it doesn't exist
        shop_columns = [col['name'] for col in inspector.get_columns('shop_settings')]
        if 'shop_logo' not in shop_columns:
            try:
                db.session.execute(text('ALTER TABLE shop_settings ADD COLUMN shop_logo VARCHAR(500)'))
                db.session.commit()
            except Exception:
                db.session.rollback()
        
        from app.models import User, ShopSettings
        if not User.query.filter_by(username='admin').first():
            admin_user = User(
                username='admin',
                email='admin@dotar.com',
                role='admin',
                full_name='System Administrator'
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
        
        if not ShopSettings.query.first():
            settings = ShopSettings()
            db.session.add(settings)
            db.session.commit()
    
    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        from app.models import Notification, ShopSettings
        from datetime import datetime
        
        result = {
            'unread_notifications': 0, 
            'now': datetime.now,
            'google_oauth_enabled': bool(app.config.get('GOOGLE_CLIENT_ID'))
        }
        
        if current_user.is_authenticated and hasattr(current_user, 'is_staff') and current_user.is_staff():
            unread_count = Notification.query.filter(
                Notification.for_role.in_(['staff', 'admin', 'nurse']),
                Notification.is_read == False
            ).count()
            result['unread_notifications'] = unread_count
        
        shop = ShopSettings.query.first()
        if shop:
            result['shop_settings'] = shop
        else:
            result['shop_settings'] = ShopSettings()
        
        return result
    
    @app.template_filter('youtube_embed')
    def youtube_embed_filter(url, autoplay=True):
        """Convert YouTube URL to embed format with autoplay"""
        import re
        if not url:
            return url
        
        video_id = None
        
        # Handle youtu.be/VIDEO_ID format
        match = re.search(r'youtu\.be/([a-zA-Z0-9_-]+)', url)
        if match:
            video_id = match.group(1)
        
        # Handle youtube.com/watch?v=VIDEO_ID format
        if not video_id:
            match = re.search(r'youtube\.com/watch\?v=([a-zA-Z0-9_-]+)', url)
            if match:
                video_id = match.group(1)
        
        # Handle youtube.com/embed/VIDEO_ID format
        if not video_id:
            match = re.search(r'youtube\.com/embed/([a-zA-Z0-9_-]+)', url)
            if match:
                video_id = match.group(1)
        
        if video_id:
            params = 'autoplay=1&mute=1&loop=1&playlist=' + video_id if autoplay else ''
            return f'https://www.youtube.com/embed/{video_id}?{params}'
        
        return url
    
    return app

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login_manager

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=True)
    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), nullable=False, default='patient')  # admin, nurse, patient
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # OAuth fields
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    profile_pic = db.Column(db.String(500), nullable=True)
    
    consultations = db.relationship('Consultation', backref='patient', lazy='dynamic', foreign_keys='Consultation.patient_id')
    responses = db.relationship('Consultation', backref='responder', lazy='dynamic', foreign_keys='Consultation.responder_id')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_nurse(self):
        return self.role == 'nurse'
    
    def is_staff(self):
        return self.role in ['admin', 'nurse']
    
    def get_reset_token(self, expires_sec=1800):
        from itsdangerous import URLSafeTimedSerializer
        from flask import current_app
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id}, salt='password-reset-salt')
    
    @staticmethod
    def verify_reset_token(token, expires_sec=1800):
        from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
        from flask import current_app
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, salt='password-reset-salt', max_age=expires_sec)
        except (SignatureExpired, BadSignature):
            return None
        return User.query.get(data['user_id'])

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))


class Drug(db.Model):
    __tablename__ = 'drugs'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, index=True)
    generic_name = db.Column(db.String(150))
    description = db.Column(db.Text)
    category = db.Column(db.String(100))
    dosage_form = db.Column(db.String(50))  # tablet, capsule, syrup, injection
    strength = db.Column(db.String(50))
    unit_price = db.Column(db.Float, nullable=False)
    quantity_in_stock = db.Column(db.Integer, default=0)
    reorder_level = db.Column(db.Integer, default=10)
    expiry_date = db.Column(db.Date)
    manufacturer = db.Column(db.String(150))
    requires_prescription = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    sales = db.relationship('Sale', backref='drug', lazy='dynamic')


class Consultation(db.Model):
    __tablename__ = 'consultations'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    symptoms = db.Column(db.Text, nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, resolved
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    response = db.Column(db.Text)
    responder_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    recommended_drugs = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime)


class Sale(db.Model):
    __tablename__ = 'sales'
    
    id = db.Column(db.Integer, primary_key=True)
    drug_id = db.Column(db.Integer, db.ForeignKey('drugs.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    customer_name = db.Column(db.String(150))
    customer_phone = db.Column(db.String(20))
    payment_method = db.Column(db.String(50), default='cash')  # cash, card, mobile_money
    sold_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    seller = db.relationship('User', backref='sales')


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50))  # order, consultation, stock, payment
    reference_id = db.Column(db.Integer)
    reference_type = db.Column(db.String(50))  # order, consultation
    is_read = db.Column(db.Boolean, default=False)
    for_role = db.Column(db.String(20), default='admin')  # admin, nurse, patient
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='notifications')


class ShopSettings(db.Model):
    __tablename__ = 'shop_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    shop_name = db.Column(db.String(200), default='Parl Drug Shop')
    shop_tagline = db.Column(db.String(300), default='Quality Healthcare, Quality Life')
    shop_email = db.Column(db.String(120), default='info@parldrugshop.com')
    shop_phone = db.Column(db.String(50), default='+256 700 000 000')
    shop_address = db.Column(db.Text, default='Kampala, Uganda')
    shop_hours = db.Column(db.String(200), default='Monday - Sunday, 8:00 AM - 10:00 PM')
    currency = db.Column(db.String(10), default='UGX')
    delivery_fee = db.Column(db.Float, default=5000)
    min_order_amount = db.Column(db.Float, default=0)
    about_text = db.Column(db.Text)
    mission_text = db.Column(db.Text)
    vision_text = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))


class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    drug_id = db.Column(db.Integer, db.ForeignKey('drugs.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    
    disease_condition = db.Column(db.String(200), nullable=False)
    condition_severity = db.Column(db.String(20), default='normal')  # mild, normal, severe, critical
    symptoms_description = db.Column(db.Text)
    
    delivery_address = db.Column(db.String(300), nullable=False)
    delivery_district = db.Column(db.String(100))
    delivery_sector = db.Column(db.String(100))
    delivery_cell = db.Column(db.String(100))
    location_landmark = db.Column(db.String(200))
    delivery_phone = db.Column(db.String(20), nullable=False)
    delivery_notes = db.Column(db.Text)
    
    order_status = db.Column(db.String(20), default='pending')  # pending, confirmed, processing, out_for_delivery, delivered, cancelled
    payment_status = db.Column(db.String(20), default='pending')  # pending, paid
    payment_amount_received = db.Column(db.Float, default=0)
    payment_received_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    payment_received_at = db.Column(db.DateTime)
    
    processed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    admin_notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    
    patient = db.relationship('User', foreign_keys=[patient_id], backref='orders')
    drug = db.relationship('Drug', backref='orders')
    processor = db.relationship('User', foreign_keys=[processed_by])
    payment_receiver = db.relationship('User', foreign_keys=[payment_received_by])


class Advertisement(db.Model):
    __tablename__ = 'advertisements'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    media_type = db.Column(db.String(20), nullable=False)  # image, video
    media_url = db.Column(db.String(500), nullable=False)  # file path or external URL
    link_url = db.Column(db.String(500))  # optional link when clicked
    display_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    creator = db.relationship('User', backref='advertisements')

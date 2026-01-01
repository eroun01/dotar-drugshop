from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models import Drug, Consultation, Order, Notification, Sale
from app.forms import ConsultationForm, OrderForm, PatientProfileForm
from app.uganda_locations import get_subcounties, get_villages, UGANDA_LOCATIONS

bp = Blueprint('patient', __name__, url_prefix='/patient')

def patient_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.is_staff():
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/dashboard')
@login_required
@patient_required
def dashboard():
    my_consultations = Consultation.query.filter_by(patient_id=current_user.id).order_by(Consultation.created_at.desc()).limit(5).all()
    pending_count = Consultation.query.filter_by(patient_id=current_user.id, status='pending').count()
    resolved_count = Consultation.query.filter_by(patient_id=current_user.id, status='resolved').count()
    
    return render_template('patient/dashboard.html',
        my_consultations=my_consultations,
        pending_count=pending_count,
        resolved_count=resolved_count
    )

@bp.route('/drugs')
@login_required
@patient_required
def browse_drugs():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    
    query = Drug.query.filter_by(is_active=True)
    
    if search:
        query = query.filter(Drug.name.ilike(f'%{search}%'))
    if category:
        query = query.filter_by(category=category)
    
    drugs = query.order_by(Drug.name).paginate(page=page, per_page=12, error_out=False)
    
    categories = db.session.query(Drug.category).distinct().all()
    categories = [c[0] for c in categories if c[0]]
    
    return render_template('patient/drugs.html', drugs=drugs, search=search, category=category, categories=categories)

@bp.route('/consult', methods=['GET', 'POST'])
@login_required
@patient_required
def consult():
    form = ConsultationForm()
    
    if form.validate_on_submit():
        consultation = Consultation(
            patient_id=current_user.id,
            subject=form.subject.data,
            symptoms=form.symptoms.data,
            message=form.message.data,
            priority=form.priority.data
        )
        db.session.add(consultation)
        db.session.commit()
        
        notification = Notification(
            title='New Consultation',
            message=f'New consultation from {current_user.full_name}: {form.subject.data}',
            notification_type='consultation',
            reference_id=consultation.id,
            reference_type='consultation',
            for_role='staff'
        )
        db.session.add(notification)
        db.session.commit()
        
        flash('Your consultation has been submitted. A nurse will respond soon.', 'success')
        return redirect(url_for('patient.my_consultations'))
    
    return render_template('patient/consult.html', form=form)

@bp.route('/consultations')
@login_required
@patient_required
def my_consultations():
    page = request.args.get('page', 1, type=int)
    consultations = Consultation.query.filter_by(patient_id=current_user.id).order_by(Consultation.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    return render_template('patient/consultations.html', consultations=consultations)

@bp.route('/consultations/<int:id>')
@login_required
@patient_required
def view_consultation(id):
    consultation = Consultation.query.filter_by(id=id, patient_id=current_user.id).first_or_404()
    return render_template('patient/consultation_detail.html', consultation=consultation)

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
@patient_required
def profile():
    """User profile page with password change functionality."""
    form = PatientProfileForm(obj=current_user)
    
    if form.validate_on_submit():
        if form.current_password.data:
            if not current_user.check_password(form.current_password.data):
                flash('Current password is incorrect.', 'error')
                return redirect(url_for('patient.profile'))
            
            if form.new_password.data:
                current_user.set_password(form.new_password.data)
                flash('Password changed successfully!', 'success')
        
        current_user.full_name = form.full_name.data
        current_user.email = form.email.data
        current_user.phone = form.phone.data
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('patient.profile'))
    
    order_count = Order.query.filter_by(patient_id=current_user.id).count()
    consultation_count = Consultation.query.filter_by(patient_id=current_user.id).count()
    
    return render_template('patient/profile.html', form=form, order_count=order_count, consultation_count=consultation_count)


@bp.route('/order', methods=['GET', 'POST'])
@bp.route('/order/<int:drug_id>', methods=['GET', 'POST'])
@login_required
@patient_required
def order(drug_id=None):
    form = OrderForm()
    drugs = Drug.query.filter_by(is_active=True).filter(Drug.quantity_in_stock > 0).all()
    form.drug_id.choices = [(0, 'Select Medicine')] + [(d.id, f"{d.name} ({d.strength or 'N/A'}) - UGX {d.unit_price:,.0f}") for d in drugs]
    
    if drug_id:
        form.drug_id.data = drug_id
    
    if form.validate_on_submit():
        drug = Drug.query.get(form.drug_id.data)
        if not drug:
            flash('Invalid medicine selected.', 'error')
            return redirect(url_for('patient.order'))
        
        if drug.quantity_in_stock < form.quantity.data:
            flash(f'Insufficient stock. Only {drug.quantity_in_stock} available.', 'error')
            return redirect(url_for('patient.order'))
        
        total_amount = drug.unit_price * form.quantity.data
        
        order = Order(
            patient_id=current_user.id,
            drug_id=drug.id,
            quantity=form.quantity.data,
            unit_price=drug.unit_price,
            total_amount=total_amount,
            disease_condition=form.disease_condition.data,
            condition_severity=form.condition_severity.data,
            symptoms_description=form.symptoms_description.data,
            delivery_address=form.delivery_address.data,
            delivery_district=form.delivery_district.data,
            delivery_sector=form.delivery_sector.data,
            delivery_cell=form.delivery_cell.data,
            location_landmark=form.location_landmark.data,
            delivery_phone=form.delivery_phone.data,
            delivery_notes=form.delivery_notes.data
        )
        
        db.session.add(order)
        db.session.commit()
        
        sale = Sale(
            drug_id=drug.id,
            quantity=form.quantity.data,
            unit_price=drug.unit_price,
            total_amount=total_amount,
            customer_name=current_user.full_name,
            customer_phone=form.delivery_phone.data,
            payment_method='cash_on_delivery',
            sold_by=1,
            notes=f'Order #{order.id} - {order.disease_condition} - Delivery to {order.delivery_address}'
        )
        db.session.add(sale)
        
        notification = Notification(
            title='New Medicine Order',
            message=f'New order from {current_user.full_name}: {drug.name} x{form.quantity.data} - UGX {total_amount:,.0f}',
            notification_type='order',
            reference_id=order.id,
            reference_type='order',
            for_role='staff'
        )
        db.session.add(notification)
        
        if order.condition_severity in ['severe', 'critical']:
            urgent_notification = Notification(
                title=f'URGENT: {order.condition_severity.upper()} Order',
                message=f'Priority delivery needed for {current_user.full_name}: {drug.name} - {order.disease_condition}',
                notification_type='urgent',
                reference_id=order.id,
                reference_type='order',
                for_role='staff'
            )
            db.session.add(urgent_notification)
        
        drug.quantity_in_stock -= form.quantity.data
        
        db.session.commit()
        
        flash(f'Order placed successfully! Total: UGX {total_amount:,.0f}. Pay on delivery.', 'success')
        return redirect(url_for('patient.my_orders'))
    
    if current_user.phone:
        form.delivery_phone.data = form.delivery_phone.data or current_user.phone
    
    return render_template('patient/order.html', form=form)


@bp.route('/orders')
@login_required
@patient_required
def my_orders():
    page = request.args.get('page', 1, type=int)
    orders = Order.query.filter_by(patient_id=current_user.id).order_by(Order.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    return render_template('patient/orders.html', orders=orders)


@bp.route('/orders/<int:id>')
@login_required
@patient_required
def view_order(id):
    order = Order.query.filter_by(id=id, patient_id=current_user.id).first_or_404()
    return render_template('patient/order_detail.html', order=order)


@bp.route('/api/subcounties/<district>')
@login_required
def get_district_subcounties(district):
    """API endpoint to fetch subcounties for a selected district"""
    district_name = district.replace('_', ' ').replace('-', ' ').title()
    
    for key in UGANDA_LOCATIONS.keys():
        if key.lower().replace(' ', '_').replace('-', '_') == district.lower():
            district_name = key
            break
    
    subcounties = get_subcounties(district_name)
    return jsonify({'subcounties': subcounties})


@bp.route('/api/villages/<district>')
@login_required
def get_district_villages(district):
    """API endpoint to fetch villages/parishes for a selected district"""
    district_name = district.replace('_', ' ').replace('-', ' ').title()
    
    for key in UGANDA_LOCATIONS.keys():
        if key.lower().replace(' ', '_').replace('-', '_') == district.lower():
            district_name = key
            break
    
    villages = get_villages(district_name)
    return jsonify({'villages': villages})

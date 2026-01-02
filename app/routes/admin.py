from flask import Blueprint, render_template, redirect, url_for, flash, request, Response, make_response, current_app
import csv
import io
import os
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, timedelta, date
from sqlalchemy import func
from app import db
from app.models import User, Drug, Consultation, Sale, Order, Notification, ShopSettings, Advertisement
from app.forms import DrugForm, ConsultationResponseForm, SaleForm, StaffRegistrationForm, OrderStatusForm, ShopSettingsForm, AdminProfileForm, AdvertisementForm

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp4', 'webm', 'mov'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

bp = Blueprint('admin', __name__, url_prefix='/admin')

def staff_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_staff():
            flash('Access denied. Staff only.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Access denied. Admin only.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/dashboard')
@login_required
@staff_required
def dashboard():
    total_drugs = Drug.query.filter_by(is_active=True).count()
    low_stock_drugs = Drug.query.filter(Drug.quantity_in_stock <= Drug.reorder_level, Drug.is_active == True).count()
    pending_consultations = Consultation.query.filter_by(status='pending').count()
    
    today = datetime.utcnow().date()
    today_sales = db.session.query(func.sum(Sale.total_amount)).filter(
        func.date(Sale.created_at) == today
    ).scalar() or 0
    
    month_start = today.replace(day=1)
    monthly_sales = db.session.query(func.sum(Sale.total_amount)).filter(
        Sale.created_at >= month_start
    ).scalar() or 0
    
    recent_consultations = Consultation.query.order_by(Consultation.created_at.desc()).limit(5).all()
    recent_sales = Sale.query.order_by(Sale.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
        total_drugs=total_drugs,
        low_stock_drugs=low_stock_drugs,
        pending_consultations=pending_consultations,
        today_sales=today_sales,
        monthly_sales=monthly_sales,
        recent_consultations=recent_consultations,
        recent_sales=recent_sales
    )

# Drug Management
@bp.route('/drugs')
@login_required
@staff_required
def drugs():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    
    query = Drug.query.filter_by(is_active=True)
    if search:
        query = query.filter(Drug.name.ilike(f'%{search}%'))
    
    drugs = query.order_by(Drug.name).paginate(page=page, per_page=10, error_out=False)
    return render_template('admin/drugs.html', drugs=drugs, search=search)

@bp.route('/drugs/add', methods=['GET', 'POST'])
@login_required
@staff_required
def add_drug():
    form = DrugForm()
    if form.validate_on_submit():
        drug = Drug(
            name=form.name.data,
            generic_name=form.generic_name.data,
            description=form.description.data,
            category=form.category.data,
            dosage_form=form.dosage_form.data,
            strength=form.strength.data,
            unit_price=form.unit_price.data,
            quantity_in_stock=form.quantity_in_stock.data,
            reorder_level=form.reorder_level.data or 10,
            expiry_date=form.expiry_date.data,
            manufacturer=form.manufacturer.data,
            requires_prescription=form.requires_prescription.data
        )
        db.session.add(drug)
        db.session.commit()
        flash('Drug added successfully!', 'success')
        return redirect(url_for('admin.drugs'))
    
    return render_template('admin/drug_form.html', form=form, title='Add New Drug')

@bp.route('/drugs/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@staff_required
def edit_drug(id):
    drug = Drug.query.get_or_404(id)
    form = DrugForm(obj=drug)
    
    if form.validate_on_submit():
        drug.name = form.name.data
        drug.generic_name = form.generic_name.data
        drug.description = form.description.data
        drug.category = form.category.data
        drug.dosage_form = form.dosage_form.data
        drug.strength = form.strength.data
        drug.unit_price = form.unit_price.data
        drug.quantity_in_stock = form.quantity_in_stock.data
        drug.reorder_level = form.reorder_level.data
        drug.expiry_date = form.expiry_date.data
        drug.manufacturer = form.manufacturer.data
        drug.requires_prescription = form.requires_prescription.data
        db.session.commit()
        flash('Drug updated successfully!', 'success')
        return redirect(url_for('admin.drugs'))
    
    return render_template('admin/drug_form.html', form=form, title='Edit Drug', drug=drug)

@bp.route('/drugs/delete/<int:id>', methods=['POST'])
@login_required
@staff_required
def delete_drug(id):
    drug = Drug.query.get_or_404(id)
    drug.is_active = False
    db.session.commit()
    flash('Drug deleted successfully!', 'success')
    return redirect(url_for('admin.drugs'))

# Consultations Management
@bp.route('/consultations')
@login_required
@staff_required
def consultations():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    
    query = Consultation.query
    if status:
        query = query.filter_by(status=status)
    
    consultations = query.order_by(Consultation.created_at.desc()).paginate(page=page, per_page=10, error_out=False)
    return render_template('admin/consultations.html', consultations=consultations, status=status)

@bp.route('/consultations/<int:id>', methods=['GET', 'POST'])
@login_required
@staff_required
def view_consultation(id):
    consultation = Consultation.query.get_or_404(id)
    form = ConsultationResponseForm()
    
    if form.validate_on_submit():
        consultation.response = form.response.data
        consultation.recommended_drugs = form.recommended_drugs.data
        consultation.status = form.status.data
        consultation.responder_id = current_user.id
        consultation.responded_at = datetime.utcnow()
        db.session.commit()
        flash('Response sent successfully!', 'success')
        return redirect(url_for('admin.consultations'))
    
    if consultation.response:
        form.response.data = consultation.response
        form.recommended_drugs.data = consultation.recommended_drugs
        form.status.data = consultation.status
    
    return render_template('admin/consultation_detail.html', consultation=consultation, form=form)

# Sales Management
@bp.route('/sales')
@login_required
@staff_required
def sales():
    page = request.args.get('page', 1, type=int)
    date_filter = request.args.get('date', '')
    
    query = Sale.query
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(func.date(Sale.created_at) == filter_date)
        except ValueError:
            pass
    
    sales = query.order_by(Sale.created_at.desc()).paginate(page=page, per_page=15, error_out=False)
    
    total_amount = db.session.query(func.sum(Sale.total_amount)).scalar() or 0
    
    return render_template('admin/sales.html', sales=sales, date_filter=date_filter, total_amount=total_amount)

@bp.route('/sales/new', methods=['GET', 'POST'])
@login_required
@staff_required
def new_sale():
    form = SaleForm()
    drugs = Drug.query.filter_by(is_active=True).filter(Drug.quantity_in_stock > 0).all()
    form.drug_id.choices = [(0, 'Select Drug')] + [(d.id, f"{d.name} ({d.strength}) - UGX {d.unit_price:,.0f} - Stock: {d.quantity_in_stock}") for d in drugs]
    
    if form.validate_on_submit():
        drug = Drug.query.get(form.drug_id.data)
        if not drug:
            flash('Invalid drug selected.', 'error')
            return redirect(url_for('admin.new_sale'))
        
        if drug.quantity_in_stock < form.quantity.data:
            flash(f'Insufficient stock. Only {drug.quantity_in_stock} available.', 'error')
            return redirect(url_for('admin.new_sale'))
        
        total_amount = drug.unit_price * form.quantity.data
        
        sale = Sale(
            drug_id=drug.id,
            quantity=form.quantity.data,
            unit_price=drug.unit_price,
            total_amount=total_amount,
            customer_name=form.customer_name.data,
            customer_phone=form.customer_phone.data,
            payment_method=form.payment_method.data,
            sold_by=current_user.id,
            notes=form.notes.data
        )
        
        drug.quantity_in_stock -= form.quantity.data
        
        db.session.add(sale)
        db.session.commit()
        flash(f'Sale recorded! Total: UGX {total_amount:,.0f}', 'success')
        return redirect(url_for('admin.sales'))
    
    return render_template('admin/sale_form.html', form=form)

# Staff Management (Admin only)
@bp.route('/staff')
@login_required
@admin_required
def staff():
    staff_members = User.query.filter(User.role.in_(['admin', 'nurse'])).all()
    return render_template('admin/staff.html', staff_members=staff_members)

@bp.route('/staff/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_staff():
    form = StaffRegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            full_name=form.full_name.data,
            phone=form.phone.data,
            role=form.role.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Staff member added successfully!', 'success')
        return redirect(url_for('admin.staff'))
    
    return render_template('admin/staff_form.html', form=form)

@bp.route('/patients')
@login_required
@staff_required
def patients():
    page = request.args.get('page', 1, type=int)
    patients = User.query.filter_by(role='patient').order_by(User.created_at.desc()).paginate(page=page, per_page=15, error_out=False)
    return render_template('admin/patients.html', patients=patients)

# Reports
@bp.route('/reports')
@login_required
@staff_required
def reports():
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    month_start = today.replace(day=1)
    
    daily_sales = db.session.query(
        func.date(Sale.created_at).label('date'),
        func.sum(Sale.total_amount).label('total')
    ).filter(Sale.created_at >= week_ago).group_by(func.date(Sale.created_at)).all()
    
    top_drugs = db.session.query(
        Drug.name,
        func.sum(Sale.quantity).label('total_sold'),
        func.sum(Sale.total_amount).label('revenue')
    ).join(Sale).group_by(Drug.id).order_by(func.sum(Sale.quantity).desc()).limit(10).all()
    
    total_patients = User.query.filter_by(role='patient').count()
    total_consultations = Consultation.query.count()
    resolved_consultations = Consultation.query.filter_by(status='resolved').count()
    
    return render_template('admin/reports.html',
        daily_sales=daily_sales,
        top_drugs=top_drugs,
        total_patients=total_patients,
        total_consultations=total_consultations,
        resolved_consultations=resolved_consultations
    )


@bp.route('/orders')
@login_required
@staff_required
def orders():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    payment = request.args.get('payment', '')
    severity = request.args.get('severity', '')
    
    query = Order.query
    if status:
        query = query.filter_by(order_status=status)
    if payment:
        query = query.filter_by(payment_status=payment)
    if severity:
        query = query.filter_by(condition_severity=severity)
    
    orders = query.order_by(Order.created_at.desc()).paginate(page=page, per_page=15, error_out=False)
    
    pending_orders = Order.query.filter_by(order_status='pending').count()
    unpaid_orders = Order.query.filter(Order.order_status == 'delivered', Order.payment_status == 'pending').count()
    total_revenue = db.session.query(func.sum(Order.payment_amount_received)).filter(Order.payment_status == 'paid').scalar() or 0
    
    return render_template('admin/orders.html', 
        orders=orders, 
        status=status, 
        payment=payment,
        severity=severity,
        pending_orders=pending_orders,
        unpaid_orders=unpaid_orders,
        total_revenue=total_revenue
    )


@bp.route('/orders/<int:id>', methods=['GET', 'POST'])
@login_required
@staff_required
def view_order(id):
    order = Order.query.get_or_404(id)
    form = OrderStatusForm()
    
    if form.validate_on_submit():
        old_status = order.order_status
        order.order_status = form.order_status.data
        order.payment_status = form.payment_status.data
        order.admin_notes = form.admin_notes.data
        order.processed_by = current_user.id
        
        if form.order_status.data == 'confirmed' and old_status == 'pending':
            order.confirmed_at = datetime.utcnow()
            drug = Drug.query.get(order.drug_id)
            if drug and drug.quantity_in_stock >= order.quantity:
                drug.quantity_in_stock -= order.quantity
        
        if form.order_status.data == 'delivered' and old_status != 'delivered':
            order.delivered_at = datetime.utcnow()
        
        if form.payment_status.data == 'paid' and order.payment_status != 'paid':
            order.payment_amount_received = form.payment_amount_received.data or order.total_amount
            order.payment_received_by = current_user.id
            order.payment_received_at = datetime.utcnow()
        
        db.session.commit()
        flash('Order updated successfully!', 'success')
        return redirect(url_for('admin.orders'))
    
    form.order_status.data = order.order_status
    form.payment_status.data = order.payment_status
    form.payment_amount_received.data = order.payment_amount_received or order.total_amount
    form.admin_notes.data = order.admin_notes
    
    return render_template('admin/order_detail.html', order=order, form=form)


@bp.route('/orders/<int:id>/cancel', methods=['POST'])
@login_required
@staff_required
def cancel_order(id):
    order = Order.query.get_or_404(id)
    
    if order.order_status in ['delivered', 'cancelled']:
        flash('Cannot cancel this order.', 'error')
        return redirect(url_for('admin.view_order', id=id))
    
    if order.order_status == 'confirmed':
        drug = Drug.query.get(order.drug_id)
        if drug:
            drug.quantity_in_stock += order.quantity
    
    order.order_status = 'cancelled'
    order.processed_by = current_user.id
    db.session.commit()
    
    flash('Order cancelled successfully.', 'success')
    return redirect(url_for('admin.orders'))


@bp.route('/notifications')
@login_required
@staff_required
def notifications():
    page = request.args.get('page', 1, type=int)
    notifications = Notification.query.filter(
        Notification.for_role.in_(['staff', 'admin', 'nurse'])
    ).order_by(Notification.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/notifications.html', notifications=notifications)


@bp.route('/notifications/mark-read/<int:id>')
@login_required
@staff_required
def mark_notification_read(id):
    notification = Notification.query.get_or_404(id)
    notification.is_read = True
    db.session.commit()
    
    if notification.reference_type == 'order' and notification.reference_id:
        return redirect(url_for('admin.view_order', id=notification.reference_id))
    elif notification.reference_type == 'consultation' and notification.reference_id:
        return redirect(url_for('admin.view_consultation', id=notification.reference_id))
    
    return redirect(url_for('admin.notifications'))


@bp.route('/notifications/mark-all-read')
@login_required
@staff_required
def mark_all_notifications_read():
    Notification.query.filter(
        Notification.for_role.in_(['staff', 'admin', 'nurse']),
        Notification.is_read == False
    ).update({'is_read': True})
    db.session.commit()
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('admin.notifications'))


@bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    settings = ShopSettings.query.first()
    if not settings:
        settings = ShopSettings()
        db.session.add(settings)
        db.session.commit()
    
    form = ShopSettingsForm(obj=settings)
    
    if form.validate_on_submit():
        if form.shop_logo.data:
            file = form.shop_logo.data
            if file and allowed_file(file.filename):
                import base64
                file_data = file.read()
                file_ext = file.filename.rsplit('.', 1)[1].lower()
                mime_type = f'image/{file_ext}' if file_ext != 'jpg' else 'image/jpeg'
                base64_data = base64.b64encode(file_data).decode('utf-8')
                settings.shop_logo = f'data:{mime_type};base64,{base64_data}'
        
        settings.shop_name = form.shop_name.data
        settings.shop_tagline = form.shop_tagline.data
        settings.shop_email = form.shop_email.data
        settings.shop_phone = form.shop_phone.data
        settings.shop_address = form.shop_address.data
        settings.shop_hours = form.shop_hours.data
        settings.currency = form.currency.data
        settings.delivery_fee = form.delivery_fee.data
        settings.min_order_amount = form.min_order_amount.data
        settings.about_text = form.about_text.data
        settings.mission_text = form.mission_text.data
        settings.vision_text = form.vision_text.data
        settings.updated_by = current_user.id
        db.session.commit()
        flash('Shop settings updated successfully!', 'success')
        return redirect(url_for('admin.settings'))
    
    return render_template('admin/settings.html', form=form, settings=settings)


@bp.route('/settings/remove-logo', methods=['POST'])
@login_required
@admin_required
def remove_logo():
    settings = ShopSettings.query.first()
    if settings and settings.shop_logo:
        settings.shop_logo = None
        settings.updated_by = current_user.id
        db.session.commit()
        flash('Shop logo removed successfully!', 'success')
    return redirect(url_for('admin.settings'))


@bp.route('/profile', methods=['GET', 'POST'])
@login_required
@staff_required
def profile():
    form = AdminProfileForm(obj=current_user)
    
    if form.validate_on_submit():
        if form.current_password.data:
            if not current_user.check_password(form.current_password.data):
                flash('Current password is incorrect.', 'error')
                return redirect(url_for('admin.profile'))
            
            if form.new_password.data:
                current_user.set_password(form.new_password.data)
        
        current_user.full_name = form.full_name.data
        current_user.email = form.email.data
        current_user.phone = form.phone.data
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('admin.profile'))
    
    return render_template('admin/profile.html', form=form)


# ============ EXPORT FUNCTIONS ============

@bp.route('/export/drugs')
@login_required
@staff_required
def export_drugs():
    drugs = Drug.query.filter_by(is_active=True).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['ID', 'Name', 'Generic Name', 'Category', 'Dosage Form', 'Strength', 
                     'Unit Price (UGX)', 'Quantity in Stock', 'Reorder Level', 'Expiry Date', 
                     'Manufacturer', 'Requires Prescription', 'Created At'])
    
    for drug in drugs:
        writer.writerow([
            drug.id,
            drug.name,
            drug.generic_name or '',
            drug.category or '',
            drug.dosage_form or '',
            drug.strength or '',
            drug.unit_price,
            drug.quantity_in_stock,
            drug.reorder_level,
            drug.expiry_date.strftime('%Y-%m-%d') if drug.expiry_date else '',
            drug.manufacturer or '',
            'Yes' if drug.requires_prescription else 'No',
            drug.created_at.strftime('%Y-%m-%d %H:%M')
        ])
    
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=drugs_export_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
    return response


@bp.route('/export/sales')
@login_required
@staff_required
def export_sales():
    date_from = request.args.get('from', '')
    date_to = request.args.get('to', '')
    
    query = Sale.query
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Sale.created_at >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d')
            query = query.filter(Sale.created_at <= to_date)
        except ValueError:
            pass
    
    sales = query.order_by(Sale.created_at.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['ID', 'Drug Name', 'Quantity', 'Unit Price (UGX)', 'Total Amount (UGX)', 
                     'Customer Name', 'Customer Phone', 'Payment Method', 'Sold By', 'Notes', 'Date'])
    
    for sale in sales:
        writer.writerow([
            sale.id,
            sale.drug.name,
            sale.quantity,
            sale.unit_price,
            sale.total_amount,
            sale.customer_name or 'Walk-in',
            sale.customer_phone or '',
            sale.payment_method,
            sale.seller.full_name if sale.seller else '',
            sale.notes or '',
            sale.created_at.strftime('%Y-%m-%d %H:%M')
        ])
    
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=sales_export_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
    return response


@bp.route('/export/customers')
@login_required
@staff_required
def export_customers():
    patients = User.query.filter_by(role='patient').all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['ID', 'Username', 'Full Name', 'Email', 'Phone', 'Status', 'Registered Date'])
    
    for patient in patients:
        writer.writerow([
            patient.id,
            patient.username,
            patient.full_name,
            patient.email,
            patient.phone or '',
            'Active' if patient.is_active else 'Inactive',
            patient.created_at.strftime('%Y-%m-%d %H:%M')
        ])
    
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=customers_export_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
    return response


@bp.route('/export/orders')
@login_required
@staff_required
def export_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['Order ID', 'Patient Name', 'Patient Phone', 'Drug Name', 'Quantity', 
                     'Unit Price (UGX)', 'Total (UGX)', 'Disease/Condition', 'Severity',
                     'Delivery Address', 'District', 'Order Status', 'Payment Status', 'Order Date'])
    
    for order in orders:
        writer.writerow([
            order.id,
            order.patient.full_name,
            order.delivery_phone,
            order.drug.name,
            order.quantity,
            order.unit_price,
            order.total_amount,
            order.disease_condition,
            order.condition_severity,
            order.delivery_address,
            order.delivery_district or '',
            order.order_status,
            order.payment_status,
            order.created_at.strftime('%Y-%m-%d %H:%M')
        ])
    
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=orders_export_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
    return response


# ============ IMPORT FUNCTIONS ============

@bp.route('/import/drugs', methods=['GET', 'POST'])
@login_required
@admin_required
def import_drugs():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected.', 'error')
            return redirect(url_for('admin.import_drugs'))
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(url_for('admin.import_drugs'))
        
        if not file.filename.endswith('.csv'):
            flash('Please upload a CSV file.', 'error')
            return redirect(url_for('admin.import_drugs'))
        
        try:
            content = file.stream.read().decode('utf-8').replace('\r\n', '\n').replace('\r', '\n')
            stream = io.StringIO(content, newline='')
            reader = csv.DictReader(stream)
            
            imported = 0
            for row in reader:
                drug = Drug(
                    name=row.get('Name', row.get('name', '')),
                    generic_name=row.get('Generic Name', row.get('generic_name', '')),
                    category=row.get('Category', row.get('category', '')),
                    dosage_form=row.get('Dosage Form', row.get('dosage_form', '')),
                    strength=row.get('Strength', row.get('strength', '')),
                    unit_price=float(row.get('Unit Price (UGX)', row.get('unit_price', 0)) or 0),
                    quantity_in_stock=int(row.get('Quantity in Stock', row.get('quantity_in_stock', 0)) or 0),
                    reorder_level=int(row.get('Reorder Level', row.get('reorder_level', 10)) or 10),
                    manufacturer=row.get('Manufacturer', row.get('manufacturer', '')),
                    requires_prescription=row.get('Requires Prescription', row.get('requires_prescription', 'No')).lower() in ['yes', 'true', '1']
                )
                db.session.add(drug)
                imported += 1
            
            db.session.commit()
            flash(f'Successfully imported {imported} drugs.', 'success')
            return redirect(url_for('admin.drugs'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error importing file: {str(e)}', 'error')
            return redirect(url_for('admin.import_drugs'))
    
    return render_template('admin/import_drugs.html')


@bp.route('/import/customers', methods=['GET', 'POST'])
@login_required
@admin_required
def import_customers():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected.', 'error')
            return redirect(url_for('admin.import_customers'))
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(url_for('admin.import_customers'))
        
        if not file.filename.endswith('.csv'):
            flash('Please upload a CSV file.', 'error')
            return redirect(url_for('admin.import_customers'))
        
        try:
            content = file.stream.read().decode('utf-8').replace('\r\n', '\n').replace('\r', '\n')
            stream = io.StringIO(content, newline='')
            reader = csv.DictReader(stream)
            
            imported = 0
            skipped = 0
            for row in reader:
                username = row.get('Username', row.get('username', ''))
                email = row.get('Email', row.get('email', ''))
                
                if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
                    skipped += 1
                    continue
                
                user = User(
                    username=username,
                    email=email,
                    full_name=row.get('Full Name', row.get('full_name', '')),
                    phone=row.get('Phone', row.get('phone', '')),
                    role='patient'
                )
                user.set_password('changeme123')
                db.session.add(user)
                imported += 1
            
            db.session.commit()
            flash(f'Successfully imported {imported} customers. Skipped {skipped} duplicates. Default password: changeme123', 'success')
            return redirect(url_for('admin.patients'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error importing file: {str(e)}', 'error')
            return redirect(url_for('admin.import_customers'))
    
    return render_template('admin/import_customers.html')


# ============ PRINT VIEWS ============

@bp.route('/print/drugs')
@login_required
@staff_required
def print_drugs():
    drugs = Drug.query.filter_by(is_active=True).order_by(Drug.name).all()
    return render_template('admin/print_drugs.html', drugs=drugs)


@bp.route('/print/sales')
@login_required
@staff_required
def print_sales():
    date_from = request.args.get('from', '')
    date_to = request.args.get('to', '')
    
    query = Sale.query
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Sale.created_at >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d')
            query = query.filter(Sale.created_at <= to_date)
        except ValueError:
            pass
    
    sales = query.order_by(Sale.created_at.desc()).all()
    total = sum(s.total_amount for s in sales)
    
    return render_template('admin/print_sales.html', sales=sales, total=total, 
                          date_from=date_from, date_to=date_to)


@bp.route('/print/customers')
@login_required
@staff_required
def print_customers():
    patients = User.query.filter_by(role='patient').order_by(User.full_name).all()
    return render_template('admin/print_customers.html', patients=patients)


# ============ ADVERTISEMENTS ============

@bp.route('/advertisements')
@login_required
@admin_required
def advertisements():
    ads = Advertisement.query.order_by(Advertisement.display_order, Advertisement.created_at.desc()).all()
    return render_template('admin/advertisements.html', advertisements=ads)


@bp.route('/advertisements/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_advertisement():
    # Check limit of 10 advertisements
    ad_count = Advertisement.query.count()
    if ad_count >= 10:
        flash('Maximum of 10 advertisements allowed. Please delete some before adding new ones.', 'warning')
        return redirect(url_for('admin.advertisements'))
    
    form = AdvertisementForm()
    
    if form.validate_on_submit():
        media_url = None
        
        if form.media_file.data:
            file = form.media_file.data
            if file and allowed_file(file.filename):
                import base64
                file_data = file.read()
                file_ext = file.filename.rsplit('.', 1)[1].lower()
                if file_ext in ['jpg', 'jpeg']:
                    mime_type = 'image/jpeg'
                elif file_ext in ['png', 'gif', 'webp']:
                    mime_type = f'image/{file_ext}'
                elif file_ext in ['mp4', 'webm']:
                    mime_type = f'video/{file_ext}'
                elif file_ext == 'mov':
                    mime_type = 'video/quicktime'
                else:
                    mime_type = 'application/octet-stream'
                base64_data = base64.b64encode(file_data).decode('utf-8')
                media_url = f'data:{mime_type};base64,{base64_data}'
            else:
                flash('Invalid file type. Allowed: png, jpg, jpeg, gif, webp, mp4, webm, mov', 'error')
                return render_template('admin/advertisement_form.html', form=form, title='Add Advertisement')
        elif form.media_url.data:
            media_url = form.media_url.data
        else:
            flash('Please upload a file or provide a media URL.', 'error')
            return render_template('admin/advertisement_form.html', form=form, title='Add Advertisement')
        
        ad = Advertisement(
            title=form.title.data,
            description=form.description.data,
            media_type=form.media_type.data,
            media_url=media_url,
            link_url=form.link_url.data,
            display_order=form.display_order.data or 0,
            is_active=form.is_active.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            created_by=current_user.id
        )
        db.session.add(ad)
        db.session.commit()
        flash('Advertisement added successfully!', 'success')
        return redirect(url_for('admin.advertisements'))
    
    return render_template('admin/advertisement_form.html', form=form, title='Add Advertisement')


@bp.route('/advertisements/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_advertisement(id):
    ad = Advertisement.query.get_or_404(id)
    form = AdvertisementForm(obj=ad)
    
    if form.validate_on_submit():
        if form.media_file.data:
            file = form.media_file.data
            if file and allowed_file(file.filename):
                import base64
                file_data = file.read()
                file_ext = file.filename.rsplit('.', 1)[1].lower()
                if file_ext in ['jpg', 'jpeg']:
                    mime_type = 'image/jpeg'
                elif file_ext in ['png', 'gif', 'webp']:
                    mime_type = f'image/{file_ext}'
                elif file_ext in ['mp4', 'webm']:
                    mime_type = f'video/{file_ext}'
                elif file_ext == 'mov':
                    mime_type = 'video/quicktime'
                else:
                    mime_type = 'application/octet-stream'
                base64_data = base64.b64encode(file_data).decode('utf-8')
                ad.media_url = f'data:{mime_type};base64,{base64_data}'
        elif form.media_url.data:
            ad.media_url = form.media_url.data
        
        ad.title = form.title.data
        ad.description = form.description.data
        ad.media_type = form.media_type.data
        ad.link_url = form.link_url.data
        ad.display_order = form.display_order.data or 0
        ad.is_active = form.is_active.data
        ad.start_date = form.start_date.data
        ad.end_date = form.end_date.data
        
        db.session.commit()
        flash('Advertisement updated successfully!', 'success')
        return redirect(url_for('admin.advertisements'))
    
    return render_template('admin/advertisement_form.html', form=form, title='Edit Advertisement', ad=ad)


@bp.route('/advertisements/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_advertisement(id):
    ad = Advertisement.query.get_or_404(id)
    db.session.delete(ad)
    db.session.commit()
    flash('Advertisement deleted successfully!', 'success')
    return redirect(url_for('admin.advertisements'))


@bp.route('/advertisements/<int:id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_advertisement(id):
    ad = Advertisement.query.get_or_404(id)
    ad.is_active = not ad.is_active
    db.session.commit()
    status = 'activated' if ad.is_active else 'deactivated'
    flash(f'Advertisement {status} successfully!', 'success')
    return redirect(url_for('admin.advertisements'))

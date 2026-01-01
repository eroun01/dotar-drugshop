from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, TextAreaField, SelectField, FloatField, IntegerField, BooleanField, DateField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError, Optional, NumberRange
from app.models import User


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Password', validators=[DataRequired()])


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=150)])
    phone = StringField('Phone Number', validators=[Optional(), Length(max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already exists. Please choose a different one.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different one.')


class StaffRegistrationForm(RegistrationForm):
    role = SelectField('Role', choices=[('nurse', 'Nurse'), ('admin', 'Admin')], validators=[DataRequired()])


class DrugForm(FlaskForm):
    name = StringField('Drug Name', validators=[DataRequired(), Length(max=150)])
    generic_name = StringField('Generic Name', validators=[Optional(), Length(max=150)])
    description = TextAreaField('Description', validators=[Optional()])
    category = SelectField('Category', choices=[
        ('', 'Select Category'),
        ('antibiotics', 'Antibiotics'),
        ('analgesics', 'Analgesics/Pain Relief'),
        ('antihistamines', 'Antihistamines'),
        ('antacids', 'Antacids'),
        ('cardiovascular', 'Cardiovascular'),
        ('diabetes', 'Diabetes'),
        ('vitamins', 'Vitamins & Supplements'),
        ('respiratory', 'Respiratory'),
        ('dermatology', 'Dermatology'),
        ('gastrointestinal', 'Gastrointestinal'),
        ('other', 'Other')
    ])
    dosage_form = SelectField('Dosage Form', choices=[
        ('', 'Select Form'),
        ('tablet', 'Tablet'),
        ('capsule', 'Capsule'),
        ('syrup', 'Syrup'),
        ('injection', 'Injection'),
        ('cream', 'Cream/Ointment'),
        ('drops', 'Drops'),
        ('inhaler', 'Inhaler'),
        ('powder', 'Powder'),
        ('suspension', 'Suspension')
    ])
    strength = StringField('Strength (e.g., 500mg)', validators=[Optional(), Length(max=50)])
    unit_price = FloatField('Unit Price', validators=[DataRequired(), NumberRange(min=0)])
    quantity_in_stock = IntegerField('Quantity in Stock', validators=[DataRequired(), NumberRange(min=0)])
    reorder_level = IntegerField('Reorder Level', validators=[Optional(), NumberRange(min=0)])
    expiry_date = DateField('Expiry Date', validators=[Optional()])
    manufacturer = StringField('Manufacturer', validators=[Optional(), Length(max=150)])
    requires_prescription = BooleanField('Requires Prescription')


class ConsultationForm(FlaskForm):
    subject = StringField('Subject', validators=[DataRequired(), Length(max=200)])
    symptoms = TextAreaField('Describe Your Symptoms', validators=[DataRequired()])
    message = TextAreaField('Additional Details', validators=[DataRequired()])
    priority = SelectField('Priority', choices=[
        ('normal', 'Normal'),
        ('low', 'Low'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ])


class ConsultationResponseForm(FlaskForm):
    response = TextAreaField('Response', validators=[DataRequired()])
    recommended_drugs = TextAreaField('Recommended Drugs', validators=[Optional()])
    status = SelectField('Status', choices=[
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved')
    ])


class SaleForm(FlaskForm):
    drug_id = SelectField('Select Drug', coerce=int, validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)])
    customer_name = StringField('Customer Name', validators=[Optional(), Length(max=150)])
    customer_phone = StringField('Customer Phone', validators=[Optional(), Length(max=20)])
    payment_method = SelectField('Payment Method', choices=[
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('mobile_money', 'Mobile Money')
    ])
    notes = TextAreaField('Notes', validators=[Optional()])


class OrderForm(FlaskForm):
    drug_id = SelectField('Select Medicine', coerce=int, validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)])
    
    disease_condition = StringField('Disease/Condition', validators=[DataRequired(), Length(max=200)])
    condition_severity = SelectField('Condition Severity', choices=[
        ('mild', 'Mild - Not urgent'),
        ('normal', 'Normal - Standard delivery'),
        ('severe', 'Severe - Need quick delivery'),
        ('critical', 'Critical - Emergency delivery needed')
    ])
    symptoms_description = TextAreaField('Describe Your Symptoms', validators=[Optional()])
    
    delivery_address = StringField('Full Delivery Address', validators=[DataRequired(), Length(max=300)])
    delivery_district = SelectField('District', choices=[
        ('', 'Select District'),
        ('kampala', 'Kampala'),
        ('wakiso', 'Wakiso'),
        ('mukono', 'Mukono'),
        ('jinja', 'Jinja'),
        ('gulu', 'Gulu'),
        ('lira', 'Lira'),
        ('mbarara', 'Mbarara'),
        ('mbale', 'Mbale'),
        ('masaka', 'Masaka'),
        ('entebbe', 'Entebbe'),
        ('fort_portal', 'Fort Portal'),
        ('kabale', 'Kabale'),
        ('soroti', 'Soroti'),
        ('arua', 'Arua'),
        ('hoima', 'Hoima'),
        ('kasese', 'Kasese'),
        ('mityana', 'Mityana'),
        ('iganga', 'Iganga'),
        ('busia', 'Busia'),
        ('tororo', 'Tororo'),
        ('kitgum', 'Kitgum'),
        ('kotido', 'Kotido'),
        ('moroto', 'Moroto'),
        ('kapchorwa', 'Kapchorwa'),
        ('kumi', 'Kumi'),
        ('pallisa', 'Pallisa'),
        ('bugiri', 'Bugiri'),
        ('mayuge', 'Mayuge'),
        ('kamuli', 'Kamuli'),
        ('kaliro', 'Kaliro'),
        ('buyende', 'Buyende'),
        ('luuka', 'Luuka'),
        ('namutumba', 'Namutumba'),
        ('budaka', 'Budaka'),
        ('kibuku', 'Kibuku'),
        ('butaleja', 'Butaleja'),
        ('manafwa', 'Manafwa'),
        ('bududa', 'Bududa'),
        ('sironko', 'Sironko'),
        ('bulambuli', 'Bulambuli'),
        ('kabarole', 'Kabarole'),
        ('kyenjojo', 'Kyenjojo'),
        ('kamwenge', 'Kamwenge'),
        ('kyegegwa', 'Kyegegwa'),
        ('ntoroko', 'Ntoroko'),
        ('bundibugyo', 'Bundibugyo'),
        ('bunyangabu', 'Bunyangabu'),
        ('bushenyi', 'Bushenyi'),
        ('sheema', 'Sheema'),
        ('buhweju', 'Buhweju'),
        ('mitooma', 'Mitooma'),
        ('rubirizi', 'Rubirizi'),
        ('ntungamo', 'Ntungamo'),
        ('rukungiri', 'Rukungiri'),
        ('kanungu', 'Kanungu'),
        ('kisoro', 'Kisoro'),
        ('rubanda', 'Rubanda'),
        ('isingiro', 'Isingiro'),
        ('kiruhura', 'Kiruhura'),
        ('ibanda', 'Ibanda'),
        ('kazo', 'Kazo'),
        ('rwampara', 'Rwampara'),
        ('lyantonde', 'Lyantonde'),
        ('rakai', 'Rakai'),
        ('kyotera', 'Kyotera'),
        ('lwengo', 'Lwengo'),
        ('bukomansimbi', 'Bukomansimbi'),
        ('kalungu', 'Kalungu'),
        ('sembabule', 'Sembabule'),
        ('gomba', 'Gomba'),
        ('butambala', 'Butambala'),
        ('mpigi', 'Mpigi'),
        ('buvuma', 'Buvuma'),
        ('buikwe', 'Buikwe'),
        ('kayunga', 'Kayunga'),
        ('luweero', 'Luweero'),
        ('nakasongola', 'Nakasongola'),
        ('nakaseke', 'Nakaseke'),
        ('kiboga', 'Kiboga'),
        ('kyankwanzi', 'Kyankwanzi'),
        ('mubende', 'Mubende'),
        ('kakumiro', 'Kakumiro'),
        ('kagadi', 'Kagadi'),
        ('kibaale', 'Kibaale'),
        ('kiryandongo', 'Kiryandongo'),
        ('masindi', 'Masindi'),
        ('buliisa', 'Buliisa'),
        ('kikuube', 'Kikuube'),
        ('nebbi', 'Nebbi'),
        ('pakwach', 'Pakwach'),
        ('zombo', 'Zombo'),
        ('moyo', 'Moyo'),
        ('obongi', 'Obongi'),
        ('adjumani', 'Adjumani'),
        ('yumbe', 'Yumbe'),
        ('koboko', 'Koboko'),
        ('maracha', 'Maracha'),
        ('terego', 'Terego'),
        ('madi_okollo', 'Madi-Okollo'),
        ('amuru', 'Amuru'),
        ('nwoya', 'Nwoya'),
        ('omoro', 'Omoro'),
        ('pader', 'Pader'),
        ('agago', 'Agago'),
        ('lamwo', 'Lamwo'),
        ('alebtong', 'Alebtong'),
        ('otuke', 'Otuke'),
        ('dokolo', 'Dokolo'),
        ('kole', 'Kole'),
        ('oyam', 'Oyam'),
        ('kwania', 'Kwania'),
        ('apac', 'Apac'),
        ('amolatar', 'Amolatar'),
        ('kaberamaido', 'Kaberamaido'),
        ('katakwi', 'Katakwi'),
        ('amuria', 'Amuria'),
        ('kapelebyong', 'Kapelebyong'),
        ('serere', 'Serere'),
        ('ngora', 'Ngora'),
        ('bukedea', 'Bukedea'),
        ('nakapiripirit', 'Nakapiripirit'),
        ('nabilatuk', 'Nabilatuk'),
        ('napak', 'Napak'),
        ('amudat', 'Amudat'),
        ('abim', 'Abim'),
        ('karenga', 'Karenga'),
        ('kaabong', 'Kaabong')
    ])
    delivery_sector = StringField('Division/Subcounty', validators=[Optional(), Length(max=100)])
    delivery_cell = StringField('Parish/Village', validators=[Optional(), Length(max=100)])
    location_landmark = StringField('Nearby Landmark', validators=[Optional(), Length(max=200)])
    delivery_phone = StringField('Delivery Phone Number', validators=[DataRequired(), Length(max=20)])
    delivery_notes = TextAreaField('Delivery Instructions', validators=[Optional()])


class OrderStatusForm(FlaskForm):
    order_status = SelectField('Order Status', choices=[
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled')
    ])
    payment_status = SelectField('Payment Status', choices=[
        ('pending', 'Pending'),
        ('paid', 'Paid')
    ])
    payment_amount_received = FloatField('Amount Received (UGX)', validators=[Optional(), NumberRange(min=0)])
    admin_notes = TextAreaField('Admin Notes', validators=[Optional()])


class ShopSettingsForm(FlaskForm):
    shop_name = StringField('Shop Name', validators=[DataRequired(), Length(max=200)])
    shop_tagline = StringField('Tagline', validators=[Optional(), Length(max=300)])
    shop_email = StringField('Email', validators=[Optional(), Email()])
    shop_phone = StringField('Phone', validators=[Optional(), Length(max=50)])
    shop_address = TextAreaField('Address', validators=[Optional()])
    shop_hours = StringField('Business Hours', validators=[Optional(), Length(max=200)])
    currency = StringField('Currency', validators=[Optional(), Length(max=10)])
    delivery_fee = FloatField('Delivery Fee', validators=[Optional(), NumberRange(min=0)])
    min_order_amount = FloatField('Minimum Order Amount', validators=[Optional(), NumberRange(min=0)])
    about_text = TextAreaField('About Us Text', validators=[Optional()])
    mission_text = TextAreaField('Mission Statement', validators=[Optional()])
    vision_text = TextAreaField('Vision Statement', validators=[Optional()])


class AdminProfileForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=150)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone Number', validators=[Optional(), Length(max=20)])
    current_password = PasswordField('Current Password', validators=[Optional()])
    new_password = PasswordField('New Password', validators=[Optional(), Length(min=6)])
    confirm_new_password = PasswordField('Confirm New Password', validators=[Optional(), EqualTo('new_password')])


class AdvertisementForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=1000)])
    media_type = SelectField('Media Type', choices=[
        ('image', 'Image'),
        ('video', 'Video')
    ], validators=[DataRequired()])
    media_file = FileField('Upload Media File', validators=[Optional()])
    media_url = StringField('Or Enter Media URL (YouTube, external link)', validators=[Optional(), Length(max=500)])
    link_url = StringField('Link URL (optional - where to go when clicked)', validators=[Optional(), Length(max=500)])
    display_order = IntegerField('Display Order', validators=[Optional(), NumberRange(min=0)], default=0)
    is_active = BooleanField('Active', default=True)
    start_date = DateField('Start Date (optional)', validators=[Optional()])
    end_date = DateField('End Date (optional)', validators=[Optional()])

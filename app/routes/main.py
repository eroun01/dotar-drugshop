from flask import Blueprint, render_template
from flask_login import current_user
from datetime import date
from app.models import Advertisement

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    today = date.today()
    advertisements = Advertisement.query.filter(
        Advertisement.is_active == True
    ).filter(
        (Advertisement.start_date == None) | (Advertisement.start_date <= today)
    ).filter(
        (Advertisement.end_date == None) | (Advertisement.end_date >= today)
    ).order_by(Advertisement.display_order, Advertisement.created_at.desc()).all()
    
    return render_template('index.html', advertisements=advertisements)

@bp.route('/about')
def about():
    return render_template('about.html')

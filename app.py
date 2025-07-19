import os
import logging
import datetime
import uuid
import json

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_mail import Mail, Message
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from dotenv import load_dotenv
from flask_talisman import Talisman

# Extensions
from extension import mail
from db import db, DATABASE_URL

# Forms
from forms import (
    RegistrationForm, 
    TransactionForm, 
    ChatMessageForm, 
    LoginForm,
    PasswordResetRequestForm,  
    PasswordResetForm
)

# Models
from models import (
    User, 
    Transaction, 
    ChatMessage, 
    Product, 
    SellerToBuyerRequest, 
    Notification
)

# Services
from email_service import (
    send_email_verification,
    send_password_reset,
    send_transaction_notification
)

# Payment
import razorpay




app = Flask(__name__)

Talisman(app)

## --- Database Configuration ---
# This NEW code gets the DATABASE_URL from the AWS server's environment
db_url = os.environ.get('DATABASE_URL')

# Fix for PostgreSQL URL format if needed
if db_url and db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)
    
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# This line will be moved down with the other initializations
# db.init_app(app)







# --- Configure Logging ---
logging.basicConfig(level=logging.DEBUG)

# --- Create Flask App ---


app = Flask(__name__, template_folder='templates')
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)



# --- Database Configuration ---
# Directly assign full DATABASE URI without using os.getenv
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "postgresql://escrow_db_a6ed_user:iTaLjdvRPMBrLdIjHXlQPaALKlAjgjR1@dpg-d1to2rbipnbc73ci2dog-a.oregon-postgres.render.com/escrow_db_a6ed"
)

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# --- Email Configuration ---
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', '587'))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'vishal.sankar12345@gmail.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'tpktmhvyfgxtryqj')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'MyPaymentSafe <vishal.sankar12345@gmail.com>')

# --- File Upload Configuration ---
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- Ensure Upload Directory Exists ---
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# --- Initialize Extensions ---
db.init_app(app)
mail = Mail()
mail.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

migrate = Migrate(app, db)





# --- User Loader ---
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- Helper Function ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ---------------- Routes ----------------


# --- Admin Auto-Creation ---
def create_admin():
    admin = User.query.filter_by(email='admin@trustcart.com').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@trustcart.com',
            password_hash=generate_password_hash('admin123'),
            role='admin',
            is_verified=True,
            email_verified=True
        )
        db.session.add(admin)
        db.session.commit()
        logging.info("Admin user created: admin@trustcart.com / admin123")

# --- Setup on App Start ---



with app.app_context():
    db.create_all()
    create_admin()

application = app

import routes


if __name__ == "__main__":
    print("🔥 Flask server starting...")
    app.run(debug=True)

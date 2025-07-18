import os
import logging
import datetime
import uuid
import json

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_mail import Mail, Message
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash,check_password_hash
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
# OLD:
# from flask_mail import Mail

# NEW:
from extension import mail


# Local imports
from forms import RegistrationForm, TransactionForm, ChatMessageForm, LoginForm
from models import db, Transaction, User, ChatMessage, Product, SellerToBuyerRequest, Notification
from email_service import (
    send_email_verification,
    send_password_reset,
    send_transaction_notification
)
import razorpay
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from db import db, DATABASE_URL
from dotenv import load_dotenv
from flask_talisman import Talisman
from forms import PasswordResetRequestForm ,  PasswordResetForm
from models import User



load_dotenv()
app = Flask(__name__)

Talisman(app)

# Database configuration
db_url = os.getenv('DATABASE_URL')

# Fix for Render's PostgreSQL URL format
if db_url and db_url.startswith('postgres://'):
    db_url = db_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)





RAZORPAY_KEY_ID = "rzp_test_XVt2SV0Q5ACLfe"  # 🔁 Define this so you can use it in templates
RAZORPAY_KEY_SECRET = "8GzctFWrAX2TvskLkjZVdUPE"

razorpay_client = razorpay.Client(auth=("rzp_test_XVt2SV0Q5ACLfe", "8GzctFWrAX2TvskLkjZVdUPE"))


# --- Configure Logging ---
logging.basicConfig(level=logging.DEBUG)

# --- Create Flask App ---


app = Flask(__name__, template_folder='templates')
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# --- Secret Key for Sessions ---
app.secret_key = "dev_12345_mypaymentsafe_secret"
s = URLSafeTimedSerializer(app.secret_key)

# --- Database Configuration ---
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# --- Email Configuration ---
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', '587'))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', 'noreply@trustcart.com')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', 'default_password')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'TrustCart <noreply@trustcart.com>')

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
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            flash("Logged in successfully.", "success")
            if user.role == "admin":
                return redirect(url_for("admin_dashboard"))
            else:
                return redirect(url_for("unified_dashboard"))
        else:
            flash("Invalid email or password.", "danger")
    return render_template("auth/login.html", form=form)

@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash("Email already registered.", "danger")
            return render_template("auth/register.html", form=form)
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data),
            is_verified=False,
            email_verified=False
        )
        db.session.add(user)
        db.session.commit()

        token = str(user.id)  # Replace with secure token logic if needed
        send_email_verification(user.email, token)
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("auth/register.html", form=form)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

def send_email_verification(user_email, token):
    verification_url = url_for('verify_email', token=token, _external=True)

    msg = Message(
        subject='Verify Your TrustCart Account',
        recipients=[user_email],
        sender='MyPaymentSafe <youremail@gmail.com>'
    )
    # ✅ Correct path to template
    msg.html = render_template('emails/verify_email.html', link=verification_url)
    mail.send(msg)

@app.route('/forgot', methods=['GET', 'POST'])
def forgot_password():
    form = PasswordResetRequestForm()

    if form.validate_on_submit():
        email = form.email.data
        user = User.query.filter_by(email=email).first()
        if user:
            token = s.dumps(email, salt='email-reset')
            reset_link = url_for('reset_password', token=token, _external=True)
            msg = Message('Reset Your Password', sender='your_email@gmail.com', recipients=[email])
            msg.html = render_template('emails/email_reset.html', link=reset_link)
            mail.send(msg)
            flash('Reset link sent to your email.', 'success')
        else:
            flash('Email not found.', 'danger')

    return render_template('forgot_password.html', form=form)

@app.route('/reset/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = s.loads(token, salt='email-reset', max_age=3600)
    except (SignatureExpired, BadSignature):
        return "Reset link expired or invalid."

    user = User.query.filter_by(email=email).first()
    if not user:
        return "User does not exist."

    form = PasswordResetForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash("Your password has been reset.", "success")
        return redirect(url_for('login'))

    return render_template('reset_password.html', form=form)

@app.route('/transaction/create', methods=['GET', 'POST'])
@login_required
def create_transaction():
    form = TransactionForm()

    if request.method == 'POST':
        title = request.form['deal_name']
        category = request.form['category']
        subcategory = request.form['subcategory']
        role = request.form['role']
        other_party_id = request.form.get('counterparty_id')
        description = request.form['description']
        price = request.form['price']
        review_period = request.form['review_period']
        uploaded_files = request.files.getlist('images')
        image_filenames = []

        # Save uploaded images
        for file in uploaded_files:
            if file and allowed_file(file.filename):
                filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
                upload_folder = app.config['UPLOAD_FOLDER']  # ✅ Use global config
                save_path = os.path.join(upload_folder, filename)
                file.save(save_path)
                image_filenames.append(filename)

        # Determine buyer and seller
        if role == 'buyer':
            buyer_id = current_user.id
            seller_id = int(other_party_id)
        else:
            seller_id = current_user.id
            buyer_id = int(other_party_id)

        # Convert price to float and use it as amount
        try:
            amount = float(price)
        except (TypeError, ValueError):
            amount = 0.0  # Default or raise error

        # Create transaction object
        transaction = Transaction(
            title=title,
            category=category,
            subcategory=subcategory,
            description=description,
            price=price,
            amount=amount,
            review_period=review_period,
            images=image_filenames,
            seller_id=seller_id,
            buyer_id=buyer_id,
            created_by_id=current_user.id,
            status='pending'
        )

        db.session.add(transaction)
        db.session.commit()

        flash("Transaction created! Awaiting response from the other party.", "success")
        return redirect(url_for("unified_dashboard"))

    all_users = User.query.filter(User.id != current_user.id).all()
    return render_template("transaction/transaction.html", form=form, all_users=all_users)

@app.route("/transaction/<int:id>", methods=["GET", "POST"])
@login_required
def transaction_detail(id):
    transaction = Transaction.query.get_or_404(id)

    # ✅ Check if the user is allowed to view this transaction
    if current_user.role != 'admin' and current_user.id not in [transaction.buyer_id, transaction.seller_id]:
        flash("You are not authorized to view this transaction.", "danger")
        return redirect(url_for('unified_dashboard'))

    # ✅ Ensure images is a list (convert from JSON string if needed)
    if isinstance(transaction.images, str):
        try:
            transaction.images = json.loads(transaction.images)
        except json.JSONDecodeError:
            transaction.images = []

    print("Transaction Images:", transaction.images)

    # ✅ Fetch chat messages
    messages = ChatMessage.query.filter_by(transaction_id=id).order_by(ChatMessage.created_at.asc()).all()
    form = ChatMessageForm()

    # ✅ Determine the user's role
    if transaction.buyer_id == current_user.id:
        role = 'buyer'
    elif transaction.seller_id == current_user.id:
        role = 'seller'
    else:
        role = 'unauthorized'

    # ✅ Logic to determine who can respond (accept/reject)
    is_creator = current_user.id == transaction.created_by_id
    can_respond = current_user.id != transaction.created_by_id and transaction.status == 'pending'

    # ✅ Get the responder (other party)
    responder_id = transaction.seller_id if transaction.created_by_id == transaction.buyer_id else transaction.buyer_id
    responder = db.session.get(User, responder_id)

    # ✅ Render template
    return render_template(
        "transaction/detail.html",
        transaction=transaction,
        messages=messages,
        form=form,
        role=role,
        responder=responder,
        can_respond=can_respond
    )
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    # ✅ Ensure only admin can access
    if current_user.role != 'admin':
        flash("Unauthorized access.", "danger")
        return redirect(url_for("unified_dashboard"))

    # ✅ Query transaction counts by status
    available_count = Transaction.query.filter_by(status='pending').count()
    active_count = Transaction.query.filter_by(status='in_progress').count()

    # ✅ Fetch all transactions grouped by status
    available_transactions = Transaction.query.filter_by(status='pending').order_by(Transaction.created_at.desc()).all()
    active_transactions = Transaction.query.filter_by(status='in_progress').order_by(Transaction.created_at.desc()).all()
    all_transactions = Transaction.query.order_by(Transaction.created_at.desc()).all()

    # ✅ Fetch all users (buyers and sellers)
    buyers = User.query.filter_by(role='user').all()
    sellers = User.query.filter_by(role='user').all()

    # ✅ Render admin dashboard template with all necessary data
    return render_template(
        "admin/dashboard.html",
        transactions=all_transactions,
        buyers=buyers,
        sellers=sellers,
        available_count=available_count,
        active_count=active_count,
        available_transactions=available_transactions,
        active_transactions=active_transactions
    )

@app.route('/transaction/<int:id>/accept', methods=['POST'])
@login_required
def accept_transaction(id):
    transaction = Transaction.query.get_or_404(id)

    if current_user.id == transaction.created_by_id:
        flash("You are not allowed to accept your own transaction request.", "danger")
        return redirect(url_for('transaction_detail', id=id))

    if transaction.status != 'pending':
        flash("This transaction has already been processed.", "warning")
        return redirect(url_for('transaction_detail', id=id))

    transaction.status = 'accepted'
    transaction.updated_at = datetime.utcnow()
    db.session.commit()

    flash("Transaction accepted. Proceed to payment.", "success")
    return redirect(url_for('transaction_detail', id=id))
@app.route('/verify_payment/<int:transaction_id>', methods=['POST'])
@login_required
def verify_payment(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)

    # ⚠️ Optional: You can verify the payment signature from Razorpay here if needed

    # ✅ Mark payment as done
    transaction.payment_done = True
    db.session.commit()

    flash("Payment Successful. You may now release the funds when you're ready.")
    return redirect(url_for('transaction_detail', id=transaction.id))


@app.route('/transaction/<int:id>/reject', methods=['POST'])
@login_required
def reject_transaction(id):
    transaction = Transaction.query.get_or_404(id)

    if current_user.id == transaction.created_by_id:
        flash("You are not allowed to reject your own transaction request.", "danger")
        return redirect(url_for('transaction_detail', id=id))

    if transaction.status != 'pending':
        flash("This transaction has already been processed.", "warning")
        return redirect(url_for('transaction_detail', id=id))

    transaction.status = 'rejected'
    transaction.updated_at = datetime.utcnow()
    db.session.commit()

    flash("Transaction rejected.", "info")
    return redirect(url_for('transaction_detail', id=id))

@app.route('/create_order/<int:transaction_id>', methods=['GET', 'POST'])
@login_required
def create_order(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)

    if request.method == 'POST':
        platform_fee = round(0.07 * float(transaction.amount), 2)  # 7% fee
        total_amount = round(float(transaction.amount) + platform_fee, 2)
        total_paise = int(total_amount * 100)

        order_data = {
            "amount": total_paise,
            "currency": "INR",
            "payment_capture": '1'
        }

        razorpay_order = razorpay_client.order.create(data=order_data)
        transaction.razorpay_order_id = razorpay_order['id']
        db.session.commit()

        return render_template(
            "payment.html",
            order_id=razorpay_order['id'],
            amount=transaction.amount,
            platform_fee=platform_fee,
            total=total_amount,
            key_id=RAZORPAY_KEY_ID,
            transaction=transaction
        )

    return redirect(url_for('transaction_detail', transaction_id=transaction.id))


@app.route('/payment/<int:transaction_id>')
@login_required
def payment_page(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)

    # Only buyer can pay
    if current_user.id != transaction.buyer_id:
        abort(403)

    order_data = {
        "amount": int(float(transaction.amount) * 100),
        "currency": "INR",
        "payment_capture": '1'
    }

    razorpay_order = razorpay_client.order.create(data=order_data)
    transaction.razorpay_order_id = razorpay_order['id']
    db.session.commit()

    return render_template("payment.html",
                           transaction=transaction,
                           order_id=razorpay_order['id'],
                           amount=transaction.amount,
                           key_id=RAZORPAY_KEY_ID)


@app.route("/transaction/respond/<int:transaction_id>", methods=["POST"])
@login_required
def respond_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)

    # Determine the correct responder (non-creator)
    if transaction.created_by_id == transaction.buyer_id:
        allowed_responder_id = transaction.seller_id
    else:
        allowed_responder_id = transaction.buyer_id

    # Only that person can respond
    if current_user.id != allowed_responder_id or transaction.status != 'pending':
        flash("You are not authorized to respond to this transaction.", "danger")
        return redirect(url_for("transaction_detail", id=transaction_id))

    response = request.form.get("response")

    if response == "accept":
        transaction.status = "in_progress"
        transaction.updated_at = datetime.datetime.now()
        db.session.commit()
        flash("Transaction accepted. Buyer can now proceed to payment.", "success")

    elif response == "reject":
        transaction.status = "rejected"
        transaction.updated_at = datetime.datetime.now()
        db.session.commit()
        flash("Transaction rejected.", "info")

    return redirect(url_for("transaction_detail", id=transaction_id))

@app.route('/transaction/<int:transaction_id>/send_message', methods=['POST'])
@login_required
def send_message(transaction_id):
    form = ChatMessageForm()
    if form.validate_on_submit():
        message = ChatMessage(
            transaction_id=transaction_id,
            sender_id=current_user.id,
            message=form.message.data
        )
        db.session.add(message)
        db.session.commit()
    return redirect(url_for('transaction_detail', id=transaction_id))

@app.route("/transaction/<int:id>/chat", endpoint="chat_room")
@login_required
def chat_room(id):
    transaction = Transaction.query.get_or_404(id)
    return render_template("chat/chat_room.html", transaction=transaction)

@app.route("/dashboard")
@app.route("/user/dashboard", endpoint="unified_dashboard")
@login_required
def unified_dashboard():
    transactions = Transaction.query.filter(
        (Transaction.buyer_id == current_user.id) | (Transaction.seller_id == current_user.id)
    ).order_by(Transaction.created_at.desc()).all()
    return render_template("dashboard.html", transactions=transactions)


@app.route('/transaction/status/<int:transaction_id>')
def get_transaction_status(transaction_id):
    transaction = Transaction.query.get(transaction_id)
    if transaction:
        return jsonify({'status': transaction.status})
    return jsonify({'status': 'not_found'}), 404

@app.route('/search_users')
@login_required
def search_users():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    users = User.query.filter(User.username.ilike(f'%{query}%'), User.id != current_user.id).limit(10).all()
    results = [user.username for user in users]
    return jsonify(results)

@app.route('/seller/send_request/<int:product_id>/<int:buyer_id>')
@login_required
def send_seller_request(product_id, buyer_id):
    existing = SellerToBuyerRequest.query.filter_by(
        seller_id=current_user.id,
        buyer_id=buyer_id,
        product_id=product_id
    ).first()

    if existing:
        flash("Request already sent.")
    else:
        req = SellerToBuyerRequest(
            seller_id=current_user.id,
            buyer_id=buyer_id,
            product_id=product_id
        )
        db.session.add(req)
        db.session.commit()
        flash("Request sent to buyer.")

    return redirect(url_for('dashboard'))

@app.route('/buyer/requests')
@login_required
def buyer_requests():
    requests = SellerToBuyerRequest.query.filter_by(buyer_id=current_user.id).all()
    return render_template('buyer_requests.html', requests=requests)

@app.route('/buyer/respond/<int:req_id>/<string:action>')
@login_required
def respond_to_seller_request(req_id, action):
    req = SellerToBuyerRequest.query.get_or_404(req_id)
    if req.buyer_id != current_user.id:
        flash("Unauthorized access.")
        return redirect(url_for('buyer_requests'))
    if action in ['accept', 'reject']:
        req.status = action
        db.session.commit()
        flash(f"Request {action}ed.")
    return redirect(url_for('buyer_requests'))


@app.route('/transaction/complete/<int:transaction_id>', methods=['POST'])
@login_required
def complete_transaction(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)

    if current_user.id != transaction.buyer_id:
        flash("You are not authorized to complete this transaction.", "danger")
        return redirect(url_for('transaction_detail', transaction_id=transaction_id))

    transaction.status = 'completed'
    transaction.completed_at = datetime.datetime.now()
    transaction.updated_at = datetime.datetime.now()

    db.session.commit()
    flash("Transaction marked as completed.", "success")
    return redirect(url_for('transaction_detail', id=transaction_id))

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

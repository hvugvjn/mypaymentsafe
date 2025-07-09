from flask import render_template, request, redirect, url_for, flash, jsonify, Response
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from datetime import datetime
import json
import time
import os
from app import app, db
from models import User, Transaction, ChatMessage, Notification
from forms import LoginForm, RegistrationForm, TransactionForm, ChatMessageForm, PasswordResetRequestForm, PasswordResetForm
from email_service import send_email_verification, send_transaction_notification, send_password_reset
from decorators import admin_required, seller_required, verified_seller_required
from .models import User
from .forms import DealForm
from werkzeug.utils import secure_filename


UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.context_processor
def inject_user():
    return dict(current_user=current_user)

# Authentication routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin_dashboard'))
        elif current_user.is_seller():
            return redirect(url_for('seller_dashboard'))
        else:
            return redirect(url_for('buyer_dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            if not user.email_verified:
                flash('Please verify your email address before logging in.', 'warning')
                return redirect(url_for('login'))
            login_user(user, remember=form.remember_me.data)
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))
        flash('Invalid email or password.', 'danger')
    return render_template('auth/login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            role=form.role.data
        )
        user.set_password(form.password.data)
        token = user.generate_email_verification_token()
        
        db.session.add(user)
        db.session.commit()
        
        send_email_verification(user.email, token)
        flash('Registration successful! Please check your email to verify your account.', 'success')
        return redirect(url_for('login'))
    return render_template('auth/register.html', form=form)

@app.route('/verify-email/<token>')
def verify_email(token):
    user = User.query.filter_by(email_verification_token=token).first()
    if user:
        user.email_verified = True
        user.email_verification_token = None
        db.session.commit()
        flash('Email verified successfully! You can now log in.', 'success')
    else:
        flash('Invalid or expired verification token.', 'danger')
    return redirect(url_for('login'))

@app.route('/reset-password-request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.generate_reset_password_token()
            db.session.commit()
            send_password_reset(user.email, token)
        flash('Check your email for password reset instructions.', 'info')
        return redirect(url_for('login'))
    return render_template('auth/reset_password_request.html', form=form)

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    user = User.query.filter_by(reset_password_token=token).first()
    if not user or user.reset_password_expires < datetime.utcnow():
        flash('Invalid or expired reset token.', 'danger')
        return redirect(url_for('login'))
    
    form = PasswordResetForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.reset_password_token = None
        user.reset_password_expires = None
        db.session.commit()
        flash('Your password has been reset successfully.', 'success')
        return redirect(url_for('login'))
    return render_template('auth/reset_password.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# Buyer routes
@app.route('/buyer/dashboard')
@login_required
def buyer_dashboard():
    if not current_user.is_buyer():
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    transactions = current_user.buyer_transactions.order_by(Transaction.created_at.desc()).all()
    return render_template('buyer/dashboard.html', transactions=transactions)

@app.route('/create-transaction', methods=['GET', 'POST'])
@login_required
def create_transaction():
    form = DealForm()
    if form.validate_on_submit():
        deal_name = request.form['deal_name']
        category = request.form['category']
        subcategory = request.form['subcategory']
        role = request.form['role']
        description = request.form['description']
        price = request.form['price']
        review_period = request.form['review_period']

        uploaded_files = request.files.getlist('images')
        image_filenames = []

        for file in uploaded_files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                save_path = os.path.join(UPLOAD_FOLDER, filename)
                file.save(save_path)
                image_filenames.append(filename)

        # Save to DB here if needed
        flash("Transaction created successfully!", "success")
        return redirect(url_for('unified_dashboard'))

    return render_template("transaction.html", form=form, all_users=User.query.all())
@app.route('/buyer/transaction/<int:id>')
@login_required
def buyer_transaction_detail(id):
    transaction = Transaction.query.get_or_404(id)
    if transaction.buyer_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('buyer_dashboard'))
    
    messages = transaction.messages.order_by(ChatMessage.created_at.asc()).all()
    form = ChatMessageForm()
    return render_template('buyer/transaction_detail.html', transaction=transaction, messages=messages, form=form)

@app.route('/buyer/complete-transaction/<int:id>', methods=['POST'])
@login_required
def complete_transaction(id):
    transaction = Transaction.query.get_or_404(id)
    if transaction.buyer_id != current_user.id or not transaction.can_be_completed():
        flash('Cannot complete this transaction.', 'danger')
        return redirect(url_for('buyer_transaction_detail', id=id))
    
    transaction.status = 'completed'
    transaction.completed_at = datetime.utcnow()
    
    # Create notification for seller
    notification = Notification(
        user_id=transaction.seller_id,
        transaction_id=transaction.id,
        title='Payment Released',
        message=f'Payment for "{transaction.title}" has been released by the buyer.'
    )
    db.session.add(notification)
    db.session.commit()
    
    send_transaction_notification(transaction.seller.email, 'Payment Released', 
                                f'Payment for "{transaction.title}" has been released.')
    
    flash('Transaction completed! Payment has been released to the seller.', 'success')
    return redirect(url_for('buyer_transaction_detail', id=id))

# Seller routes
@app.route('/seller/dashboard')
@login_required
@seller_required
def seller_dashboard():
    if not current_user.is_verified:
        return render_template('seller/verification_pending.html')
    
    available_transactions = Transaction.query.filter_by(status='pending', seller_id=None).order_by(Transaction.created_at.desc()).all()
    my_transactions = current_user.seller_transactions.order_by(Transaction.created_at.desc()).all()
    return render_template('seller/dashboard.html', available_transactions=available_transactions, my_transactions=my_transactions)

@app.route('/seller/accept-transaction/<int:id>', methods=['POST'])
@login_required
@verified_seller_required
def accept_transaction(id):
    transaction = Transaction.query.get_or_404(id)
    if not transaction.can_be_accepted():
        flash('This transaction cannot be accepted.', 'danger')
        return redirect(url_for('seller_dashboard'))
    
    transaction.seller_id = current_user.id
    transaction.status = 'in_progress'
    
    # Create notification for buyer
    notification = Notification(
        user_id=transaction.buyer_id,
        transaction_id=transaction.id,
        title='Transaction Accepted',
        message=f'Your transaction "{transaction.title}" has been accepted by {current_user.username}.'
    )
    db.session.add(notification)
    db.session.commit()
    
    send_transaction_notification(transaction.buyer.email, 'Transaction Accepted', 
                                f'Your transaction "{transaction.title}" has been accepted.')
    
    flash('Transaction accepted successfully!', 'success')
    return redirect(url_for('seller_dashboard'))

@app.route('/seller/transaction/<int:id>')
@login_required
@verified_seller_required
def seller_transaction_detail(id):
    transaction = Transaction.query.get_or_404(id)
    if transaction.seller_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('seller_dashboard'))
    
    messages = transaction.messages.order_by(ChatMessage.created_at.asc()).all()
    form = ChatMessageForm()
    return render_template('seller/transaction_detail.html', transaction=transaction, messages=messages, form=form)

@app.route('/seller/mark-delivered/<int:id>', methods=['POST'])
@login_required
@verified_seller_required
def mark_delivered(id):
    transaction = Transaction.query.get_or_404(id)
    if transaction.seller_id != current_user.id or not transaction.can_be_marked_delivered():
        flash('Cannot mark this transaction as delivered.', 'danger')
        return redirect(url_for('seller_transaction_detail', id=id))
    
    # Create notification for buyer
    notification = Notification(
        user_id=transaction.buyer_id,
        transaction_id=transaction.id,
        title='Order Delivered',
        message=f'"{transaction.title}" has been marked as delivered. Please confirm receipt to release payment.'
    )
    db.session.add(notification)
    db.session.commit()
    
    send_transaction_notification(transaction.buyer.email, 'Order Delivered', 
                                f'"{transaction.title}" has been marked as delivered.')
    
    flash('Transaction marked as delivered! Waiting for buyer confirmation.', 'success')
    return redirect(url_for('seller_transaction_detail', id=id))

# Admin routes
@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    pending_sellers = User.query.filter_by(role='seller', is_verified=False).all()
    total_users = User.query.count()
    total_transactions = Transaction.query.count()
    completed_transactions = Transaction.query.filter_by(status='completed').count()
    
    return render_template('admin/dashboard.html', 
                         pending_sellers=pending_sellers,
                         total_users=total_users,
                         total_transactions=total_transactions,
                         completed_transactions=completed_transactions)

@app.route('/admin/verify-seller/<int:id>', methods=['POST'])
@login_required
@admin_required
def verify_seller(id):
    user = User.query.get_or_404(id)
    if user.role != 'seller':
        flash('User is not a seller.', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    action = request.form.get('action')
    if action == 'approve':
        user.is_verified = True
        flash(f'Seller {user.username} has been verified.', 'success')
        send_transaction_notification(user.email, 'Seller Verification Approved', 
                                    'Your seller account has been approved. You can now accept transactions.')
    elif action == 'reject':
        db.session.delete(user)
        flash(f'Seller {user.username} has been rejected and removed.', 'info')
    
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/transactions')
@login_required
@admin_required
def admin_transactions():
    transactions = Transaction.query.order_by(Transaction.created_at.desc()).all()
    return render_template('admin/transaction_management.html', transactions=transactions)

# Chat functionality
@app.route('/chat/send-message/<int:transaction_id>', methods=['POST'])
@login_required
def send_message(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)
    
    # Check if user is involved in this transaction
    if transaction.buyer_id != current_user.id and transaction.seller_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    form = ChatMessageForm()
    if form.validate_on_submit():
        message = ChatMessage(
            transaction_id=transaction_id,
            sender_id=current_user.id,
            message=form.message.data
        )
        db.session.add(message)
        db.session.commit()
        flash('Message sent.', 'success')
    
    # Redirect back to appropriate transaction detail page
    if current_user.is_buyer():
        return redirect(url_for('buyer_transaction_detail', id=transaction_id))
    else:
        return redirect(url_for('seller_transaction_detail', id=transaction_id))

# Server-sent events for real-time notifications
@app.route('/notifications/stream')
@login_required
def notification_stream():
    def event_stream():
        last_check = datetime.utcnow()
        while True:
            # Check for new notifications
            new_notifications = Notification.query.filter(
                Notification.user_id == current_user.id,
                Notification.created_at > last_check,
                Notification.is_read == False
            ).all()
            
            for notif in new_notifications:
                data = {
                    'id': notif.id,
                    'title': notif.title,
                    'message': notif.message,
                    'created_at': notif.created_at.isoformat()
                }
                yield f"data: {json.dumps(data)}\n\n"
            
            last_check = datetime.utcnow()
            time.sleep(5)  # Check every 5 seconds
    
    return Response(event_stream(), mimetype="text/event-stream")

@app.route('/notifications/mark-read/<int:id>', methods=['POST'])
@login_required
def mark_notification_read(id):
    notification = Notification.query.get_or_404(id)
    if notification.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    notification.is_read = True
    db.session.commit()
    return jsonify({'success': True})

@app.route('/transaction/<int:transaction_id>')
@login_required
def transaction_details(transaction_id):
    transaction = Transaction.query.get_or_404(transaction_id)

    # Your role logic
    if transaction.created_by_id == current_user.id:
        role = 'creator'
    elif transaction.buyer_id == current_user.id:
        role = 'buyer'
    elif transaction.seller_id == current_user.id:
        role = 'seller'
    else:
        role = 'guest'

    # Who is the responder
    if transaction.created_by_id == transaction.buyer_id:
        responder_role = 'seller'
    else:
        responder_role = 'buyer'

    messages = ChatMessage.query.filter_by(transaction_id=transaction.id).order_by(ChatMessage.created_at).all()

    return render_template("details.html",
        transaction=transaction,
        messages=messages,
        role=role,
        responder_role=responder_role,
        current_user=current_user
    )


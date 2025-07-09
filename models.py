from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from db import db
from sqlalchemy.dialects.postgresql import JSON


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')  # 'admin' or 'user'
    is_verified = db.Column(db.Boolean, default=False)
    email_verified = db.Column(db.Boolean, default=False)
    email_verification_token = db.Column(db.String(100), unique=True, nullable=True)
    reset_password_token = db.Column(db.String(100), unique=True, nullable=True)
    reset_password_expires = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships using back_populates
    transactions_as_buyer = db.relationship(
        'Transaction',
        back_populates='buyer',
        foreign_keys='Transaction.buyer_id',
        lazy='dynamic'
    )

    transactions_as_seller = db.relationship(
        'Transaction',
        back_populates='seller',
        foreign_keys='Transaction.seller_id',
        lazy='dynamic'
    )

    sent_messages = db.relationship(
        'ChatMessage',
        foreign_keys='ChatMessage.sender_id',
        back_populates='sender',
        lazy='dynamic'
    )

    notifications = db.relationship('Notification', back_populates='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_email_verification_token(self):
        self.email_verification_token = secrets.token_urlsafe(32)
        return self.email_verification_token

    def generate_reset_password_token(self):
        self.reset_password_token = secrets.token_urlsafe(32)
        self.reset_password_expires = datetime.utcnow() + timedelta(hours=1)
        return self.reset_password_token

    def is_admin(self):
        return self.role == 'admin'

    def is_seller(self):
        return False

    def is_buyer(self):
        return False


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=True)
    subcategory = db.Column(db.String(100), nullable=True)
    review_period = db.Column(db.Integer, nullable=True)  # In days
    price = db.Column(db.Float, nullable=True)
    images = db.Column(JSON, nullable=True)   # JSON string of image filenames
    description = db.Column(db.Text, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    payment_done = db.Column(db.Boolean, default=False)


    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    created_by = db.relationship('User', foreign_keys=[created_by_id])
    buyer = db.relationship('User', back_populates='transactions_as_buyer', foreign_keys=[buyer_id])
    seller = db.relationship('User', back_populates='transactions_as_seller', foreign_keys=[seller_id])

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    messages = db.relationship('ChatMessage', back_populates='transaction', lazy='dynamic', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', back_populates='transaction', lazy='dynamic', cascade='all, delete-orphan')

    def can_be_accepted(self):
        return self.status == 'pending' and self.seller_id is None

    def can_be_marked_delivered(self):
        return self.status == 'in_progress' and self.seller_id is not None

    def can_be_completed(self):
        return self.status == 'in_progress'


class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    transaction = db.relationship('Transaction', back_populates='messages')
    sender = db.relationship('User', back_populates='sent_messages')


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', back_populates='notifications')
    transaction = db.relationship('Transaction', back_populates='notifications')


class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)

    buyer_requests = db.relationship('SellerToBuyerRequest', back_populates='product', cascade='all, delete-orphan')


class SellerToBuyerRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    status = db.Column(db.String(10), default='pending')  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    seller = db.relationship('User', foreign_keys=[seller_id], backref='sent_requests')
    buyer = db.relationship('User', foreign_keys=[buyer_id], backref='received_requests')
    product = db.relationship('Product', back_populates='buyer_requests')

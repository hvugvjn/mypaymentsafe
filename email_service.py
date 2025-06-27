from flask import url_for, render_template
from flask_mail import Message
from app import mail, app
import logging

def send_email_verification(email, token):
    """Send email verification message"""
    try:
        with app.app_context():
            msg = Message(
                'Verify Your TrustCart Account',
                recipients=[email]
            )
            verification_url = url_for('verify_email', token=token, _external=True)
            msg.html = render_template('emails/verify_email.html', verification_url=verification_url)
            mail.send(msg)
            logging.info(f"Email verification sent to {email}")
    except Exception as e:
        logging.error(f"Failed to send email verification to {email}: {str(e)}")

def send_password_reset(email, token):
    """Send password reset message"""
    try:
        with app.app_context():
            msg = Message(
                'Reset Your TrustCart Password',
                recipients=[email]
            )
            reset_url = url_for('reset_password', token=token, _external=True)
            msg.html = f"""
            <h2>Password Reset Request</h2>
            <p>Click the link below to reset your password:</p>
            <p><a href="{reset_url}">Reset Password</a></p>
            <p>This link will expire in 1 hour.</p>
            <p>If you didn't request this, please ignore this email.</p>
            """
            mail.send(msg)
            logging.info(f"Password reset sent to {email}")
    except Exception as e:
        logging.error(f"Failed to send password reset to {email}: {str(e)}")

def send_transaction_notification(email, title, message):
    """Send transaction notification"""
    try:
        with app.app_context():
            msg = Message(
                f'TrustCart: {title}',
                recipients=[email]
            )
            msg.html = render_template('emails/transaction_update.html', title=title, message=message)
            mail.send(msg)
            logging.info(f"Transaction notification sent to {email}")
    except Exception as e:
        logging.error(f"Failed to send transaction notification to {email}: {str(e)}")

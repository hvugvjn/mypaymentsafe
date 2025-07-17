import logging
from flask import url_for, render_template
from flask_mail import Message

# Important: You must import the 'mail' object that you initialize in your app.
# If you followed the recommendation to put it in an 'extensions.py' file,
# this import will work.
from extension import mail


def send_email_verification(email, token):
    """Sends an email verification link to the user."""
    try:
        # The application context is already available because this function
        # is called from a Flask route. No need for `with app.app_context()`.
        
        verification_url = url_for('verify_email', token=token, _external=True)
        
        msg = Message(
            subject='Verify Your TrustCart Account',
            recipients=[email]
            # The sender is configured in your app.config, so you don't need it here.
        )
        
        # The render_template function also works automatically inside the app context.
        msg.html = render_template('emails/verify_email.html', verification_url=verification_url)
        
        mail.send(msg)
        logging.info(f"[EMAIL SENT] Verification email sent to {email}")

    except Exception as e:
        # The str(e) gives a more descriptive error message.
        logging.error(f"[EMAIL ERROR] Failed to send verification to {email}: {str(e)}")


def send_password_reset(email, token):
    """Sends a password reset link to the user."""
    # We remove 'app' and 'mail' from the function arguments because they are not needed.
    try:
        reset_url = url_for('reset_password', token=token, _external=True)
        
        msg = Message(
            'Reset Your TrustCart Password',
            recipients=[email]
        )
        
        msg.html = render_template('emails/email_reset.html', link=reset_url)
        
        mail.send(msg)
        logging.info(f"Password reset sent to {email}")

    except Exception as e:
        logging.error(f"Failed to send password reset to {email}: {str(e)}")


def send_transaction_notification(email, title, message):
    """Sends a general transaction notification to the user."""
    # We remove 'app' and 'mail' from the function arguments here as well.
    try:
        msg = Message(
            f'TrustCart: {title}',
            recipients=[email]
        )
        
        msg.html = render_template('emails/transaction_update.html', title=title, message=message)
        
        mail.send(msg)
        logging.info(f"Transaction notification sent to {email}")

    except Exception as e:
        logging.error(f"Failed to send transaction notification to {email}: {str(e)}")
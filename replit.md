# TrustCart - Secure Digital Mediator Platform

## Overview

TrustCart is a Flask-based web application that serves as a secure digital mediator platform for online transactions. It provides an escrow-like service where buyers can safely purchase products or services from verified sellers, with funds held in trust until transaction completion.

## System Architecture

### Frontend Architecture
- **Framework**: Flask with Jinja2 templating
- **UI Framework**: Bootstrap 5 with dark theme
- **Icons**: Feather Icons
- **Real-time Features**: Server-Sent Events (SSE) for notifications
- **JavaScript**: Vanilla JS for chat functionality and notifications

### Backend Architecture
- **Framework**: Flask (Python 3.11)
- **Database ORM**: SQLAlchemy with Flask-SQLAlchemy
- **Authentication**: Flask-Login with session management
- **Form Handling**: WTForms with Flask-WTF
- **Email Service**: Flask-Mail for transactional emails
- **Deployment**: Gunicorn WSGI server

### Database Schema
- **Users**: Authentication, role-based access (buyer/seller/admin), email verification
- **Transactions**: Core business logic with status tracking (pending/in_progress/completed/disputed)
- **Chat Messages**: Real-time communication between buyers and sellers
- **Notifications**: System notifications for transaction updates

## Key Components

### Authentication System
- User registration with email verification
- Password reset functionality with time-limited tokens
- Role-based access control (buyers, sellers, admins)
- Session management with Flask-Login

### Transaction Management
- Escrow-like transaction flow
- Status tracking: pending → in_progress → completed/disputed
- Buyer creates transactions, verified sellers can accept them
- Built-in dispute resolution framework

### Communication System
- Real-time chat between transaction parties
- Server-sent events for live notifications
- Email notifications for transaction updates

### Admin Panel
- Seller verification system
- Transaction oversight and management
- User management capabilities

### Security Features
- CSRF protection with Flask-WTF
- Password hashing with Werkzeug
- Email verification for account activation
- Secure token generation for password resets

## Data Flow

1. **User Registration**: New users register → email verification → account activation
2. **Seller Verification**: Sellers submit for verification → admin approval → can accept transactions
3. **Transaction Creation**: Buyers create transactions with escrow amount → visible to verified sellers
4. **Transaction Acceptance**: Sellers accept transactions → status changes to in_progress
5. **Work Completion**: Sellers mark as delivered → buyers can complete and release funds
6. **Communication**: Real-time chat and notifications throughout the process

## External Dependencies

### Core Dependencies
- Flask 3.1.1 (web framework)
- SQLAlchemy 2.0.41 (database ORM)
- Gunicorn 23.0.0 (WSGI server)
- Flask-Login 0.6.3 (authentication)
- Flask-Mail 0.10.0 (email service)
- WTForms 3.2.1 (form handling)

### Database Options
- SQLite (default/development)
- PostgreSQL (production-ready, configured in .replit)

### Email Configuration
- SMTP support (Gmail configured by default)
- Configurable via environment variables

## Deployment Strategy

### Replit Configuration
- **Runtime**: Python 3.11 with Nix package manager
- **Deployment**: Autoscale deployment target
- **Database**: PostgreSQL and OpenSSL packages included
- **Web Server**: Gunicorn with bind to 0.0.0.0:5000

### Environment Variables Required
- `SESSION_SECRET`: Flask session secret key
- `DATABASE_URL`: Database connection string
- `MAIL_SERVER`, `MAIL_USERNAME`, `MAIL_PASSWORD`: Email configuration

### Production Considerations
- Database connection pooling configured
- ProxyFix middleware for proper headers
- Logging configured for debugging

## User Preferences

Preferred communication style: Simple, everyday language.

## Changelog

Changelog:
- June 27, 2025. Initial setup
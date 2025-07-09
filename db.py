# db.py

import os
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Define the custom base
class Base(DeclarativeBase):
    pass

# Create the SQLAlchemy object with custom base
db = SQLAlchemy(model_class=Base)

# Get the database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# Raise an error if the URL is missing
if not DATABASE_URL:
    raise Exception("DATABASE_URL not found in .env file")

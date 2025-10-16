# In your app/db.py file

# --- CORRECTED IMPORTS ---
# We DO NOT import 'db' from here. It is created in __init__.py.
from . import db
from flask_login import UserMixin
import datetime

# --- User Model (Merged and Updated) ---
# This model combines your original User model with the new relationships needed for budgeting.
class User(UserMixin, db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(1000), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)
    session_id = db.Column(db.String(50), nullable=False) # Kept from your original model

    # --- NEW: Relationships for budgeting feature ---
    statements = db.relationship("Statements", backref="user", lazy=True, cascade="all, delete-orphan")
    categories = db.relationship("Category", backref="user", lazy=True, cascade="all, delete-orphan")
    budgets = db.relationship("Budget", backref="user", lazy=True, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User Id:{self.id}, Email:{self.email}>"

# --- VisitorStats Model (Unchanged from your original) ---
class VisitorStats(db.Model):
    __tablename__ = "visitor_stats"
    id = db.Column(db.Integer, primary_key=True)
    browser = db.Column(db.String(100))
    device = db.Column(db.String(100))
    operating_system = db.Column(db.String(100))
    is_bot = db.Column(db.Boolean())
    date = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __repr__(self) -> str:
        return f"<VisitorStats Id:{self.id}>"

# --- Admin Model (Unchanged from your original) ---
class Admin(db.Model):
    __tablename__ = "admin"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.Text, nullable=False)
    session_id = db.Column(db.String(50), nullable=False, unique=True)

    def __repr__(self) -> str:
        return f"<Admin Id:{self.id}, Username:{self.username}>"

# --- Statements Model (Updated with Category) ---
# This is your original model, but with the new category_id foreign key added.
class Statements(db.Model):
    __tablename__ = "statements"
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False) # Kept your original Numeric type
    operation_time = db.Column(db.DateTime, nullable=False, default=datetime.datetime.utcnow)
    statement_id = db.Column(db.String(50), nullable=False, unique=True)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    
    # --- NEW: Foreign Key to Category ---
    category_id = db.Column(db.Integer, db.ForeignKey("category.id", ondelete="CASCADE"), nullable=False)

    def __repr__(self) -> str:
        return f"<Statement Id:{self.id}, Desc:{self.description}>"

# --- NEW: Category Model ---
class Category(db.Model):
    __tablename__ = "category"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)

    # Ensures a user can't have two categories with the same name
    __table_args__ = (db.UniqueConstraint('name', 'user_id', name='_user_category_uc'),)

    def __repr__(self) -> str:
        return f"<Category Id:{self.id}, Name:{self.name}>"

# --- NEW: Budget Model ---
class Budget(db.Model):
    __tablename__ = "budget"
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False) # Using Numeric for consistency
    period = db.Column(db.String(50), nullable=False, default='monthly')
    user_id = db.Column(db.Integer, db.ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("category.id", ondelete="CASCADE"), nullable=False)

    # Ensures a user can only have one budget per category
    __table_args__ = (db.UniqueConstraint('user_id', 'category_id', name='_user_category_budget_uc'),)

    def __repr__(self) -> str:
        return f"<Budget Id:{self.id}, Amount:{self.amount}>"
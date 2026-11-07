from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    categories = db.relationship('Category', backref='user', lazy=True)
    budgets = db.relationship('Budget', backref='user', lazy=True)
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    wallets = db.relationship('Wallet', backref='user', lazy=True)

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    icon = db.Column(db.String(50), nullable=True)

    transactions = db.relationship('Transaction', backref='category', lazy=True)
    budgets = db.relationship('Budget', backref='category', lazy=True)

class Budget(db.Model):
    __tablename__ = 'budgets'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    month = db.Column(db.String(7), nullable=False) # Format: YYYY-MM
    amount = db.Column(db.Float, nullable=False)

class Wallet(db.Model):
    __tablename__ = 'wallets'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    balance = db.Column(db.Float, default=0.0)

    transactions = db.relationship('Transaction', backref='wallet', lazy=True)

class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True) 
    wallet_id = db.Column(db.Integer, db.ForeignKey('wallets.id'), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(10), nullable=False) # 'expense' or 'income'
    txn_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    note = db.Column(db.String(255), nullable=True)

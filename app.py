import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from sqlalchemy import func
import csv
import io

from models import db, User, Category, Budget, Wallet, Transaction

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expense_tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Login Failed. Check email and password.', 'danger')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email address already exists', 'danger')
            return redirect(url_for('signup'))
        
        new_user = User(email=email, name=name, password_hash=generate_password_hash(password, method='pbkdf2:sha256'))
        db.session.add(new_user)
        db.session.commit()
        
        # Seed default categories & wallets
        db.session.add_all([
            Category(user_id=new_user.id, name='Food', icon='🍔'),
            Category(user_id=new_user.id, name='Transport', icon='🚌'),
            Category(user_id=new_user.id, name='Entertainment', icon='🎬'),
            Wallet(user_id=new_user.id, name='Cash', balance=0),
            Wallet(user_id=new_user.id, name='Bank', balance=0)
        ])
        db.session.commit()
        flash('Account created successfully', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    today = date.today()
    current_month = today.strftime('%Y-%m')
    
    # Get total spend today
    today_txns = Transaction.query.filter_by(user_id=current_user.id, txn_date=today, type='expense').all()
    today_total = sum(t.amount for t in today_txns)
    
    # Get budget vs spend for current month
    budgets = Budget.query.filter_by(user_id=current_user.id, month=current_month).all()
    
    budget_data = []
    for b in budgets:
        # get spend for this category in current month
        start_date = date(today.year, today.month, 1)
        # Handle next month logic for end_date safely...
        next_month = today.month + 1 if today.month < 12 else 1
        next_year = today.year if today.month < 12 else today.year + 1
        end_date = date(next_year, next_month, 1)
        
        spend = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == current_user.id,
            Transaction.category_id == b.category_id,
            Transaction.type == 'expense',
            Transaction.txn_date >= start_date,
            Transaction.txn_date < end_date
        ).scalar() or 0.0
        
        percent = (spend / b.amount) * 100 if b.amount > 0 else 0
        budget_data.append({
            'category': b.category.name,
            'budget': b.amount,
            'spend': spend,
            'percent': min(percent, 100),
            'alert': 'danger' if percent >= 100 else 'warning' if percent >= 80 else 'success'
        })
        
        # In-app alert flash
        if percent >= 100:
            flash(f'Budget for {b.category.name} is fully consumed!', 'danger')
        elif percent >= 80:
            flash(f'Warning: {b.category.name} budget is at {percent:.1f}%', 'warning')

    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.txn_date.desc(), Transaction.id.desc()).limit(10).all()
    categories = Category.query.filter_by(user_id=current_user.id).all()
    wallets = Wallet.query.filter_by(user_id=current_user.id).all()
    total_balance = sum(w.balance for w in wallets)
    
    # Calculate Monthly Income vs Expense Alert
    start_date = date(today.year, today.month, 1)
    next_month = today.month + 1 if today.month < 12 else 1
    next_year = today.year if today.month < 12 else today.year + 1
    end_date = date(next_year, next_month, 1)
    
    month_txns = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.txn_date >= start_date,
        Transaction.txn_date < end_date
    ).all()
    
    monthly_income = sum(t.amount for t in month_txns if t.type == 'income')
    monthly_expense = sum(t.amount for t in month_txns if t.type == 'expense')
    
    if monthly_income > 0:
        if monthly_expense >= monthly_income:
            flash(f'🚨 Critical: Your expenses this month (₹{monthly_expense:.2f}) have exceeded your income (₹{monthly_income:.2f})!', 'danger')
        elif monthly_expense >= 0.8 * monthly_income:
            flash(f'⚠️ Warning: Your expenses this month (₹{monthly_expense:.2f}) have exceeded 80% of your income!', 'warning')
            
    return render_template('dashboard.html', total_balance=total_balance, today_total=today_total, budget_data=budget_data, transactions=transactions, categories=categories, wallets=wallets, today_date=today.strftime('%Y-%m-%d'))

@app.route('/add_transaction', methods=['POST'])
@login_required
def add_transaction():
    amount = float(request.form.get('amount'))
    category_name = request.form.get('category_name')
    wallet_id = request.form.get('wallet_id')
    if not wallet_id:
        default_wallet = Wallet.query.filter_by(user_id=current_user.id).first()
        if default_wallet:
            wallet_id = default_wallet.id
            
    txn_type = request.form.get('type')
    txn_date_str = request.form.get('txn_date')
    note = request.form.get('note')
    
    txn_date = datetime.strptime(txn_date_str, '%Y-%m-%d').date()
    
    category_id = None
    if category_name and category_name.strip():
        cat_name = category_name.strip()
        cat = Category.query.filter(func.lower(Category.name) == cat_name.lower(), Category.user_id == current_user.id).first()
        if not cat:
            cat = Category(user_id=current_user.id, name=cat_name.title(), icon='📌')
            db.session.add(cat)
            db.session.flush()
        category_id = cat.id
    
    txn = Transaction(
        user_id=current_user.id,
        category_id=category_id if category_id else None,
        wallet_id=wallet_id if wallet_id else None,
        amount=amount,
        type=txn_type,
        txn_date=txn_date,
        note=note
    )
    db.session.add(txn)
    
    # Update wallet balance
    if wallet_id:
        wallet = Wallet.query.get(wallet_id)
        if txn_type == 'expense':
            wallet.balance -= amount
        else:
            wallet.balance += amount
            
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/delete_transaction/<int:txn_id>', methods=['POST'])
@login_required
def delete_transaction(txn_id):
    txn = Transaction.query.get_or_404(txn_id)
    if txn.user_id != current_user.id:
        flash('Unauthorized to delete this transaction.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Revert wallet balance
    if txn.wallet_id:
        wallet = Wallet.query.get(txn.wallet_id)
        if txn.type == 'expense':
            wallet.balance += txn.amount
        else:
            wallet.balance -= txn.amount
            
    db.session.delete(txn)
    db.session.commit()
    flash('Transaction deleted successfully.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/history')
@login_required
def history():
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.txn_date.desc(), Transaction.id.desc()).all()
    return render_template('history.html', transactions=transactions)

@app.route('/insights', methods=['GET'])
@login_required
def insights():
    month_str = request.args.get('month', date.today().strftime('%Y-%m'))
    try:
        year, month = map(int, month_str.split('-'))
        start_date = date(year, month, 1)
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1
        end_date = date(next_year, next_month, 1)
    except Exception:
        start_date = date(date.today().year, date.today().month, 1)
        end_date = date.today()
    
    # Fetch Data for Charts
    txns = Transaction.query.filter(
        Transaction.user_id == current_user.id,
        Transaction.type == 'expense',
        Transaction.txn_date >= start_date,
        Transaction.txn_date < end_date
    ).all()
    
    # 1. Pie chart of spend split (Category wise)
    category_totals = {}
    for t in txns:
        cat_name = t.category.name if t.category else 'Unknown'
        category_totals[cat_name] = category_totals.get(cat_name, 0) + t.amount
        
    pie_labels = list(category_totals.keys())
    pie_data = list(category_totals.values())
    
    # 2. Line chart of daily spend
    daily_totals = {}
    for t in txns:
        d_str = t.txn_date.strftime('%Y-%m-%d')
        daily_totals[d_str] = daily_totals.get(d_str, 0) + t.amount
        
    # Sort by date
    daily_sorted = sorted(daily_totals.items())
    line_labels = [d[0] for d in daily_sorted]
    line_data = [d[1] for d in daily_sorted]
    
    # 3. Bar chart vs budget
    budgets = Budget.query.filter_by(user_id=current_user.id, month=month_str).all()
    bar_labels = []
    bar_budget = []
    bar_actual = []
    
    for b in budgets:
        cat_name = b.category.name
        bar_labels.append(cat_name)
        bar_budget.append(b.amount)
        bar_actual.append(category_totals.get(cat_name, 0))
        
    return render_template('insights.html', 
                           month_str=month_str,
                           pie_labels=pie_labels, pie_data=pie_data,
                           line_labels=line_labels, line_data=line_data,
                           bar_labels=bar_labels, bar_budget=bar_budget, bar_actual=bar_actual)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        # Add budget
        category_name = request.form.get('category_name')
        amount = request.form.get('amount')
        month = request.form.get('month')
        if category_name and amount and month:
            cat_name = category_name.strip()
            cat = Category.query.filter(func.lower(Category.name) == cat_name.lower(), Category.user_id == current_user.id).first()
            if not cat:
                cat = Category(user_id=current_user.id, name=cat_name.title(), icon='📌')
                db.session.add(cat)
                db.session.flush()
            
            b = Budget.query.filter_by(user_id=current_user.id, category_id=cat.id, month=month).first()
            if b:
                b.amount = float(amount)
            else:
                new_budget = Budget(user_id=current_user.id, category_id=cat.id, month=month, amount=float(amount))
                db.session.add(new_budget)
            db.session.commit()
            flash('Budget updated successfully.', 'success')
            return redirect(url_for('settings'))
            
    categories = Category.query.filter_by(user_id=current_user.id).all()
    budgets = Budget.query.filter_by(user_id=current_user.id).order_by(Budget.month.desc()).all()
    return render_template('settings.html', categories=categories, budgets=budgets)

@app.route('/delete_budget/<int:budget_id>', methods=['POST'])
@login_required
def delete_budget(budget_id):
    budget = Budget.query.get_or_404(budget_id)
    if budget.user_id != current_user.id:
        flash('Unauthorized to delete this budget.', 'danger')
        return redirect(url_for('settings'))
    
    db.session.delete(budget)
    db.session.commit()
    flash('Budget deleted successfully.', 'success')
    return redirect(url_for('settings'))

@app.route('/export')
@login_required
def export_csv():
    txns = Transaction.query.filter_by(user_id=current_user.id).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Type', 'Category', 'Amount', 'Note'])
    for t in txns:
        writer.writerow([
            t.txn_date.strftime('%Y-%m-%d'),
            t.type,
            t.category.name if t.category else '',
            t.amount,
            t.note
        ])
    
    # Create a BytesIO object because send_file expects binary mode for attachments usually, 
    # but since Flask 2.0 send_file can take string/bytes. We will return a Response.
    from flask import Response
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=transactions.csv"}
    )

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)

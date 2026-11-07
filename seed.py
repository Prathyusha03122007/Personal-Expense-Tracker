import random
from datetime import date, timedelta
from werkzeug.security import generate_password_hash
from app import app, db
from models import User, Category, Budget, Wallet, Transaction

def seed_data():
    with app.app_context():
        # Clean db
        db.drop_all()
        db.create_all()

        # Create Demo User
        user = User(name='Demo Student', email='student@example.com', password_hash=generate_password_hash('password123', method='pbkdf2:sha256'))
        db.session.add(user)
        db.session.commit()

        # Create Categories
        cats_data = [
            ('Food', '🍔'),
            ('Transport', '🚌'),
            ('Entertainment', '🎬'),
            ('Groceries', '🛒'),
            ('Utilities', '💡')
        ]
        categories = []
        for name, icon in cats_data:
            cat = Category(user_id=user.id, name=name, icon=icon)
            db.session.add(cat)
            categories.append(cat)
        db.session.commit()

        # Create Wallets
        wallet1 = Wallet(user_id=user.id, name='Cash', balance=1500)
        wallet2 = Wallet(user_id=user.id, name='Bank', balance=12000)
        db.session.add_all([wallet1, wallet2])
        db.session.commit()

        # Create Budgets for last 3 months and current month
        today = date.today()
        months = []
        for i in range(3):
            # Calculate past months
            month_date = today.replace(day=1) - timedelta(days=30*i)
            months.append(month_date.strftime('%Y-%m'))
        months.append(today.strftime('%Y-%m')) # Ensure current month is there

        for month in set(months):
            for cat in categories:
                amount = random.randint(1000, 5000)
                b = Budget(user_id=user.id, category_id=cat.id, month=month, amount=amount)
                db.session.add(b)
        db.session.commit()

        # Create Transactions for the last 90 days
        start_date = today - timedelta(days=90)
        notes = ['Lunch', 'Bus ticket', 'Movie', 'Snacks', 'Electricity Bill', 'Coffee', 'Uber', 'Stationery']
        
        for i in range(90):
            current_date = start_date + timedelta(days=i)
            # Add 1 to 3 expenses per day
            num_txns = random.randint(1, 3)
            for _ in range(num_txns):
                cat = random.choice(categories)
                wallet = random.choice([wallet1, wallet2])
                amount = random.uniform(50.0, 500.0)
                
                txn = Transaction(
                    user_id=user.id,
                    category_id=cat.id,
                    wallet_id=wallet.id,
                    amount=round(amount, 2),
                    type='expense',
                    txn_date=current_date,
                    note=random.choice(notes)
                )
                db.session.add(txn)
                wallet.balance -= round(amount, 2)
                
            # Random Income once a week
            if i % 7 == 0:
                income_amt = random.uniform(2000.0, 5000.0)
                txn = Transaction(
                    user_id=user.id,
                    category_id=None,
                    wallet_id=wallet2.id,
                    amount=round(income_amt, 2),
                    type='income',
                    txn_date=current_date,
                    note='Allowance / Part-time'
                )
                db.session.add(txn)
                wallet2.balance += round(income_amt, 2)

        db.session.commit()
        print("Database seeded successfully with 3 months of data.")
        print("Login with email: student@example.com / password: password123")

if __name__ == '__main__':
    seed_data()

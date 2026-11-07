from app import app, db
from models import User, Category, Budget, Wallet, Transaction

def clear_dummy_data():
    with app.app_context():
        # Find the demo user
        demo_user = User.query.filter_by(email='student@example.com').first()
        if demo_user:
            print("Found demo user. Deleting dummy data...")
            # Delete transactions
            Transaction.query.filter_by(user_id=demo_user.id).delete()
            # Delete budgets
            Budget.query.filter_by(user_id=demo_user.id).delete()
            # Delete wallets
            Wallet.query.filter_by(user_id=demo_user.id).delete()
            # Delete categories
            Category.query.filter_by(user_id=demo_user.id).delete()
            # Delete user
            db.session.delete(demo_user)
            db.session.commit()
            print("Dummy data successfully removed.")
        else:
            print("Demo user not found. No dummy data to remove.")

if __name__ == '__main__':
    clear_dummy_data()

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class UserModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    mess_code = db.Column(db.String(50))
    is_admin = db.Column(db.Boolean, default=False)
    deposit = db.Column(db.Float, default=0)
    balance = db.Column(db.Float, default=0.0)

    
class MealRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user_model.id'))
    date = db.Column(db.Date, nullable=False)
    breakfast = db.Column(db.Boolean, default=False)
    lunch = db.Column(db.Boolean, default=False)
    dinner = db.Column(db.Boolean, default=False)
    # approved_meal_count = db.Column(db.Integer, default=0)

class BazaarEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    total_bazaar = db.Column(db.Float)
    shared_cost = db.Column(db.Float)
    remarks = db.Column(db.String(300))
    mess_code = db.Column(db.String(50), nullable=False)

    # __tablename__ = 'user'
    # deposit_history = db.relationship('DepositHistory', back_populates='user')

# class DepositHistory(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Ensure 'user.id' matches the UserModel
#     deposit_amount = db.Column(db.Float, nullable=False)
#     deposit_date = db.Column(db.Date, nullable=False)

#     __tablename__ = 'deposit_history'
#     user = db.relationship('UserModel', back_populates='deposit_history') 



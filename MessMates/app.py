from flask import Flask, render_template, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, UserModel, MealRequest, BazaarEntry
from datetime import date, timedelta
from sqlalchemy import func


app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///messmates.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
from flask_migrate import Migrate
migrate = Migrate(app, db)


@app.route('/')
def index():
    return redirect('/login')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = UserModel.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect('/home')
        return "Invalid credentials"
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        mess_code = request.form['mess_code']
        is_admin = 'is_admin' in request.form
        user = UserModel(username=username, email=email, password=password, mess_code=mess_code,is_admin=is_admin)
        db.session.add(user)
        db.session.commit()
        return redirect('/login')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


@app.route('/home', methods=['GET', 'POST'])
def home():
    if 'user_id' not in session:
        return redirect('/login')
    user = UserModel.query.get(session['user_id'])

    today = date.today()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'meal':
            existing = MealRequest.query.filter_by(user_id=user.id, date=today).first()
            if not existing:
                breakfast = 'breakfast' in request.form
                lunch = 'lunch' in request.form
                dinner = 'dinner' in request.form

                request_entry = MealRequest(user_id=user.id, date=today,
                                            breakfast=breakfast,
                                            lunch=lunch,
                                            dinner=dinner)
                db.session.add(request_entry)
                db.session.commit()

        elif action == 'deposit':
            amount = float(request.form.get('amount'))
            if amount > 0:
                user.deposit += amount
                db.session.commit()

    return render_template('home.html', user=user)


@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect('/login')

    user = UserModel.query.get(session['user_id'])

    # Get Total Meals
    today = date.today()

    # breakfast + lunch + dinner
    total_meals = (
        MealRequest.query.filter_by(user_id=user.id, breakfast=True).count() +
        MealRequest.query.filter_by(user_id=user.id, lunch=True).count() +
        MealRequest.query.filter_by(user_id=user.id, dinner=True).count()
    )

    # Total Deposit for the user
    total_deposit = user.deposit

    # Get Meal Rate- Monthly Stats logic
    start_of_month = today.replace(day=1)
    total_bazaar = db.session.query(func.sum(BazaarEntry.total_bazaar)) \
        .filter(BazaarEntry.date >= start_of_month).scalar() or 0
    total_meals_this_month = MealRequest.query.filter(MealRequest.date >= start_of_month).count()

    # Calculate meal rate 
    meal_rate = total_bazaar / total_meals_this_month if total_meals_this_month else 0

    # Calculate Meal Cost
    total_meal_cost = meal_rate * total_meals

    # Get Shared Cost for the user's mess code
    shared_cost_for_mess = db.session.query(func.sum(BazaarEntry.shared_cost)) \
        .filter(BazaarEntry.date >= start_of_month, BazaarEntry.mess_code == user.mess_code).scalar() or 0

    # Calculate Total Cost 
    total_cost = total_meal_cost + shared_cost_for_mess

    # non-neg due
    due = max(0, total_cost - total_deposit)  # Ensures due is not negative

    # stats render
    stats = {
        'total_meal': total_meals,
        'total_deposit': total_deposit,
        'cost': round(total_cost, 2),  # Total cost now includes both meal and shared cost
        'due': round(due, 2)
    }

    return render_template('profile.html', user=user, stats=stats)

   


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'user_id' not in session:
        return redirect('/login')

    user = UserModel.query.get(session['user_id'])
    if not user.is_admin:
        return "Unauthorized", 403

    today = date.today()

    mess_code = user.mess_code 

    # save bazaar entry
    if request.method == 'POST':
        total_bazaar = float(request.form['total_bazaar'])
        shared_cost = float(request.form['shared_cost'])  # Ensure shared_cost is fetched here
        remarks = request.form['remarks']

        # Entry to the db
        bazaar = BazaarEntry(
            date=today,
            total_bazaar=total_bazaar,
            shared_cost=shared_cost,
            remarks=remarks,
            mess_code=mess_code  
        )
        db.session.add(bazaar)
        db.session.commit()
        
        # sharing the same mess code
        users_in_mess = UserModel.query.filter_by(mess_code=mess_code).all()

        # Calculate shared cost/user
        shared_cost_per_user = shared_cost / len(users_in_mess) if len(users_in_mess) > 0 else 0

        
        for u in users_in_mess:
            u.balance -= shared_cost_per_user  # Deduct shared cost 
            db.session.commit()


    today_meals = {
        'breakfast': MealRequest.query.filter_by(date=today, breakfast=True).count(),
        'lunch': MealRequest.query.filter_by(date=today, lunch=True).count(),
        'dinner': MealRequest.query.filter_by(date=today, dinner=True).count()
    }

    #  Monthly stats 
    start_of_month = today.replace(day=1)

    # All meal request// current month
    meals = MealRequest.query.filter(MealRequest.date >= start_of_month).all()
    total_meals = sum([int(m.breakfast) + int(m.lunch) + int(m.dinner) for m in meals])

    # Total bazaar and shared cost// month
    total_bazaar = db.session.query(func.sum(BazaarEntry.total_bazaar)) \
        .filter(BazaarEntry.date >= start_of_month).scalar() or 0

    total_shared = db.session.query(func.sum(BazaarEntry.shared_cost)) \
        .filter(BazaarEntry.date >= start_of_month).scalar() or 0

    # Total deposits by all users
    total_deposit = db.session.query(func.sum(UserModel.deposit)).scalar() or 0

    # Meal rate and balance
    meal_rate = total_bazaar / total_meals if total_meals else 0
    total_meal_cost = meal_rate * total_meals
    mess_balance = total_deposit - (total_meal_cost + total_shared)

    monthly = {
        'total_meal': total_meals,
        'meal_rate': round(meal_rate, 2),
        'total_meal_cost': round(total_meal_cost, 2),
        'total_deposit': round(total_deposit, 2),
        'total_shared_cost': round(total_shared, 2),
        'mess_balance': round(mess_balance, 2)
    }

    return render_template('admin.html',
                           user=user,
                           today=today,
                           today_meals=today_meals,
                           monthly=monthly)

#----------------------------------------------------APIs-------------------------------------------------------------------
#GET users by messcode
@app.route('/users/<mess_code>', methods=['GET'])
def get_users_by_mess_code(mess_code):
    
    users = UserModel.query.filter_by(mess_code=mess_code).all()

    
    if not users:
        return jsonify({"message": "No users found for this mess code"}), 404

    
    users_data = [{
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'mess_code': user.mess_code,
        'mess balance': user.balance,
        'deposit': user.deposit
    } for user in users]

    return jsonify(users_data)
#------------------------------------------------------------------------------------------------------------------------

# from datetime import date

# @app.route('/deposit-history/<int:user_id>', methods=['GET'])
# def deposit_history(user_id):
#     # Ensure user is logged in (for security purposes)
#     if 'user_id' not in session:
#         return redirect('/login')

#     # Get the user (if exists)
#     user = UserModel.query.get(user_id)
#     if not user:
#         return jsonify({'message': 'User not found'}), 404

#     # Get today's date and start of the current month
#     today = date.today()
#     start_of_month = today.replace(day=1)

#     # Fetch deposit history for the user in the current month
#     deposits = DepositHistory.query.filter(
#         DepositHistory.user_id == user_id,
#         DepositHistory.deposit_date >= start_of_month
#     ).all()

#     # Prepare deposit data for response
#     deposit_history = []
#     for deposit in deposits:
#         deposit_data = {
#             'deposit_amount': deposit.deposit_amount,
#             'deposit_date': deposit.deposit_date.strftime('%Y-%m-%d')
#         }
#         deposit_history.append(deposit_data)

#     return jsonify({
#         'user_id': user_id,
#         'deposit_history': deposit_history
#     })


#-------------------------------------------------------------------------------------------------------------------------
@app.route('/admins', methods=['GET'])
def get_admins():
    admins = UserModel.query.filter_by(is_admin=True).all()
    result = []

    for admin in admins:
        result.append({
            'username': admin.username,
            'email': admin.email,
            'mess_code': admin.mess_code
        })

    return jsonify(result)
#----------------------------------------------------------------------------------------------------------
from flask import jsonify
from datetime import date
from models import MealRequest, UserModel  # Assuming you've imported these

@app.route('/meal-requests', methods=['GET'])
def get_meal_requests():
    start_of_month = date.today().replace(day=1)
    meal_requests = MealRequest.query.filter(MealRequest.date >= start_of_month).all()

    data = []
    for m in meal_requests:
        user = UserModel.query.get(m.user_id)
        data.append({
            'username': user.username if user else 'Unknown',
            'date': m.date.strftime('%Y-%m-%d'),
            'breakfast': m.breakfast,
            'lunch': m.lunch,
            'dinner': m.dinner
        })

    return jsonify(data)

#----------------------------------------------------------------------------------------------------------
@app.route('/total-users/<mess_code>', methods=['GET'])
def get_total_users(mess_code):
    users = UserModel.query.filter_by(mess_code=mess_code).all()
    return jsonify({
        'mess_code': mess_code,
        'total_users': len(users)
    })

#----------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
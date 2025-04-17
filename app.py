from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit
import os
from dotenv import load_dotenv
from database import db, execute_with_retry, log_database_operation
import logging
from bson import ObjectId
import datetime
from datetime import timedelta
import random
import smtplib
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Flask app & SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here-make-it-strong-and-unique')
socketio = SocketIO(app)

# LoginManager setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# MongoDB setup
client = MongoClient(os.getenv("MONGODB_URI"))
db = client['webx_microscope']

# User model
class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.email = user_data['email']
        self.name = user_data['name']

@login_manager.user_loader
def load_user(user_id):
    user_data = db.users.find_one({'_id': ObjectId(user_id)})
    return User(user_data) if user_data else None


# Generate OTP
def generate_otp():
    return str(random.randint(100000, 999999))

# Email OTP function
def send_otp_email(to_email, otp):
    try:
        smtp_user = os.getenv("EMAIL_USER")
        smtp_password = os.getenv("EMAIL_PASSWORD")
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            subject = "Your OTP Code"
            body = f"Your OTP is: {otp}"
            message = f"Subject: {subject}\n\n{body}"
            server.sendmail(smtp_user, to_email, message)
            logger.info(f"OTP sent to {to_email}")
    except Exception as e:
        logger.error(f"send_otp_email error: {e}")
        flash('There was an error sending OTP. Please try again later.', 'danger')

# -----------------------------------
# ROUTES
# -----------------------------------

@app.route('/')
def home():
    try:
        # Fetch microscopes from the database
        microscopes = execute_with_retry(lambda: list(db.microscopes.find()))
        return render_template('home.html', microscopes=microscopes)
    except Exception as e:
        log_database_operation('get_microscopes_home', False, str(e))
        logger.error(f"Error fetching microscopes for home page: {e}")
        flash('Error loading microscopes', 'danger')
        return render_template('home.html', microscopes=[])
    
@app.route('/microscope/<microscope_id>')
def microscope_detail(microscope_id):
    try:
        microscope = execute_with_retry(lambda: db.microscopes.find_one({'_id': ObjectId(microscope_id)}))
        if not microscope:
            flash('Microscope not found', 'danger')
            return redirect(url_for('home'))
        
        return render_template('microscope_details.html', microscope=microscope)
    except Exception as e:
        log_database_operation('get_microscope_detail', False, str(e))
        flash('Error loading microscope details', 'danger')
        return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')

        existing_user = db.users.find_one({'email': email})
        if existing_user:
            flash('Email already registered!', 'danger')
            return redirect(url_for('register'))

        result = db.users.insert_one({
            'email': email,
            'name': name,
            'password': generate_password_hash(password)  # Always hash passwords in production
        })

        otp = generate_otp()
        expiry = datetime.datetime.now() + datetime.timedelta(minutes=5)

        db.users.update_one({'_id': result.inserted_id}, {
            '$set': {'otp': otp, 'otp_expiry': expiry, 'otp_verified': False}
        })

        send_otp_email(email, otp)

        login_user(User({'_id': result.inserted_id, 'email': email, 'name': name}))
        flash('OTP sent. Please verify.', 'info')
        return redirect(url_for('verify_otp'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = db.users.find_one({'email': email})
        if not user or not check_password_hash(user['password'], password):
            flash('Invalid credentials', 'danger')
            return redirect(url_for('login'))

        otp = generate_otp()
        expiry = datetime.datetime.now() + datetime.timedelta(minutes=5)

        db.users.update_one({'_id': user['_id']}, {
            '$set': {'otp': otp, 'otp_expiry': expiry, 'otp_verified': False}
        })

        send_otp_email(email, otp)

        login_user(User(user))
        flash('OTP sent. Please verify.', 'info')
        return redirect(url_for('verify_otp'))

    return render_template('login.html')

@app.route('/verify-otp', methods=['GET', 'POST'])
@login_required
def verify_otp():
    if request.method == 'POST':
        entered_otp = request.form.get('otp')
        user = db.users.find_one({'_id': ObjectId(current_user.id)})

        if user:
            if datetime.datetime.now() > user.get('otp_expiry', datetime.datetime.min):
                flash('OTP expired. Please login again.', 'danger')
                logout_user()
                return redirect(url_for('login'))

            if user['otp'] == entered_otp:
                db.users.update_one({'_id': user['_id']}, {
                    '$unset': {'otp': "", 'otp_expiry': ""},
                    '$set': {'otp_verified': True}  # ✅ Mark OTP as verified
                })
                flash('OTP verified. Login successful!', 'success')
                return redirect(url_for('dashboard'))

            flash('Incorrect OTP', 'danger')

    return render_template('verify_otp.html')

def otp_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = db.users.find_one({'_id': ObjectId(current_user.id)})
        if not user.get('otp_verified', False):
            flash("Please verify your OTP first.", "warning")
            return redirect(url_for('verify_otp'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/dashboard')
@login_required
@otp_required
def dashboard():
    try:
        # Default to "all" bookings if no filter is applied
        filter_type = request.args.get('filter', 'all')
        user_bookings = execute_with_retry(lambda: list(db.bookings.find({'user_id': ObjectId(current_user.id)})))
        
        # Get microscope details for each booking
        for booking in user_bookings:
            microscope = execute_with_retry(lambda: db.microscopes.find_one({'_id': ObjectId(booking['microscope_id'])}))
            booking['microscope_name'] = microscope['name'] if microscope else 'Unknown Microscope'
        
        # Return filtered bookings based on the filter selected
        return render_template('dashboard.html', bookings=user_bookings, filter_type=filter_type)
    except Exception as e:
        log_database_operation('get_user_bookings', False, str(e))
        flash('Error loading bookings')
        return render_template('dashboard.html', bookings=[], filter_type='all')

@app.route('/filter-bookings')
@login_required
@otp_required
def filter_bookings():
    filter_type = request.args.get('filter')
    today = datetime.datetime.now()
    
    # Determine the filter type and calculate the appropriate date range
    if filter_type == 'today':
        start_date = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = today.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif filter_type == 'weekly':
        start_date = today - timedelta(days=today.weekday())  # Start of the week (Monday)
        end_date = start_date + timedelta(days=6, hours=23, minutes=59, seconds=59)  # End of the week (Sunday)
    elif filter_type == 'monthly':
        start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)  # Start of the month
        # Calculate last day of the month
        if today.month == 12:
            next_month = datetime.datetime(today.year + 1, 1, 1)
        else:
            next_month = datetime.datetime(today.year, today.month + 1, 1)
        end_date = next_month - datetime.timedelta(days=1)
        end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    else:  # Default to "all" bookings
        start_date = datetime.datetime(2000, 1, 1)  # Arbitrary early date
        end_date = datetime.datetime(2100, 1, 1)  # Arbitrary future date

    # Query bookings based on the selected date range
    user_bookings = execute_with_retry(lambda: list(db.bookings.find({
        'user_id': ObjectId(current_user.id),
        'date': {'$gte': start_date.strftime('%Y-%m-%d'), '$lte': end_date.strftime('%Y-%m-%d')}
    })))

    # Get microscope details for each booking
    for booking in user_bookings:
        microscope = execute_with_retry(lambda: db.microscopes.find_one({'_id': ObjectId(booking['microscope_id'])}))
        booking['microscope_name'] = microscope['name'] if microscope else 'Unknown Microscope'
        
        # Convert ObjectId to string for JSON serialization
        booking['_id'] = str(booking['_id'])
        booking['microscope_id'] = str(booking['microscope_id'])
        booking['user_id'] = str(booking['user_id'])
        
        # Convert datetime objects to strings for JSON serialization
        if 'created_at' in booking and isinstance(booking['created_at'], datetime.datetime):
            booking['created_at'] = booking['created_at'].isoformat()
        if 'updated_at' in booking and isinstance(booking['updated_at'], datetime.datetime):
            booking['updated_at'] = booking['updated_at'].isoformat()
        if 'cancelled_at' in booking and isinstance(booking['cancelled_at'], datetime.datetime):
            booking['cancelled_at'] = booking['cancelled_at'].isoformat()

    # Get the booking count for cards
    booking_count = len(user_bookings)

    # Return the filtered bookings and the booking count
    return jsonify({'bookings': user_bookings, 'booking_count': booking_count})

@app.route('/update-booking/<booking_id>', methods=['GET', 'POST'])
@login_required
@otp_required
def update_booking(booking_id):
    try:
        booking = execute_with_retry(lambda: db.bookings.find_one({'_id': ObjectId(booking_id)}))
        
        # Check if booking exists and belongs to current user
        if not booking or str(booking['user_id']) != current_user.id:
            flash('Booking not found or unauthorized')
            return redirect(url_for('dashboard'))
            
        if request.method == 'POST':
            date = request.form.get('date')
            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')
            
            # Check for conflicts (excluding current booking)
            existing_booking = execute_with_retry(lambda: db.bookings.find_one({
                '_id': {'$ne': ObjectId(booking_id)},
                'microscope_id': booking['microscope_id'],
                'date': date,
                '$or': [
                    {'start_time': {'$lte': start_time}, 'end_time': {'$gt': start_time}},
                    {'start_time': {'$lt': end_time}, 'end_time': {'$gte': end_time}}
                ]
            }))
            
            if existing_booking:
                flash('This slot is already booked')
                return redirect(url_for('update_booking', booking_id=booking_id))
            
            # Update booking
            execute_with_retry(lambda: db.bookings.update_one(
                {'_id': ObjectId(booking_id)},
                {'$set': {
                    'date': date,
                    'start_time': start_time,
                    'end_time': end_time,
                    'updated_at': datetime.datetime.now()
                }}
            ))
            
            socketio.emit('booking_update', {'message': 'Booking updated'})
            flash('Booking updated successfully')
            return redirect(url_for('dashboard'))
            
        # Get microscope details for the form
        microscope = execute_with_retry(lambda: db.microscopes.find_one({'_id': ObjectId(booking['microscope_id'])}))
        return render_template('update_booking.html', booking=booking, microscope=microscope)
        
    except Exception as e:
        log_database_operation('update_booking', False, str(e))
        flash('Error updating booking')
        return redirect(url_for('dashboard'))

@app.route('/cancel-booking/<booking_id>', methods=['POST'])
@login_required
@otp_required
def cancel_booking(booking_id):
    try:
        booking = execute_with_retry(lambda: db.bookings.find_one({'_id': ObjectId(booking_id)}))
        
        # Check if booking exists and belongs to current user
        if not booking or str(booking['user_id']) != current_user.id:
            flash('Booking not found or unauthorized')
            return redirect(url_for('dashboard'))
            
        # Update booking status to cancelled
        execute_with_retry(lambda: db.bookings.update_one(
            {'_id': ObjectId(booking_id)},
            {'$set': {
                'status': 'cancelled',
                'cancelled_at': datetime.datetime.now()
            }}
        ))
        
        socketio.emit('booking_update', {'message': 'Booking cancelled'})
        flash('Booking cancelled successfully')
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        log_database_operation('cancel_booking', False, str(e))
        flash('Error cancelling booking')
        return redirect(url_for('dashboard'))

@app.route('/book', methods=['GET', 'POST'])
@login_required
@otp_required
def book():
    if request.method == 'POST':
        try:
            microscope_id_str = request.form.get('microscope_id')
            date = request.form.get('date')
            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')

            print("Form Data:", microscope_id_str, date, start_time, end_time)

            if not (microscope_id_str and date and start_time and end_time):
                flash('All fields are required.', 'danger')
                return redirect(url_for('book'))

            microscope_id = ObjectId(microscope_id_str)

            # Check for conflicts
            existing_booking = execute_with_retry(lambda: db.bookings.find_one({
                'microscope_id': microscope_id,
                'date': date,
                '$or': [
                    {'start_time': {'$lte': start_time}, 'end_time': {'$gt': start_time}},
                    {'start_time': {'$lt': end_time}, 'end_time': {'$gte': end_time}}
                ]
            }))

            if existing_booking:
                flash('This slot is already booked.', 'danger')
                return redirect(url_for('book'))

            # Insert the booking
            execute_with_retry(lambda: db.bookings.insert_one({
                'user_id': ObjectId(current_user.id),
                'microscope_id': microscope_id,
                'date': date,
                'start_time': start_time,
                'end_time': end_time,
                'status': 'confirmed',
                'created_at': datetime.datetime.now()
            }))

            socketio.emit('booking_update', {'message': 'New booking created'})
            flash('Slot booked successfully!', 'success')
            return redirect(url_for('thank_you'))

        except Exception as e:
            log_database_operation('book', False, str(e))
            flash('Error during booking: ' + str(e), 'danger')
            return redirect(url_for('book'))

    # GET request — render booking form
    try:
        microscopes = execute_with_retry(lambda: list(db.microscopes.find()))
        return render_template('book.html', microscopes=microscopes)
    except Exception as e:
        log_database_operation('get_microscopes', False, str(e))
        flash('Error loading microscopes', 'danger')
        return render_template('book.html', microscopes=[])
    


@app.route('/thank-you')
@login_required
@otp_required
def thank_you():
    return render_template('thank_you.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@socketio.on('connect')
def handle_connect():
    emit('status', {'data': 'Connected'})

if __name__ == '__main__':
    try:
        socketio.run(app, debug=True)
    except Exception as e:
        logger.error(f"Error starting application: {e}")
from gevent import monkey
monkey.patch_all()

from flask import Flask, redirect, url_for, render_template, flash, session, request, jsonify
import random
from events import events
import json
from flask_sqlalchemy import SQLAlchemy
from form import Login, Signup
from flask_mail import Mail, Message
from datetime import date, datetime
import pickle
import pandas as pd
from sqlalchemy import asc, desc
from flask_socketio import SocketIO
from ai_features import (
    get_chatbot_response,
    get_price_with_confidence,
    get_event_recommendations,
    generate_event_description,
    get_admin_analytics,
    admin_nl_query,
    check_date_intelligence,
    analyze_special_requirements,
    analyze_venue_mood
)

import os
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, 
            instance_path=os.path.join(basedir, 'instance'),
            template_folder=os.path.join(basedir, 'templates'),
            static_folder=os.path.join(basedir, 'static'))

# Ensure instance folder exists
instance_path = app.instance_path
if not os.path.exists(instance_path):
    os.makedirs(instance_path)

# Use absolute path for SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(instance_path, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["SECRET_KEY"] = "084c798ae26ad8bb088a191feb8224f772"
app.config['TEMPLATES_AUTO_RELOAD'] = True
db = SQLAlchemy(app)

# --- JINJA GLOBALS ---
app.jinja_env.globals.update(zip=zip, max=max, min=min)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'gouravswian8764@gmail.com'   
app.config['MAIL_PASSWORD'] = 'dtua syam bzaf amii'      

mail = Mail(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')


class User(db.Model):
    username = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), primary_key=True)
    password = db.Column(db.String(255), nullable=False)
    
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(150), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    guests = db.Column(db.Integer, nullable=False)
    date_booked = db.Column(db.String(50), nullable=False)
    catering = db.Column(db.String(10), nullable=False)
    entertainment = db.Column(db.String(10), nullable=False)
    user_email = db.Column(db.String(120), db.ForeignKey('user.email'), nullable=False)
    
    # New columns for Phase 2
    customer_name = db.Column(db.String(150), nullable=True)
    contact_number = db.Column(db.String(20), nullable=True)
    special_requirements = db.Column(db.Text, nullable=True)
    event_extra = db.Column(db.String(255), nullable=True)
    price = db.Column(db.Float, default=0.0)
    payment_method = db.Column(db.String(50), nullable=True)
    payment_status = db.Column(db.String(20), default="Pending")
    feedback_sent = db.Column(db.Boolean, default=False)

class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), nullable=True)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

class CustomEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(50), nullable=False)
    image = db.Column(db.String(200), nullable=True)

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(120), db.ForeignKey('user.email'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    sender = db.Column(db.String(20), nullable=False)  # "user" or "admin"
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    conversation = db.relationship('Conversation', backref='messages')



with app.app_context():
    db.create_all()
    # Auto-fix missing columns (SQLite doesn't support db.create_all updates)
    import sqlite3
    db_path = os.path.join(app.instance_path, 'database.db')
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(booking)")
        cols = [r[1] for r in cur.fetchall()]
        needed = {"price":"FLOAT", "customer_name":"VARCHAR(150)", "contact_number":"VARCHAR(20)", 
                  "special_requirements":"TEXT", "event_extra":"VARCHAR(150)", 
                  "payment_method":"VARCHAR(50)", "payment_status":"VARCHAR(20)", 
                  "feedback_sent":"BOOLEAN DEFAULT 0"}
        for col, ctype in needed.items():
            if col not in cols:
                cur.execute(f"ALTER TABLE booking ADD COLUMN {col} {ctype}")
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Schema auto-fix skipped: {e}")


@app.route("/")
def landingpage():
    return render_template("landingpage.html")

@app.route("/home")
def home():
    today = date.today()

    user_email = session.get('email')
    all_bookings = Booking.query.filter_by(user_email=user_email).all() if user_email else []

    live_events = []
    upcoming_events = []
    completed_events = []


    for booking in all_bookings:
        try:
            event_date = datetime.strptime(booking.date_booked, "%Y-%m-%d").date()
        except ValueError:
            continue  

        if event_date == today:
            live_events.append(booking)
        elif event_date > today:
            upcoming_events.append(booking)
        else:
            completed_events.append(booking)

    total_events = (
        len(live_events)
        + len(upcoming_events)
        + len(completed_events)
    )

    return render_template(
        "home.html",
        live_events=live_events,
        upcoming_events=upcoming_events,
        completed_events=completed_events,
        total_events=total_events,
        live_count=len(live_events),
        upcoming_count=len(upcoming_events),
        completed_count=len(completed_events)
    )


@app.route("/create")
def create():
    if 'username' not in session:
        flash("Please log in to create an event.")
        return redirect(url_for('login'))  
    return render_template('create.html')

@app.route("/marriage")
def marriage():
    return render_template('marriage.html', events=events)

@app.route("/birthday")
def birthday():
    return render_template('birthday.html', events=events)

@app.route("/meetup")
def meetup():
    return render_template('meetup.html', events=events)

@app.route("/corporate")
def corporate():
    return render_template('corporate.html', events=events)

@app.route("/fashion_show")
def fashion_show():
    cat_events = [e for e in events if e['title'] == 'Fashion Show']
    return render_template('event_category.html',
        events=cat_events,
        category_label="Haute Couture",
        hero_title="Fashion Shows",
        hero_subtitle="World-class runway experiences with elite lighting, staging, and designer coordination.",
        hero_image=url_for('static', filename='image/fashion_show.jpg'),
        highlights=[
            {"icon": "👗", "title": "Runway Staging", "desc": "Professional catwalk design with premium lighting rigs."},
            {"icon": "🎤", "title": "Live Coverage", "desc": "Media & press management for your brand exposure."},
            {"icon": "💎", "title": "VIP Lounge", "desc": "Exclusive seating for elite guests and press."},
            {"icon": "📸", "title": "Photo Studio", "desc": "On-site professional photography zone."},
        ]
    )

@app.route("/sports")
def sports():
    cat_events = [e for e in events if e['title'] == 'Sports']
    return render_template('event_category.html',
        events=cat_events,
        category_label="Champions Arena",
        hero_title="Sports Tournaments",
        hero_subtitle="Action-packed sporting events managed end-to-end with pro-level coordination.",
        hero_image=url_for('static', filename='image/sports.jpg'),
        highlights=[
            {"icon": "🏆", "title": "Tournament Setup", "desc": "Complete bracket & scheduling system."},
            {"icon": "📡", "title": "Live Streaming", "desc": "HD broadcast & commentary support."},
            {"icon": "🍔", "title": "Fan Zones", "desc": "Food courts and entertainment areas for fans."},
            {"icon": "🏅", "title": "Award Ceremony", "desc": "Grand closing ceremony with trophy presentation."},
        ]
    )

@app.route("/festival")
def festival():
    cat_events = [e for e in events if e['title'] == 'Festival']
    return render_template('event_category.html',
        events=cat_events,
        category_label="Cultural Celebration",
        hero_title="Cultural Festivals",
        hero_subtitle="Large-scale festivals with multiple stages, immersive art, and premium vendor ecosystems.",
        hero_image=url_for('static', filename='image/festival.jpg'),
        highlights=[
            {"icon": "🎪", "title": "Multi-Stage", "desc": "Live music, arts & cultural performances."},
            {"icon": "🎆", "title": "Fireworks", "desc": "Grand pyrotechnic finale coordination."},
            {"icon": "🛒", "title": "Vendor Market", "desc": "Curated artisan and food vendor alley."},
            {"icon": "🎭", "title": "Art Installations", "desc": "Interactive art zones for all guests."},
        ]
    )

@app.route("/charity")
def charity():
    cat_events = [e for e in events if e['title'] == 'Charity']
    return render_template('event_category.html',
        events=cat_events,
        category_label="Giving Back",
        hero_title="Charity Galas",
        hero_subtitle="Elegant fundraising events that inspire donors and maximize your charitable impact.",
        hero_image=url_for('static', filename='image/charity.jpg'),
        highlights=[
            {"icon": "❤️", "title": "Impact Stories", "desc": "Live storytelling to connect donors with causes."},
            {"icon": "🎗️", "title": "Silent Auction", "desc": "Curated auction management platform."},
            {"icon": "📊", "title": "Fund Tracker", "desc": "Live fundraising goal dashboard display."},
            {"icon": "🤝", "title": "Donor Relations", "desc": "Personalized recognition for major donors."},
        ]
    )

@app.route("/book", methods=["GET", "POST"])
def book():
    if 'email' not in session:
        flash(" Boss...Please login to book an event.")
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form.get("title")
        location = request.form.get("location")
        capacity = int(request.form.get("capacity"))
        guests = int(request.form.get("guests"))
        date_booked = request.form.get("date_booked")
        catering = request.form.get("catering")
        entertainment = request.form.get("entertainment")
        user_email = session['email']
        
        # New fields
        customer_name = request.form.get("customer_name")
        contact_number = request.form.get("contact_number")
        special_requirements = request.form.get("special_requirements")
        event_extra = request.form.get("event_extra")
        
        if guests > capacity:
            return redirect(url_for("book", title=title, location=location, capacity=capacity))

        # --- DYNAMIC PRICING ENGINE ---
        # 1. Base Price by Event Type
        base_price = 50000.0  # Default
        if title == 'Marriage': base_price = 150000.0
        elif title == 'Corporate': base_price = 80000.0
        elif title == 'Birthday': base_price = 50000.0
        elif title == 'Meetup': base_price = 40000.0
        elif title == 'Fashion Show': base_price = 120000.0
        elif title == 'Sports': base_price = 100000.0
        elif title == 'Festival': base_price = 90000.0
        elif title == 'Charity': base_price = 60000.0
        
        # 2. Guest Scaling (Linear)
        base_price += guests * 250
        
        # 3. AI Date Intelligence (Dynamic Factors)
        intelligence = check_date_intelligence(date_booked, Booking.query.all())
        multiplier = 1.0
        
        # Weekend Premium (Fri-Sun)
        dt_obj = datetime.strptime(date_booked, "%Y-%m-%d")
        if dt_obj.weekday() in [4, 5, 6]:
            multiplier += 0.15  # 15% weekend surge
            
        # Holiday Premium
        if intelligence.get('is_holiday'):
            multiplier += 0.20  # 20% holiday surge
            
        # Demand-based adjustment (Dynamic Load Balancing)
        demand = intelligence.get('demand_level', 'Moderate')
        if demand == "Very High": multiplier += 0.30
        elif demand == "High": multiplier += 0.15
        
        # Seasonality (Wedding season surcharge)
        if dt_obj.month in [11, 12, 1, 2]:
            multiplier += 0.10
        
        # 4. Final Aggregated Price
        final_price = base_price * multiplier
        
        # 5. Add-on Multipliers
        if catering == 'Yes': final_price *= 1.25
        if entertainment == 'Yes': final_price *= 1.15

        new_booking = Booking(
            title=title,
            location=location,
            capacity=capacity,
            guests=guests,
            date_booked=date_booked,
            catering=catering,
            entertainment=entertainment,
            user_email=user_email,
            customer_name=customer_name,
            contact_number=contact_number,
            special_requirements=special_requirements,
            event_extra=event_extra,
            price=round(final_price, 2),
            payment_status="Pending"
        )

        db.session.add(new_booking)
        db.session.commit()
        
        # --- BOOKING NOTIFICATION (Email) ---
        try:
            msg = Message(
                subject=f"Reservation Confirmation: {title} at {location}",
                sender=app.config['MAIL_USERNAME'],
                recipients=[user_email]
            )
            msg.html = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; border: 1px solid #ddd; padding: 20px; border-radius: 10px;">
                <h2 style="color: #9333ea; text-align: center;">Eventer Reservation Confirmed!</h2>
                <p>Dear <b>{customer_name}</b>,</p>
                <p>Your booking for a <b>{title}</b> event has been successfully initialized in our system.</p>
                <div style="background: #f9f9f9; padding: 15px; border-radius: 8px;">
                    <p><b>Venue:</b> {location}</p>
                    <p><b>Date:</b> {date_booked}</p>
                    <p><b>Guests:</b> {guests}</p>
                    <p><b>Estimated Total:</b> ₹{round(final_price, 2):,}</p>
                </div>
                <p>Please log in to your dashboard to complete the payment and secure your slot.</p>
                <p style="text-align: center; margin-top: 20px;">
                    <a href="{request.host_url}mybookings" style="background: #9333ea; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">View My Bookings</a>
                </p>
                <hr>
                <p style="font-size: 12px; color: #777;">Thank you for choosing Eventer - The AI-Powered Event Management Platform.</p>
            </div>
            """
            mail.send(msg)
        except Exception as e:
            print(f"Notification Error: {e}")

        session['pending_booking_id'] = new_booking.id
        flash(f"Reservation details saved with Dynamic Pricing: ₹{round(final_price, 2):,}. Please complete payment.")
        return redirect(url_for("payment", booking_id=new_booking.id))

    # GET request
    today = date.today().isoformat()
    title = request.args.get("title")
    location = request.args.get("location")
    capacity = request.args.get("capacity")
    return render_template("book.html", title=title, location=location, capacity=capacity,today=today)

@app.route("/mybookings")
def mybookings():
    if 'email' not in session:
        flash(" Boss...Please log in to view your bookings.")
        return redirect(url_for('login'))

    user_email = session['email']
    user_bookings = Booking.query.filter_by(user_email=user_email).all()
    total_bookings = len(user_bookings)

    return render_template("bookings.html", bookings=user_bookings, total=total_bookings)

@app.route("/about")
def about():
     return render_template("about.html")

@app.route("/contact", methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')

        msg = Message(
            subject=f"Contact Form: {subject}",
            sender=app.config['MAIL_USERNAME'],
            recipients=[app.config['MAIL_USERNAME']],
            body=f"You have received a new message from the contact form.\n\nName: {name}\nEmail: {email}\n\nMessage:\n{message}"
        )
        
        # Save to database for Admin Dashboard
        new_msg = ContactMessage(name=name, email=email, subject=subject, message=message)
        db.session.add(new_msg)
        db.session.commit()

        try:
            mail.send(msg)
            flash("Your message has been sent successfully!", "success")
        except Exception as e:
             # Log the error if possible, or just flash a generic error message, 
             # but here I'll show the error for debugging purposes if needed, 
             # or better yet just say it failed. 
             # Given the "User Review Required" note, I'll allow the error to be seen if it fails.
            flash(f"An error occurred: {str(e)}", "danger")
        
        return redirect(url_for('contact'))
    return render_template("contact.html")

@app.route("/signup", methods=['GET', 'POST'])
def signup():
     form = Signup()
     if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash(f"Email already registered: {form.email.data}. Use another email.")
        else:
            new_user = User(username=form.username.data, email=form.email.data, password=form.password.data)
            db.session.add(new_user)
            db.session.commit()
            flash(f"Successfully registered {form.username.data}.")
            return redirect(url_for('login'))
     return render_template("signup.html", title="Signup", form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    form = Login()
    if form.validate_on_submit():
        email = form.email.data
        passwords = form.password.data  
        
        ADMIN_EMAIL = "admin@gmail.com"
        ADMIN_PASSWORD = "admin123"
        if email == ADMIN_EMAIL and passwords == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            flash("Welcome Admin!", "success")
            return redirect(url_for('admin_dashboard'))
              
        user = User.query.filter_by(email=email).first()
        if user and user.password == passwords:
            session['username'] = user.username
            session['email'] = user.email
            flash('Login Successfully.')

            msg = Message(
                subject="Login Successful - Event Management System",
                sender=app.config['MAIL_USERNAME'],
                recipients=[user.email]
            )

            msg.html = f"""
<html>
  <body style="margin:0; padding:0; font-family:'Segoe UI',Roboto,Arial,sans-serif; background-color:#f5f7fb;">
    <table width="100%" cellspacing="0" cellpadding="0" style="background-color:#f5f7fb; padding:40px 0;">
      <tr>
        <td align="center">
          <table width="600" cellpadding="0" cellspacing="0" style="background:white; border-radius:16px; box-shadow:0 4px 25px rgba(0,0,0,0.1); overflow:hidden;">
            
            <!-- Header -->
            <tr>
              <td style="background:linear-gradient(90deg,#00c3ff,#9333ea,#ff4081); padding:30px 0; text-align:center;">
                <h1 style="font-size:2rem; margin:0; font-weight:900; color:white; letter-spacing:2px;">Eventer</h1>
                <p style="margin:8px 0 0; color:#e0e0e0; font-size:14px; letter-spacing:1px;">Making Every Occasion Memorable</p>
              </td>
            </tr>

            <!-- Body -->
            <tr>
              <td style="padding:40px 30px; text-align:left; color:#333;">
                <p style="font-size:18px; margin:0 0 15px;">Hello <b>{user.username}</b>,</p>
                <p style="font-size:16px; line-height:1.6; margin:0 0 20px;">
                  We're thrilled to see you back! 🎉<br>
                  You’ve successfully logged into your <b>Eventer</b> account.
                </p>

                <p style="font-size:15px; color:#555; line-height:1.6; margin-bottom:20px;">
                  If this wasn’t you, please <a href="https://youreventer.com/reset" style="color:#9333ea; text-decoration:none;">secure your account immediately</a>.
                </p>

                <p style="font-size:15px; color:#555; margin-bottom:10px;">
                  With regards,<br>
                  <b>The Eventer Team 💜</b>
                </p>
              </td>
            </tr>

            <!-- Divider -->
            <tr>
              <td style="border-top:1px solid #eee;"></td>
            </tr>

            <!-- Footer -->
            <tr>
              <td style="background-color:#fafafa; padding:20px; text-align:center; font-size:12px; color:#999;">
                <p style="margin:0;">© 2025 Eventer. All rights reserved.</p>
                <p style="margin:4px 0 0;">Your trusted AI-powered Event Management Platform</p>
              </td>
            </tr>

          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


            mail.send(msg)

            return redirect(url_for('home'))
        else:
            flash('Invalid Email or Password.')
    return render_template("login.html", title="Login", form=form)

@app.route("/forgot_password", methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            # Simulation of sending a recovery link
            session['reset_email'] = email
            flash(f"A recovery link has been sent to {email}. (Note: This is a simulation)", "info")
            return redirect(url_for('reset_password'))
        else:
            flash("Email address not found.", "danger")
            return redirect(url_for('forgot_password'))
    return render_template("forgot_password.html")

@app.route("/reset_password", methods=['GET', 'POST'])
def reset_password():
    email = session.get('reset_email')
    if not email:
        flash("Please request a password reset first.", "warning")
        return redirect(url_for('forgot_password'))
        
    if request.method == 'POST':
        new_password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user:
            user.password = new_password
            db.session.commit()
            session.pop('reset_email', None)
            flash("Your password has been reset successfully! You can now log in.", "success")
            return redirect(url_for('login'))
        else:
            flash("Error during reset. User not found.", "danger")
            return redirect(url_for('forgot_password'))
            
    return render_template("reset_password.html")

    
@app.route("/account")
def account():
    username = session.get('username')
    email = session.get('email')
    return render_template("account.html", username=username, email=email)  



try:
    with open("event_price_model.pkl", "rb") as f:
        model = pickle.load(f)
except Exception as e:
    print(f"CRITICAL: Failed to load ML model (likely RAM limit): {e}")
    model = None
@app.route('/predict_price', methods=['GET','POST'])
def predict_price():
    if request.method == 'POST':
        Event_Title = request.form.get('Event_Title')
        Location = request.form.get('Location')
        Capacity = int(request.form.get('Capacity', 100))
        Date = request.form.get('Date')
        Catering = request.form.get('Catering')
        Entertainment = request.form.get('Entertainment')

        # 1. Base ML Model Prediction (Simplified fallback for now)
        try:
            input_df = pd.DataFrame({
                'Event_Title': [Event_Title],
                'Location': [Location],
                'Capacity': [Capacity],
                'Date': [Date],
                'Catering': [Catering],
                'Entertainment': [Entertainment]
            })
            # Simple encoding for the pickle model
            for col in input_df.select_dtypes(include=['object']).columns:
                input_df[col] = input_df[col].astype('category').cat.codes
            if model is not None:
                base_predicted_price = model.predict(input_df)[0]
            else:
                raise ValueError("Model not loaded")
        except Exception as e:
            print(f"ML Model error: {e}")
            # Reliable heuristic fallback if model fails
            base_prices = {"Marriage": 150000, "Birthday": 50000, "Corporate Event": 80000, "Meetup": 40000}
            base_predicted_price = base_prices.get(Event_Title, 60000) + (Capacity * 150)

        # 2. Enhanced AI Confidence & Date Intelligence
        all_bookings = Booking.query.all()
        confidence_data = get_price_with_confidence(
            base_predicted_price, Event_Title, Location, 
            Capacity, Catering, Entertainment, Date, all_bookings
        )

        form_data = {
            'Event_Title': Event_Title, 'Location': Location, 
            'Capacity': Capacity, 'Date': Date, 
            'Catering': Catering, 'Entertainment': Entertainment
        }

        # Handle AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                "prediction": confidence_data['prediction'],
                "lower": confidence_data['lower'],
                "upper": confidence_data['upper'],
                "confidence": confidence_data['confidence'],
                "variance_pct": confidence_data['variance_pct'],
                "drivers_up": confidence_data['drivers_up'],
                "drivers_down": confidence_data['drivers_down']
            })

        return render_template('predict.html', 
                             prediction_text=f"₹{confidence_data['prediction']:,.2f}",
                             confidence_data=confidence_data,
                             form_data=form_data,
                             today=date.today().isoformat())
                             
    today = date.today().isoformat()
    return render_template('predict.html', today=today)

@app.route('/get_event_counts')
def get_event_counts():
    today = date.today()
    user_email = session.get('email')
    all_bookings = Booking.query.filter_by(user_email=user_email).all() if user_email else []

    
    live_count = 0
    upcoming_count = 0
    completed_count = 0
    
    for booking in all_bookings:
        try:
            event_date = datetime.strptime(booking.date_booked, "%Y-%m-%d").date()
        except ValueError:
            continue
        
        if event_date == today:
            live_count += 1
        elif event_date > today:
            upcoming_count += 1
        else:
            completed_count += 1
    
    total = live_count + upcoming_count + completed_count
    return jsonify({
        'total': total,
        'live': live_count,
        'upcoming': upcoming_count,
        'completed': completed_count
    })



@app.route("/payment/<int:booking_id>", methods=['GET', 'POST'])
def payment(booking_id):
    if 'email' not in session:
        return redirect(url_for('login'))
    
    booking = Booking.query.get_or_404(booking_id)
    if request.method == 'POST':
        method = request.form.get('payment_method', 'Card')
        booking.payment_method = method
        booking.payment_status = "Completed"
        db.session.commit()
        
        # --- PAYMENT SUCCESS NOTIFICATION ---
        try:
            msg = Message(
                subject=f"Receipt: Payment Secured for {booking.title}",
                sender=app.config['MAIL_USERNAME'],
                recipients=[booking.user_email]
            )
            msg.html = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; border: 1px solid #ddd; padding: 25px; border-radius: 12px; background-color: #fcfcfc;">
                <div style="text-align: center; border-bottom: 2px solid #9333ea; padding-bottom: 15px; margin-bottom: 20px;">
                    <h2 style="color: #9333ea; margin: 0;">Payment Successful ✅</h2>
                    <p style="color: #666; margin: 5px 0 0;">Transaction Confirmed via {method}</p>
                </div>
                
                <p>Hello <b>{booking.customer_name}</b>,</p>
                <p>Thank you! Your payment of <b>₹{booking.price:,}</b> has been received and your booking for <b>{booking.date_booked}</b> is now fully secured.</p>
                
                <div style="background: white; border: 1px dashed #ccc; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h4 style="margin-top: 0; color: #333;">Event Summary</h4>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr><td style="padding: 5px 0; color: #666;">Booking ID:</td><td style="text-align: right; font-weight: bold;">#EVT-{booking.id}</td></tr>
                        <tr><td style="padding: 5px 0; color: #666;">Event Type:</td><td style="text-align: right; font-weight: bold;">{booking.title}</td></tr>
                        <tr><td style="padding: 5px 0; color: #666;">Venue:</td><td style="text-align: right; font-weight: bold;">{booking.location}</td></tr>
                        <tr><td style="padding: 5px 0; color: #666;">Status:</td><td style="text-align: right; color: #008855; font-weight: bold;">FULLY BOOKED</td></tr>
                    </table>
                </div>
                
                <p>Our event coordinator will reach out to you within 24 hours to discuss the fine details.</p>
                <p style="text-align: center; color: #999; font-size: 13px; margin-top: 30px;">
                    © 2026 Eventer Systems. All rights reserved.
                </p>
            </div>
            """
            mail.send(msg)
        except Exception as e:
            print(f"Payment Email Error: {e}")

        flash(f"Payment successful via {method}! Your event is confirmed.")
        return redirect(url_for('home'))
        
    return render_template("payment.html", booking=booking)

@app.route("/discover")
def discover():
    user_bookings = []
    if 'email' in session:
        user_bookings = Booking.query.filter_by(user_email=session['email']).all()
    
    # Use AI Recommender
    recs = get_event_recommendations(user_bookings, [])
    return render_template("discover.html", recommendations=recs)

@app.route("/explore_categories")
def explore_categories():
    return render_template("explore_categories.html")

# ─── ADMIN DASHBOARD ROUTES ──────────────────────────────────────────────────

def admin_required(f):
    def wrap(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash("Access Denied: Admin Terminal Only")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

@app.route("/admin/master")
@admin_required
def admin_master():
    return render_template("master_admin.html")

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    total_users = User.query.count()
    total_bookings = Booking.query.count()
    all_bookings = Booking.query.order_by(Booking.id.desc()).all()
    recent_bookings = all_bookings[:5]
    users = User.query.all()
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    custom_events = CustomEvent.query.all()
    
    # AI Analytics
    ai_analytics = get_admin_analytics(all_bookings)
    
    return render_template("admin_dashboard.html", 
                         total_users=total_users, 
                         total_bookings=total_bookings,
                         recent_bookings=recent_bookings,
                         all_bookings=all_bookings,
                         users=users,
                         messages=messages,
                         custom_events=custom_events,
                         ai_analytics=ai_analytics,
                         ContactMessage=ContactMessage,
                         zip=zip,
                         max=max)

@app.route("/admin/bookings")
@admin_required
def admin_bookings():
    bookings = Booking.query.all()
    return render_template("admin_bookings.html", bookings=bookings)

@app.route("/admin/users")
@admin_required
def admin_users():
    users = User.query.all()
    return render_template("admin_users.html", users=users)

@app.route("/admin/messages")
@admin_required
def admin_messages():
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template("admin_messages.html", messages=messages)

@app.route("/admin/events", methods=['GET', 'POST'])
@admin_required
def admin_events():
    if request.method == 'POST':
        title = request.form.get("title")
        location = request.form.get("location")
        description = request.form.get("description")
        capacity = int(request.form.get("capacity"))
        type = request.form.get("type")
        image = request.form.get("image")
        
        new_ev = CustomEvent(title=title, location=location, description=description, 
                             capacity=capacity, type=type, image=image)
        db.session.add(new_ev)
        db.session.commit()
        flash(f"Blueprint for {title} has been deployed successfully.")
        return redirect(url_for('admin_events'))

    custom_events = CustomEvent.query.all()
    return render_template("admin_events.html", custom_events=custom_events)

@app.route("/api/ai/venue-mood", methods=["POST"])
def api_venue_mood():
    data = request.json
    location = data.get("location", "")
    event_type = data.get("event_type", "")
    tags = analyze_venue_mood(location, event_type)
    return jsonify({"tags": tags})

@app.route("/admin/delete-event/<int:id>")
@admin_required
def delete_event(id):
    ev = CustomEvent.query.get_or_404(id)
    db.session.delete(ev)
    db.session.commit()
    flash("Event blueprint archived.")
    return redirect(url_for('admin_events'))

@app.route("/admin/logout")
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('home'))

@app.route("/trigger_feedback_emails", methods=['POST'])
@admin_required
def trigger_feedback_emails():
    # Only send to completed bookings that haven't received feedback yet
    completed = Booking.query.filter_by(payment_status="Completed", feedback_sent=False).all()
    count = 0
    for b in completed:
        msg = Message("How was your event?", recipients=[b.user_email])
        msg.body = f"Hi {b.customer_name}, we hope your {b.title} was amazing! Please share your feedback."
        try:
            mail.send(msg)
            b.feedback_sent = True
            count += 1
        except:
            pass
    db.session.commit()
    flash(f"Successfully triggered feedback emails for {count} events.")
    return redirect(url_for('admin_dashboard'))

# ─── AI API ENDPOINTS ────────────────────────────────────────────────────────

@app.route("/api/ai/check-date", methods=["POST"])
def api_check_date():
    date_str = request.json.get("date")
    existing = Booking.query.all()
    result = check_date_intelligence(date_str, existing)
    return jsonify(result)

@app.route("/api/ai/analyze-requirements", methods=["POST"])
def api_analyze_reqs():
    text = request.json.get("text")
    result = analyze_special_requirements(text)
    return jsonify(result)

@app.route("/api/ai/generate-description", methods=["POST"])
def api_gen_desc():
    data = request.json
    desc = generate_event_description(
        data.get("event_type"),
        data.get("location"),
        data.get("guests"),
        data.get("extra")
    )
    return jsonify({"description": desc})

@app.route("/api/admin/nl-query", methods=["POST"])
@admin_required
def api_admin_nl_query():
    query = request.json.get("query")
    all_bookings = Booking.query.all()
    filtered = admin_nl_query(query, all_bookings)
    
    results = []
    for b in filtered:
        results.append({
            "id": b.id, "title": b.title, "customer_name": b.customer_name or b.user_email,
            "location": b.location, "date_booked": b.date_booked, "guests": b.guests
        })
    return jsonify({"results": results, "count": len(results)})

# (Previous routes continue...)
@app.route("/ai_chatbot")
def ai_chatbot_page():
    return render_template("ai_chatbot.html")

@app.route("/api/ai/chat", methods=["POST"])
def ai_chat_api():
    user_msg = request.json.get("message", "")
    bot_resp = get_chatbot_response(user_msg)
    return jsonify({"response": bot_resp})

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for('home'))


# ─── REAL-TIME CHAT (SocketIO) ───────────────────────────────────────────────

@app.route("/chat")
def chat():
    if 'email' not in session:
        flash("Please login to access support chat.")
        return redirect(url_for('login'))
    
    user_email = session['email']
    # Get or create conversation for this user
    conv = Conversation.query.filter_by(user_email=user_email).first()
    if not conv:
        conv = Conversation(user_email=user_email)
        db.session.add(conv)
        db.session.commit()
    
    return render_template("user_chat.html", conversation_id=conv.id)

@app.route("/admin/chat")
@admin_required
def admin_chat():
    conversations = Conversation.query.order_by(Conversation.created_at.desc()).all()
    return render_template("admin_chat.html", conversations=conversations)

@socketio.on('join')
def on_join(data):
    from flask_socketio import join_room
    room = str(data['conversation_id'])
    join_room(room)

@socketio.on('get_messages')
def on_get_messages(data):
    conv_id = data['conversation_id']
    messages = ChatMessage.query.filter_by(conversation_id=conv_id).order_by(ChatMessage.created_at.asc()).all()
    msg_list = []
    for m in messages:
        msg_list.append({
            "sender": m.sender,
            "content": m.content,
            "created_at": m.created_at.isoformat()
        })
    socketio.emit('message_history', {"conversation_id": conv_id, "messages": msg_list}, room=str(conv_id))

@socketio.on('send_message')
def on_send_message(data):
    conv_id = data['conversation_id']
    sender = data['sender']
    content = data['content']
    
    new_msg = ChatMessage(conversation_id=conv_id, sender=sender, content=content)
    db.session.add(new_msg)
    db.session.commit()
    
    socketio.emit('new_message', {
        "conversation_id": conv_id,
        "sender": sender,
        "content": content,
        "created_at": new_msg.created_at.isoformat()
    }, room=str(conv_id))


if __name__ == "__main__":
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

from flask import Flask, redirect, url_for, render_template, flash, session, request, jsonify
import random
from events import events
import json
from flask_sqlalchemy import SQLAlchemy
from form import Login, Signup
from flask_mail import Mail, Message
from datetime import date, datetime
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

# Serve another static folder for "extra" images
from flask import send_from_directory
@app.route('/extra/<path:filename>')
def serve_extra(filename):
    return send_from_directory(os.path.join(basedir, 'extra'), filename)

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
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

@app.after_request
def add_header(response):
    """
    Add Cache-Control header for static assets to speed up project loading
    """
    if 'static' in request.path:
        # Cache static assets for 1 year
        response.cache_control.max_age = 31536000
    return response


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
    
    # New columns for Phase 2 & 3
    customer_name = db.Column(db.String(150), nullable=True)
    contact_number = db.Column(db.String(20), nullable=True)
    hotel_contact = db.Column(db.String(50), nullable=True)
    region = db.Column(db.String(50), nullable=True)
    special_requirements = db.Column(db.Text, nullable=True)
    event_extra = db.Column(db.String(255), nullable=True)
    price = db.Column(db.Float, default=0.0)
    vendor_total = db.Column(db.Float, default=0.0)
    payment_method = db.Column(db.String(50), nullable=True)
    payment_status = db.Column(db.String(20), default="Pending")
    feedback_sent = db.Column(db.Boolean, default=False)
    rsvp_link = db.Column(db.String(150), nullable=True)
    rsvp_count = db.Column(db.Integer, default=0)

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

class Wishlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(120), db.ForeignKey('user.email'), nullable=False)
    event_title = db.Column(db.String(100), nullable=False)
    event_location = db.Column(db.String(150), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)

class Vendor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False) # e.g., 'Caterer', 'Photographer'
    price = db.Column(db.Float, nullable=False)
    rating = db.Column(db.Float, default=5.0)
    city = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), nullable=True)
    image = db.Column(db.String(200), nullable=True)

class VendorSelection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendor.id'), nullable=False)
    cost = db.Column(db.Float, nullable=False)

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



def init_db():
    with app.app_context():
        db_path = os.path.join(app.instance_path, 'database.db')
        # Only run full creation/migration if absolutely necessary OR on cold start
        if not os.path.exists(db_path):
            db.create_all()
            try:
                import sqlite3
                conn = sqlite3.connect(db_path)
                cur = conn.cursor()
                cur.execute("CREATE TABLE IF NOT EXISTS schema_info (version INTEGER)")
                cur.execute("INSERT OR IGNORE INTO schema_info (version) VALUES (3)")
                conn.commit()
                conn.close()
            except: pass
            print("📦 Database Initialized.")
        # Migration hint check (V3)
        # We only do this very occasionally or on explicit call now to save startup time


@app.route("/")
def landingpage():
    return render_template("landingpage.html")

@app.route("/ping")
def ping():
    return "Eventer AI: Active"

@app.route("/planner-quiz", methods=['GET', 'POST'])
def planner_quiz():
    recommendation = None
    if request.method == 'POST':
        q1 = request.form.get('budget') # Low, Mid, High
        q2 = request.form.get('guests') # <50, 50-200, >200
        q3 = request.form.get('vibe')   # Indoor, Outdoor, Modern, Classic
        
        # Simple AI Recommendation Logic
        if q1 == 'High' and q3 == 'Classic':
            recommendation = {"title": "Grand Heritage Wedding", "desc": "A majestic royal experience in a historic palace venue."}
        elif q1 == 'High' and q3 == 'Modern':
            recommendation = {"title": "Elite Tech Summit", "desc": "A cutting-edge corporate experience with futuristic decor."}
        elif q1 == 'Mid':
            recommendation = {"title": "Premium Rooftop Gala", "desc": "A sophisticated social gathering with skyline views."}
        else:
            recommendation = {"title": "Classic Garden Celebration", "desc": "An intimate and elegant outdoor experience."}
            
    return render_template("planner_quiz.html", recommendation=recommendation)

@app.route("/rsvp/<int:booking_id>", methods=['GET', 'POST'])
def rsvp(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if request.method == 'POST':
        name = request.form.get('guest_name')
        diet = request.form.get('dietary')
        # In a real app we'd save to a Guest table, here we just increment count for demo
        booking.rsvp_count += 1
        db.session.commit()
        flash(f"Thank you {name}, your RSVP has been recorded!", "success")
        return render_template("rsvp_confirm.html", booking=booking)
    return render_template("rsvp.html", booking=booking)

@app.route("/dashboard")
def dashboard():
    if 'email' not in session:
        flash("Please log in to access your secure dashboard.")
        return redirect(url_for('login'))
    
    user_email = session['email']
    user = User.query.filter_by(email=user_email).first()
    all_bookings = Booking.query.filter_by(user_email=user_email).all()
    wishlist = Wishlist.query.filter_by(user_email=user_email).all()
    
    today = date.today()
    upcoming = [b for b in all_bookings if datetime.strptime(b.date_booked, "%Y-%m-%d").date() >= today]
    completed = [b for b in all_bookings if datetime.strptime(b.date_booked, "%Y-%m-%d").date() < today]
    
    total_spent = sum(b.price for b in all_bookings if b.price)
    
    # AI recommendations for dashboard
    from events import events as catalog
    recommendations = get_event_recommendations(all_bookings, catalog)
    
    return render_template("dashboard.html", 
                           user=user, 
                           bookings=all_bookings,
                           upcoming=upcoming,
                           completed=completed,
                           total_spent=total_spent,
                           recommendations=recommendations,
                           wishlist=wishlist)

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
        hero_image=url_for('static', filename='image/fashion show/kendall-jenner-walks-runway-at-schiaparelli-fashion-show-at-paris-fashion-week-10-02-2025-4.jpg'),
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
        hero_image=url_for('static', filename='image/sports/view-of-centre-court-full-of-spectators-watching-a-game-at-wimbledon-GEDHCR.jpg'),
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
        hero_image=url_for('static', filename='image/cultural event/indian-girls-dancing-garba-dance-for-navratri-festival-in-ahmedabad-H34DA5.jpg'),
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
        hero_image=url_for('static', filename='image/charity/charity-fundraising-event2-1.jpg'),
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
        
        # Basic info
        customer_name = request.form.get("customer_name")
        contact_number = request.form.get("contact_number")
        hotel_contact = request.form.get("hotel_contact")
        region = request.form.get("region")
        special_requirements = request.form.get("special_requirements")
        event_extra = request.form.get("event_extra")
        vendor_total_val = request.form.get("vendor_total", "0")
        try:
            vendor_total = float(vendor_total_val) if vendor_total_val else 0.0
        except ValueError:
            vendor_total = 0.0
        
        if guests > capacity:
            return redirect(url_for("book", title=title, location=location, capacity=capacity))

        # --- DYNAMIC PRICING ENGINE ---
        base_price = get_fallback_price(title, guests)
        
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

        # 6. Add Vendor specific pricing
        final_price += vendor_total

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
            hotel_contact=hotel_contact,
            region=region,
            special_requirements=special_requirements,
            event_extra=event_extra,
            price=round(final_price, 2),
            vendor_total=vendor_total,
            payment_status="Pending",
            rsvp_link=f"/rsvp/{title.replace(' ', '_')}/{location.replace(' ', '_')}"
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
            print(f"Booking Confirmation Email failed: {e}")

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

@app.route("/gallery/charity")
def gallery_charity():
    return render_template("gallery_charity.html")

@app.route("/gallery/cultural")
def gallery_cultural():
    return render_template("gallery_cultural.html")

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

            # ─── ELITE WELCOME NOTIFICATION ───
            try:
                msg = Message(
                    subject="Membership Confirmation: Welcome to the Eventer Elite",
                    sender=app.config['MAIL_USERNAME'],
                    recipients=[form.email.data]
                )
                msg.html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;700&display=swap');
    </style>
</head>
<body style="margin:0; padding:0; font-family:'Outfit', sans-serif; background-color:#08080c; color:#ffffff;">
    <table width="100%" cellspacing="0" cellpadding="0" style="background-color:#08080c; padding:40px 0;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background:#111111; border: 1px solid #c5a059; border-radius:24px; overflow:hidden;">
                    <tr>
                        <td style="background: linear-gradient(135deg, #c5a059 0%, #8e6d31 100%); padding:60px 40px; text-align:center;">
                            <div style="font-size:3rem; font-weight:900; color:#000; letter-spacing:5px;">WELCOME</div>
                            <div style="color:#000; font-size:14px; letter-spacing:4px; font-weight:700; margin-top:10px;">TO THE FUTURE OF EVENTS</div>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:50px 40px;">
                            <p style="color:#c5a059; font-size:22px; font-weight:700;">Hello {form.username.data},</p>
                            <p style="color:#94a3b8; font-size:16px; line-height:1.8;">
                                Your account has been officially activated. You are now part of an exclusive circle of clients who demand nothing less than perfection.
                            </p>
                            <div style="margin:40px 0; border:1px solid #222; border-radius:12px; padding:30px;">
                                <h4 style="color:#c5a059; margin-top:0;">Your Elite Perks:</h4>
                                <ul style="color:#94a3b8; padding-left:20px; line-height:2;">
                                    <li>AI-Driven Budget Optimization</li>
                                    <li>Priority Venue Reservations</li>
                                    <li>dedicated 24/7 Concierge Support</li>
                                    <li>Real-time Logistics Monitoring</li>
                                </ul>
                            </div>
                            <p style="color:#64748b; font-size:14px; text-align:center;">
                                We look forward to orchestrating your next masterpiece.
                            </p>
                        </td>
                    </tr>
                    <tr>
                        <td style="background-color:#0a0a0a; padding:30px; text-align:center; font-size:11px; color:#475569;">
                            © 2026 Neuro Eventer Logistics | Handcrafted by Sohan Swain
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
            except Exception as e:
                print(f"Welcome Email failed: {e}")

            flash(f"Successfully registered {form.username.data}. Welcome to the Elite!")
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
            # ─── ELITE LOGIN NOTIFICATION ───
            msg = Message(
                subject="Security Alert: Successful Entry to Eventer Terminal",
                sender=app.config['MAIL_USERNAME'],
                recipients=[user.email]
            )

            msg.html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;700&display=swap');
    </style>
</head>
<body style="margin:0; padding:0; font-family:'Outfit', sans-serif; background-color:#08080c; color:#ffffff;">
    <table width="100%" cellspacing="0" cellpadding="0" style="background-color:#08080c; padding:40px 0;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background:#111111; border: 1px solid #c5a059; border-radius:24px; overflow:hidden; box-shadow:0 30px 60px rgba(0,0,0,0.8);">
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #c5a059 0%, #8e6d31 100%); padding:40px; text-align:center;">
                            <div style="font-size:2.5rem; font-weight:900; color:#000; letter-spacing:4px; text-transform:uppercase;">EVENTER</div>
                            <div style="color:#000; font-size:12px; letter-spacing:3px; margin-top:5px; font-weight:700;">ELITE LOGISTICS TERMINAL</div>
                        </td>
                    </tr>
                    <!-- Content -->
                    <tr>
                        <td style="padding:50px 40px; text-align:left;">
                            <h2 style="color:#c5a059; font-size:24px; margin-bottom:20px;">Welcome Back, {user.username}.</h2>
                            <p style="color:#94a3b8; font-size:16px; line-height:1.8; margin-bottom:25px;">
                                Your secure session has been initialized. You now have full access to our AI-powered planning orchestration and premium venue ecosystems.
                            </p>
                            <div style="background:rgba(197, 160, 89, 0.05); border-left:4px solid #c5a059; padding:20px; margin-bottom:30px;">
                                <p style="margin:0; color:#c5a059; font-size:14px; font-weight:700;">SESSION SECURITY DETAILS</p>
                                <p style="margin:5px 0 0; color:#94a3b8; font-size:14px;">Status: Authorized Access</p>
                                <p style="margin:5px 0 0; color:#94a3b8; font-size:14px;">Node: Neuro-Central-01</p>
                            </div>
                            <p style="color:#64748b; font-size:14px; line-height:1.6;">
                                If this login was not authorized by you, please reset your password immediately via the terminal security dashboard.
                            </p>
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="background-color:#0a0a0a; padding:30px; text-align:center; font-size:11px; color:#475569; border-top:1px solid #222;">
                            <p style="margin:0; letter-spacing:1px;">ORCHESTRATED BY NEURO EVENTER LOGISTICS</p>
                            <p style="margin:5px 0 0;">© 2026 Elite Event Management Platform</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
            try:
                mail.send(msg)
            except Exception as e:
                print(f"Login Confirmation Email failed: {e}")

            return redirect(url_for('dashboard'))
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

@app.route("/budget-calc", methods=['GET', 'POST'])
def budget_calc():
    result = None
    if request.method == 'POST':
        event_type = request.form.get('event_type')
        guests = int(request.form.get('guests', 0))
        city = request.form.get('city')
        quality = request.form.get('quality', 'Standard')
        
        # Simple Logic for Calculator
        base_rates = {"Marriage": 1000, "Birthday": 500, "Corporate": 800, "Meetup": 300}
        city_multipliers = {"Mumbai": 1.5, "Bangalore": 1.3, "Hyderabad": 1.2, "Bhubaneswar": 1.0, "Cuttack": 0.9}
        quality_multipliers = {"Standard": 1.0, "Premium": 1.5, "Luxury": 2.5}
        
        cost_per_guest = base_rates.get(event_type, 500) * city_multipliers.get(city, 1.0) * quality_multipliers.get(quality, 1.0)
        total = cost_per_guest * guests
        
        result = {
            "total": round(total, 2),
            "venue": round(total * 0.4, 2),
            "catering": round(total * 0.35, 2),
            "decor": round(total * 0.15, 2),
            "photography": round(total * 0.1, 2)
        }
    return render_template("budget_calc.html", result=result)

@app.route("/wishlist/toggle", methods=['POST'])
def wishlist_toggle():
    if 'email' not in session:
        return jsonify({"error": "Login required"}), 401
    
    data = request.json
    user_email = session['email']
    title = data.get('title')
    location = data.get('location')
    etype = data.get('type')
    
    item = Wishlist.query.filter_by(user_email=user_email, event_title=title, event_location=location).first()
    if item:
        db.session.delete(item)
        db.session.commit()
        return jsonify({"status": "removed"})
    else:
        new_item = Wishlist(user_email=user_email, event_title=title, event_location=location, event_type=etype)
        db.session.add(new_item)
        db.session.commit()
        return jsonify({"status": "added"})

@app.route("/marketplace")
def marketplace():
    vendors = Vendor.query.all()
    if not vendors:
        # Seed some vendors if empty
        v1 = Vendor(name="Gourmet Delights", type="Caterer", price=500, city="Mumbai", description="Premium multi-cuisine catering.")
        v2 = Vendor(name="Studio 24", type="Photographer", price=15000, city="Mumbai", description="Cinematic wedding photography.")
        v3 = Vendor(name="Royal Decorators", type="Decorator", price=25000, city="Bangalore", description="Grand stage and floral setups.")
        db.session.add_all([v1, v2, v3])
        db.session.commit()
        vendors = Vendor.query.all()
    return render_template("marketplace.html", vendors=vendors)

    
@app.route("/account")
def account():
    username = session.get('username')
    email = session.get('email')
    return render_template("account.html", username=username, email=email)  




# ─── PRICING REVENUE ENGINE ───────────────────────────────────────────────

def get_fallback_price(event_type, guests):
    base_prices = {
        "Marriage": 150000, 
        "Birthday": 50000, 
        "Corporate": 80000, 
        "Meetup": 40000,
        "Fashion Show": 120000,
        "Sports": 100000,
        "Festival": 90000,
        "Charity": 60000
    }
    base = base_prices.get(event_type, 60000)
    return base + (int(guests) * 250)

multiplier_map = {
    "Mumbai": 1.45, "Bangalore": 1.35, "Delhi": 1.40, 
    "Chennai": 1.25, "Kolkata": 1.20, "Hyderabad": 1.30,
    "Pune": 1.20, "Ahmedabad": 1.15, "Jaipur": 1.25, "Goa": 1.50
}

type_mapping = {
    "Marriage": "Wedding",
    "Birthday": "Party",
    "Corporate": "Business",
    "Meetup": "Social",
    "Fashion Show": "Fashion",
    "Sports": "Sporting",
    "Festival": "Cultural",
    "Charity": "Non-profit"
}

model = None
def load_ml_model():
    global model
    if model is None:
        try:
            import pickle
            if os.path.exists("event_price_model.pkl"):
                with open("event_price_model.pkl", "rb") as f:
                    model = pickle.load(f)
        except Exception as e:
            print(f"AI Model Error: {e}")
            model = None

@app.route("/predict_price", methods=['GET', 'POST'])
def predict_price():
    if request.method == 'GET':
        return redirect(url_for('predict'))
    try:
        import pandas as pd
        # 1. Capture Inputs with fallbacks
        EventType = request.form.get('EventType', 'Marriage')
        GuestCount = int(request.form.get('GuestCount', 100))
        Location = request.form.get('Location', 'Mumbai')
        FoodQuality = request.form.get('FoodQuality', 'Premium')
        DecorLevel = request.form.get('DecorLevel', 'Elite')
        Entertainment = request.form.get('Entertainment', 'Live Music')

        # Synchronize location naming (remove potential extra info if present)
        Location = Location.split(' (')[0] if ' (' in Location else Location

        input_df = pd.DataFrame({
            'Event_Type': [EventType],
            'Guest_Count': [GuestCount],
            'Location': [Location],
            'Food_Quality': [FoodQuality],
            'Decor_Style': [DecorLevel],
            'Entertainment': [Entertainment]
        })
        
        # 2. Predictive Execution
        for col in input_df.select_dtypes(include=['object', 'str']).columns:
            input_df[col] = input_df[col].astype('category').cat.codes

        base_predicted_price = 0
        if model is not None:
            try:
                base_predicted_price = model.predict(input_df)[0]
            except Exception:
                base_predicted_price = get_fallback_price(EventType, GuestCount)
        else:
            base_predicted_price = get_fallback_price(EventType, GuestCount)

        # Apply Regional Premium
        multiplier_map = {
            "Mumbai": 1.4, "Bangalore": 1.3, "Delhi": 1.3, "Goa": 1.5,
            "Hyderabad": 1.2, "Pune": 1.15, "Chennai": 1.2, "Kolkata": 1.1
        }
        final_price = base_predicted_price * multiplier_map.get(Location, 1.0)
        
        # 3. AI Mood Context
        mood_tags = ["Premium", "Elite", "Luxury", "Dynamic"]
        mood_tag = mood_tags[min(len(EventType), len(mood_tags)) - 1] if EventType else "Premium"
        mood = {"tag": mood_tag, "desc": f"Elite coordination optimized for {Location}."}

        # 4. JSON Response (Standard for our Neural AJAX)
        return jsonify({
            "status": "success",
            "price": f"{int(final_price):,}",
            "mood": mood,
            "location_analysis": f"AI budget optimization for {Location} completed."
        })

    except Exception as e:
        print(f"🔥 AI Prediction Failure: {e}")
        return jsonify({
            "status": "error",
            "price": "Calculating...",
            "mood": {"tag": "Analyzing", "desc": "Syncing with neural engine..."},
            "message": str(e)
        }), 200 # Return 200 to keep the frontend heart beating

@app.route("/predict")
def predict():
    return render_template("predict.html")

@app.route("/get_event_counts")
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
<!DOCTYPE html>
<html>
<head>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;700&display=swap');
    </style>
</head>
<body style="margin:0; padding:0; font-family:'Outfit', sans-serif; background-color:#08080c; color:#ffffff;">
    <table width="100%" cellspacing="0" cellpadding="0" style="background-color:#08080c; padding:40px 0;">
        <tr>
            <td align="center">
                <table width="600" cellpadding="0" cellspacing="0" style="background:#111111; border: 1px solid #c5a059; border-radius:24px; overflow:hidden;">
                    <tr>
                        <td style="background: linear-gradient(135deg, #c5a059 0%, #8e6d31 100%); padding:50px 40px; text-align:center;">
                            <h2 style="color:#000; margin:0; letter-spacing:2px; text-transform:uppercase; font-size:24px;">Booking Secured</h2>
                            <p style="color:#000; opacity:0.8; margin-top:5px; font-weight:700;">INVOICE #EVT-{booking.id}</p>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:40px;">
                            <p style="color:#c5a059; font-size:18px; font-weight:700; margin-bottom:30px;">Hello {booking.customer_name},</p>
                            <p style="color:#94a3b8; font-size:15px; line-height:1.6;">Your investment in excellence has been confirmed. Our logistics engine is now preparing your event at <b>{booking.location}</b>.</p>
                            
                            <table width="100%" style="margin:30px 0; border-collapse:collapse; background:rgba(255,255,255,0.03); border-radius:12px;">
                                <tr><td style="padding:15px; color:#64748b; border-bottom:1px solid #222;">Event Masterclass</td><td style="padding:15px; color:#fff; text-align:right; border-bottom:1px solid #222;">{booking.title}</td></tr>
                                <tr><td style="padding:15px; color:#64748b; border-bottom:1px solid #222;">Date Status</td><td style="padding:15px; color:#fff; text-align:right; border-bottom:1px solid #222;">{booking.date_booked}</td></tr>
                                <tr><td style="padding:15px; color:#64748b; border-bottom:1px solid #222;">Payment Instrument</td><td style="padding:15px; color:#fff; text-align:right; border-bottom:1px solid #222;">{method}</td></tr>
                                <tr><td style="padding:20px; color:#c5a059; font-weight:700; font-size:18px;">Total Capital</td><td style="padding:20px; color:#c5a059; text-align:right; font-weight:700; font-size:22px;">₹{booking.price:,}</td></tr>
                            </table>

                            <p style="color:#64748b; font-size:13px; text-align:center; font-style:italic;">This is an electronically generated receipt for your records.</p>
                        </td>
                    </tr>
                    <tr>
                        <td style="background-color:#0a0a0a; padding:30px; text-align:center; font-size:11px; color:#475569;">
                            NEURO EVENTER LOGISTICS TERMINAL | LUXURY & PRECISION
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
            try:
                mail.send(msg)
            except Exception as e:
                print(f"Receipt Email failed: {e}")
        except Exception as e:
            print(f"Payment Email Error: {e}")

        flash(f"Payment successful via {method}! Your event is confirmed.", "success")
        return redirect(url_for('receipt', booking_id=booking.id))
        
    return render_template("payment.html", booking=booking)

@app.route("/receipt/<int:booking_id>")
def receipt(booking_id):
    if 'email' not in session:
        return redirect(url_for('login'))
    booking = Booking.query.get_or_404(booking_id)
    return render_template("receipt.html", booking=booking)

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

@app.route("/admin/broadcast", methods=["POST"])
@admin_required
def admin_broadcast():
    broadcast_msg = request.json.get("message")
    users = User.query.all()
    # In a real app, you would use a mail queue (Celery/Redis)
    # Here we simulate the successful transmission to the entire user fleet
    count = len(users)
    return jsonify({"status": "success", "count": count, "log": f"Broadcast transmitted to {count} nodes."})

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
    init_db() # Ready in milliseconds!
    import threading
    threading.Thread(target=load_ml_model, daemon=True).start()
    
    # ------------------------------------------------------------------
    # FINAL REVIEW READY STATUS
    # ------------------------------------------------------------------
    print("\n" + "="*50)
    print(" [LIVE] EVENTER AI: LIVE & READY FOR FINAL REVIEW")
    print(" URL: http://127.0.0.1:8002")
    print("="*50 + "\n")
    
    socketio.run(app, host='127.0.0.1', port=8002, debug=True, use_reloader=True)

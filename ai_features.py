"""
ai_features.py — Eventer AI Module
All 8 AI features implemented using rule-based + ML logic (no external API key required).
Falls back gracefully if optional packages are missing.
"""

import re
import random
from datetime import datetime, date, timedelta
from collections import Counter

# ─── 1. AI CHATBOT ─────────────────────────────────────────────────────────────

CHATBOT_INTENTS = [
    {
        "patterns": ["hello", "hi", "hey", "good morning", "good evening", "greet"],
        "response": "👋 Welcome to **Eventer AI**! I'm your personal event planning assistant. How can I help you today?\n\nYou can ask me about:\n- 📅 Booking an event\n- 💰 Pricing & packages\n- 📍 Venues & locations\n- 🎉 Event types\n- 📞 Support"
    },
    {
        "patterns": ["book", "reserve", "booking", "make a reservation", "how to book", "want to book"],
        "response": "🎯 **How to Book Your Event:**\n\n1. Browse our event categories — *Marriage, Birthday, Corporate, Meetup*\n2. Select your preferred venue & click **Book Now**\n3. Fill in your details (guest count, date, preferences)\n4. Complete payment via **Card, UPI, or Cash**\n5. Receive instant email confirmation ✅\n\nWould you like me to take you to a specific category?"
    },
    {
        "patterns": ["price", "cost", "pricing", "how much", "budget", "estimate", "expensive", "cheap", "fee", "charge"],
        "response": "💰 **Eventer Pricing Overview:**\n\n| Event Type | Starting From |\n|---|---|\n| 💍 Marriage | ₹1,50,000 |\n| 🎂 Birthday | ₹50,000 |\n| 🤝 Corporate | ₹80,000 |\n| 🎤 Meetup | ₹40,000 |\n\n✨ Use our **AI Budget Predictor** for a precise estimate tailored to your event!\n\nPrices vary by location, guest count, catering, and entertainment options."
    },
    {
        "patterns": ["venue", "location", "place", "where", "city", "mumbai", "bangalore", "hyderabad", "bhubaneswar", "cuttack"],
        "response": "📍 **Our Premium Venues:**\n\n🌆 **Mumbai** — Waterfront Grand Ballroom, The Oberoi\n🌿 **Bangalore** — Taj West End, The Leela Palace\n🏖️ **Hyderabad** — Park Hyatt, Novotel HICC\n🏛️ **Bhubaneswar** — Mayfair Lagoon, Swosti Grand\n🌊 **Cuttack** — Hotel Akbari, The Cuttack Club\n\nAll venues are handpicked for luxury, accessibility & ambiance."
    },
    {
        "patterns": ["wedding", "marriage", "bride", "groom", "matrimony"],
        "response": "💍 **Wedding Services at Eventer:**\n\nWe specialize in **luxury weddings** that create lifelong memories:\n\n✨ Royal/Traditional/Destination themes\n🌸 Floral decoration & stage design\n🍽️ Premium catering (veg & non-veg)\n📸 Photography & videography\n🎶 Live music & entertainment\n🏨 Guest accommodation arrangements\n\nOur wedding packages start from **₹1,50,000**. [Book Now](/marriage)"
    },
    {
        "patterns": ["birthday", "bday", "party", "celebrate", "anniversary"],
        "response": "🎂 **Birthday Event Services:**\n\nMake your special day legendary!\n\n🎈 Themed decorations (Hollywood, Bollywood, Fairy tale...)\n🎂 Custom cakes & dessert tables\n🎮 Fun entertainment packages\n📸 Photo booth & memories\n🎁 Gift coordination\n\nPackages from **₹50,000**. [Plan Your Birthday](/birthday)"
    },
    {
        "patterns": ["corporate", "business", "conference", "seminar", "team", "office", "professional"],
        "response": "🤝 **Corporate Event Solutions:**\n\nPower your business events with excellence:\n\n📊 Conference & seminar setups\n🎤 Keynote speaker arrangements  \n☕ Business-class catering\n💻 AV & tech equipment\n🏆 Award ceremonies\n🤝 Networking event design\n\nPackages from **₹80,000**. [Explore Corporate](/corporate)"
    },
    {
        "patterns": ["meetup", "concert", "music", "festival", "gathering", "exhibition"],
        "response": "🎤 **Meetup & Festival Events:**\n\nCreate unforgettable experiences:\n\n🎵 Concert & music events\n🖼️ Art exhibitions & showcases  \n🎭 Cultural gatherings\n🏃 Sports & community events\n\nPackages from **₹40,000**. [Explore Meetups](/meetup)"
    },
    {
        "patterns": ["catering", "food", "menu", "vegetarian", "veg", "non-veg", "cuisine", "buffet", "chef"],
        "response": "🍽️ **Catering Excellence:**\n\nOur culinary team curates:\n\n✅ Multi-cuisine buffet spreads\n✅ Live cooking stations\n✅ Custom menus (veg, vegan, Jain, gluten-free)\n✅ Premium dessert tables\n✅ Mocktail & cocktail bars\n✅ Traditional & continental options\n\nCatering is available as **add-on** during booking."
    },
    {
        "patterns": ["entertainment", "music", "band", "dj", "dance", "performer", "show"],
        "response": "🎶 **Entertainment Packages:**\n\n🎸 Live bands & orchestras\n🎧 Professional DJ sets\n💃 Classical & Bollywood dance troupes\n🎤 Stand-up comedy shows\n🎪 Magic & circus acts\n🎆 Fireworks & light shows\n\nEntertainment can be added while booking your event!"
    },
    {
        "patterns": ["cancel", "cancellation", "refund", "reschedule", "change date"],
        "response": "📋 **Cancellation & Refund Policy:**\n\n⏰ **30+ days before**: 90% refund\n📅 **15-30 days before**: 60% refund  \n📅 **7-15 days before**: 30% refund\n⚠️ **< 7 days**: No refund\n\nFor **rescheduling**, contact us at least **10 days** before your event at no extra charge.\n\nNeed help? [Contact Support](/contact)"
    },
    {
        "patterns": ["payment", "pay", "upi", "card", "cash", "online payment", "transaction"],
        "response": "💳 **Payment Options:**\n\n📱 **UPI** — Google Pay, PhonePe, Paytm\n💳 **Credit/Debit Card** — Visa, Mastercard, RuPay\n💵 **Cash** — Pay at venue (50% advance required)\n🏦 **Net Banking** — All major banks\n\nAll payments are secured with **256-bit SSL encryption**."
    },
    {
        "patterns": ["support", "help", "assist", "contact", "problem", "issue", "question"],
        "response": "📞 **Get Human Support:**\n\n📧 Email: gouravswian8764@gmail.com\n💬 Live Chat: [Open Chat](/chat)\n📱 WhatsApp: +91 98765 43210\n\n⏰ **Support Hours:** Mon–Sat, 9 AM – 8 PM IST\n\nFor urgent issues, our team typically responds within **2 hours**."
    },
    {
        "patterns": ["my booking", "my reservation", "check booking", "booking status", "view booking"],
        "response": "📋 **Your Bookings:**\n\nView all your reservations at [My Bookings](/mybookings). You'll find:\n\n✅ Booking confirmation details\n📍 Venue information  \n📅 Event date & schedule\n👥 Guest count\n💳 Payment status\n\nFor modifications, contact our concierge team."
    },
    {
        "patterns": ["predict", "estimate price", "budget tool", "ai price", "price predictor", "how much will it cost"],
        "response": "🤖 **AI Budget Predictor:**\n\nOur machine learning model estimates event costs based on:\n\n📊 Event type & location\n👥 Guest count\n🍽️ Catering preferences  \n🎶 Entertainment add-ons\n📅 Date & seasonality\n\nTry it now: [Get Price Estimate](/predict_price) ✨"
    },
    {
        "patterns": ["thanks", "thank you", "awesome", "great", "perfect", "helpful", "good job"],
        "response": "😊 You're most welcome! I'm here anytime you need help.\n\nIs there anything else I can assist you with? Whether it's **booking, pricing, venues, or support** — I've got you covered! 🌟"
    },
    {
        "patterns": ["bye", "goodbye", "see you", "exit", "quit"],
        "response": "👋 **Goodbye!** Thank you for choosing **Eventer**.\n\nWe look forward to making your event extraordinary! ✨\n\nFeel free to chat anytime — I'm available 24/7!"
    },
]

DEFAULT_RESPONSE = "🤔 I'm not sure I understood that. Could you try rephrasing?\n\nHere are some topics I can help with:\n- 📅 **Booking** an event\n- 💰 **Pricing** & packages  \n- 📍 **Venues** & locations\n- 🎉 **Event types** (wedding, birthday, corporate)\n- 📞 **Support** & contact\n- 🤖 **AI Price Predictor**"

def get_chatbot_response(user_message: str) -> str:
    """Rule-based chatbot that matches patterns and returns responses."""
    message_lower = user_message.lower().strip()
    
    if not message_lower:
        return "Please type a message so I can help you! 😊"
    
    best_match = None
    best_score = 0
    
    for intent in CHATBOT_INTENTS:
        for pattern in intent["patterns"]:
            if pattern in message_lower:
                score = len(pattern)  # longer patterns = more specific match
                if score > best_score:
                    best_score = score
                    best_match = intent
    
    if best_match:
        return best_match["response"]
    
    # Fuzzy word matching
    words = set(message_lower.split())
    for intent in CHATBOT_INTENTS:
        for pattern in intent["patterns"]:
            pattern_words = set(pattern.split())
            if pattern_words & words:  # intersection
                return intent["response"]
    
    return DEFAULT_RESPONSE


# ─── 2. SMART PRICE PREDICTION WITH CONFIDENCE INTERVAL ───────────────────────

def get_price_with_confidence(base_prediction: float, event_type: str, location: str,
                               capacity: int, catering: str, entertainment: str, 
                               event_date_str: str = None, all_bookings: list = []) -> dict:
    """
    Adds confidence interval and price driver explanations to a base prediction.
    """
    # Initialize factors
    multiplier = 1.0
    drivers_up = []
    drivers_down = []
    
    # ─── DATE INTELLIGENCE ───
    if event_date_str:
        try:
            intelligence = check_date_intelligence(event_date_str, all_bookings)
            
            # Weekend Check
            dt_obj = datetime.strptime(event_date_str, "%Y-%m-%d")
            if dt_obj.weekday() in [4, 5, 6]: # Fri, Sat, Sun
                multiplier += 0.15
                drivers_up.append("📅 Weekend premium (+15%)")
            
            # Holiday Check
            if intelligence.get('is_holiday'):
                multiplier += 0.20
                drivers_up.append(f"🎉 Holiday: {intelligence.get('holiday_name')} (+20%)")
            
            # Demand Based Check
            demand = intelligence.get('demand_level', 'Moderate')
            if demand == "Very High":
                multiplier += 0.25
                drivers_up.append("📈 Very High Demand on this date (+25%)")
            elif demand == "High":
                multiplier += 0.12
                drivers_up.append("📊 High Demand on this date (+12%)")
                
            # Seasonality
            if dt_obj.month in [11, 12, 1, 2]:
                multiplier += 0.10
                drivers_up.append("❄️ Peak Season premium (+10%)")
                
        except Exception as e:
            print(f"Date intelligence error: {e}")

    # Apply multiplier to base prediction
    base_prediction *= multiplier

    # Determine confidence band (±10-20% based on inputs)
    variance_pct = 0.12  # base 12% variance
    
    # More variance for larger events
    if capacity > 500:
        variance_pct += 0.05
    if event_type in ["Marriage", "Corporate Event"]:
        variance_pct += 0.03
    
    lower = base_prediction * (1 - variance_pct)
    upper = base_prediction * (1 + variance_pct)
    
    # Static Price drivers
    if catering == "Yes":
        drivers_up.append("🍽️ Catering included (+25%)")
    else:
        drivers_down.append("⬇️ No catering (−15%)")
    
    if entertainment == "Yes":
        drivers_up.append("🎶 Entertainment package (+15%)")
    else:
        drivers_down.append("⬇️ No entertainment (−10%)")
    
    premium_locations = ["Mumbai", "Bangalore", "Hyderabad"]
    budget_locations = ["Bhubaneswar", "Cuttack"]
    if location in premium_locations:
        drivers_up.append(f"📍 {location} premium city factor")
    elif location in budget_locations:
        drivers_down.append(f"📍 {location} value city factor")
    
    if capacity > 300:
        drivers_up.append(f"👥 Large guest count ({capacity})")
    elif capacity < 100:
        drivers_down.append(f"👥 Intimate event economy")
    
    if event_type == "Marriage":
        drivers_up.append("💍 Wedding category premium")
    elif event_type == "Meetup":
        drivers_down.append("🎤 Meetup economy pricing")
    
    return {
        "prediction": base_prediction,
        "lower": lower,
        "upper": upper,
        "variance_pct": variance_pct * 100,
        "drivers_up": drivers_up,
        "drivers_down": drivers_down,
        "confidence": "High" if variance_pct < 0.15 else "Medium"
    }


# ─── 3. AI EVENT RECOMMENDER ──────────────────────────────────────────────────

def get_event_recommendations(user_bookings: list, all_events_catalog: list) -> list:
    """
    Returns personalized event recommendations based on booking history.
    `user_bookings`: list of Booking objects
    `all_events_catalog`: list of dicts with event info
    """
    image_map = {
        "Marriage": "wedding.png",
        "Birthday": "birthday.png",
        "Corporate": "corporate.png",
        "Meetup": "concert.png" # Assuming concert.png for meetups or similar
    }
    
    if not user_bookings:
        # Cold start: return popular events
        return [
            {"title": "Marriage", "type": "Marriage", "location": "Mumbai",
             "reason": "🌟 Most Popular", "url": "/marriage", "emoji": "💍", 
             "image": "wedding.png", "description": "Opulent wedding orchestration for elite families."},
            {"title": "Corporate", "type": "Corporate", "location": "Bangalore",
             "reason": "🏆 Top Rated", "url": "/corporate", "emoji": "🤝",
             "image": "corporate.png", "description": "High-impact corporate summits and galla."},
            {"title": "Birthday", "type": "Birthday", "location": "Hyderabad",
             "reason": "🎉 Trending", "url": "/birthday", "emoji": "🎂",
             "image": "birthday.png", "description": "Immersive birthday experiences designed by AI."},
        ]
    
    # Analyze past bookings
    booked_types = [b.title for b in user_bookings]
    booked_locations = [b.location for b in user_bookings]
    
    type_counts = Counter(booked_types)
    location_counts = Counter(booked_locations)
    
    top_type = type_counts.most_common(1)[0][0] if type_counts else "Marriage"
    top_location = location_counts.most_common(1)[0][0] if location_counts else "Mumbai"
    
    recommendations = []
    
    # Same-type recommendation
    type_map = {
        "Marriage": {"url": "/marriage", "emoji": "💍", "desc": "Exclusive venues for your next union."},
        "Birthday": {"url": "/birthday", "emoji": "🎂", "desc": "Memorable celebrations for your loved ones."},
        "Corporate": {"url": "/corporate", "emoji": "🤝", "desc": "Professional galla orchestrations."},
        "Meetup": {"url": "/meetup", "emoji": "🎤", "desc": "Intimate meetups for tech and networking."},
    }
    
    rec1_info = type_map.get(top_type, {"url": "/marriage", "emoji": "✨", "desc": "Curated experience."})
    recommendations.append({
        "title": top_type,
        "type": top_type,
        "location": top_location,
        "reason": f"📋 Based on your {top_type} history",
        "url": rec1_info["url"],
        "emoji": rec1_info["emoji"],
        "image": image_map.get(top_type, "landing_hero.png"),
        "description": rec1_info["desc"]
    })
    
    # Cross-type recommendation
    all_types = ["Marriage", "Birthday", "Corporate", "Meetup"]
    new_types = [t for t in all_types if t not in booked_types]
    if new_types:
        new_type = random.choice(new_types)
        rec2_info = type_map.get(new_type, {"url": "/home", "emoji": "🌟", "desc": "Discover something new."})
        recommendations.append({
            "title": new_type,
            "type": new_type,
            "location": "Local Venues",
            "reason": "🔭 Expand your experience",
            "url": rec2_info["url"],
            "emoji": rec2_info["emoji"],
            "image": image_map.get(new_type, "landing_hero.png"),
            "description": rec2_info["desc"]
        })
    
    # Seasonal recommendation
    current_month = datetime.now().month
    if current_month in [11, 12, 1, 2]:  # Wedding season
        recommendations.append({
            "title": "Marriage",
            "type": "Marriage",
            "location": "Mumbai",
            "reason": "❄️ Peak wedding season discount",
            "url": "/marriage",
            "emoji": "💍",
            "image": "wedding_bg_rings.png",
            "description": "Premium winter orchestration slots are now open."
        })
    elif current_month in [6, 7, 8]:  # Corporate Q2
        recommendations.append({
            "title": "Corporate",
            "type": "Corporate",
            "location": "Bangalore",
            "reason": "📊 Q2 Corporate season",
            "url": "/corporate",
            "emoji": "🤝",
            "image": "corporate.png",
            "description": "Strategic networking summits for the fiscal year."
        })
    else:
        recommendations.append({
            "title": "Birthday",
            "type": "Birthday",
            "location": top_location,
            "reason": "🎉 Perfect for this season",
            "url": "/birthday",
            "emoji": "🎂",
            "image": "birthday.png",
            "description": "Celebrate milestones with AI-driven aesthetics."
        })
    
    return recommendations[:3]


# ─── 4. AI EVENT DESCRIPTION GENERATOR ───────────────────────────────────────

DESCRIPTION_TEMPLATES = {
    "Marriage": [
        "Step into a world of timeless elegance at {location}, where {guests} cherished guests will witness two souls unite in an unforgettable ceremony. This bespoke {extra} wedding is designed to reflect your unique love story — from breathtaking floral arrangements to gourmet cuisine — every detail speaks of luxury and romance.",
        "Your dream wedding comes alive at the prestigious {location}, a venue that has witnessed countless love stories. With {guests} guests in attendance and a {extra} theme, this celebration blends tradition with modern grandeur, crafting memories that will be treasured across generations.",
        "An extraordinary love deserves an extraordinary celebration. At {location}, surrounded by {guests} of your nearest and dearest, your {extra} wedding promises to be the most magical day of your lives — a perfect blend of sophistication, joy, and everlasting moments.",
    ],
    "Birthday": [
        "Celebrate another year of brilliance at {location} with an exclusive {extra}-themed party for {guests} vibrant guests. From personalized décor to a spectacular entertainment lineup, this birthday experience is curated to make you feel truly extraordinary on your special day.",
        "Life is too short for ordinary birthdays! At {location}, your {extra} celebration will dazzle {guests} guests with world-class entertainment, premium catering, and jaw-dropping décor that transforms the evening into a legendary memory.",
        "Mark this milestone in style at the stunning {location}. Your {extra} birthday party for {guests} guests will be a masterpiece of fun, flair, and unforgettable moments — a night that will be talked about for years to come.",
    ],
    "Corporate": [
        "Elevate your brand at {location} with a premier corporate event designed to inspire, connect, and impress. Hosting {guests} industry leaders for a {extra} event, this meticulously planned occasion features state-of-the-art AV, executive catering, and a program that drives meaningful business outcomes.",
        "Transform your corporate vision into reality at {location}. This elite {extra} event for {guests} professionals combines cutting-edge presentations, premium networking spaces, and flawless event management that positions your brand as an industry leader.",
        "Your next big business milestone deserves the perfect stage. At {location}, our team orchestrates a flawless {extra} corporate event for {guests} attendees — balancing professionalism with impactful experiences that strengthen partnerships and fuel growth.",
    ],
    "Meetup": [
        "Bring your community together at the vibrant {location} for an inspiring {extra} gathering. With {guests} enthusiastic attendees, this meetup is designed to spark meaningful conversations, foster connections, and create a shared experience that resonates long after the event ends.",
        "Experience the power of community at {location}. Your {extra} meetup for {guests} passionate participants will feature engaging sessions, collaborative spaces, and an electric atmosphere that turns strangers into collaborators and ideas into action.",
        "Create impact at scale with your {extra} event at {location}. Curated for {guests} like-minded individuals, this gathering blends knowledge-sharing with memorable experiences, leaving every attendee inspired, connected, and energized.",
    ]
}

def generate_event_description(event_type: str, location: str, guests: int, extra: str = "") -> str:
    """Generate a professional AI event description."""
    templates = DESCRIPTION_TEMPLATES.get(event_type, DESCRIPTION_TEMPLATES["Marriage"])
    template = random.choice(templates)
    
    extra_clean = extra if extra else f"premium {event_type.lower()}"
    
    return template.format(
        location=location or "our premium venue",
        guests=f"{guests:,}" if guests else "your",
        extra=extra_clean
    )


# ─── 5. ADMIN ANALYTICS ───────────────────────────────────────────────────────

def get_admin_analytics(all_bookings: list) -> dict:
    """
    Compute analytics: trend, forecast, top metrics, anomalies.
    `all_bookings`: list of Booking ORM objects
    """
    if not all_bookings:
        return {
            "total": 0, "monthly_bookings": {}, "top_location": "N/A",
            "top_event": "N/A", "forecast_next_month": 0,
            "avg_guests": 0, "anomalies": [], "monthly_labels": [],
            "monthly_values": [], "catering_pct": 0, "entertainment_pct": 0,
            "type_distribution": {}
        }
    
    total = len(all_bookings)
    monthly_bookings = {}
    location_counts = Counter()
    event_counts = Counter()
    guests_list = []
    catering_yes = 0
    entertainment_yes = 0
    
    for b in all_bookings:
        try:
            d = datetime.strptime(b.date_booked, "%Y-%m-%d")
            key = d.strftime("%b %Y")
            monthly_bookings[key] = monthly_bookings.get(key, 0) + 1
        except:
            pass
        
        location_counts[b.location] += 1
        event_counts[b.title] += 1
        guests_list.append(b.guests or 0)
        
        if b.catering == "Yes":
            catering_yes += 1
        if b.entertainment == "Yes":
            entertainment_yes += 1
    
    # Forecast: simple moving average of last 3 months
    sorted_months = sorted(monthly_bookings.items(),
                           key=lambda x: datetime.strptime(x[0], "%b %Y"))
    recent_counts = [v for _, v in sorted_months[-3:]]
    forecast = int(sum(recent_counts) / len(recent_counts)) if recent_counts else 0
    
    # Anomaly detection: months with >2x average are anomalies
    if monthly_bookings:
        avg = sum(monthly_bookings.values()) / len(monthly_bookings)
        anomalies = [f"📈 {m}: {c} bookings (surge detected!)"
                     for m, c in monthly_bookings.items() if c > avg * 1.8]
    else:
        anomalies = []
    
    # Chart data (last 6 months)
    labels = [k for k, _ in sorted_months[-6:]]
    values = [v for _, v in sorted_months[-6:]]
    
    return {
        "total": total,
        "monthly_bookings": dict(sorted_months),
        "top_location": location_counts.most_common(1)[0][0] if location_counts else "N/A",
        "top_event": event_counts.most_common(1)[0][0] if event_counts else "N/A",
        "forecast_next_month": forecast,
        "avg_guests": int(sum(guests_list) / len(guests_list)) if guests_list else 0,
        "anomalies": anomalies,
        "monthly_labels": labels,
        "monthly_values": values,
        "catering_pct": int((catering_yes / total) * 100) if total else 0,
        "entertainment_pct": int((entertainment_yes / total) * 100) if total else 0,
        "type_distribution": dict(event_counts.most_common()),
    }


def admin_nl_query(query: str, all_bookings: list) -> list:
    """
    Natural language query on bookings.
    e.g. "show bookings above 100000" or "show bookings in march"
    """
    query_lower = query.lower()
    results = list(all_bookings)
    
    # Filter by event type
    for etype in ["marriage", "birthday", "corporate", "meetup"]:
        if etype in query_lower:
            results = [b for b in results if b.title.lower() == etype]
            break
    
    # Filter by month
    months = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12
    }
    for month_name, month_num in months.items():
        if month_name in query_lower:
            filtered = []
            for b in results:
                try:
                    d = datetime.strptime(b.date_booked, "%Y-%m-%d")
                    if d.month == month_num:
                        filtered.append(b)
                except:
                    pass
            results = filtered
            break
    
    # Filter by location
    for city in ["mumbai", "bangalore", "hyderabad", "bhubaneswar", "cuttack"]:
        if city in query_lower:
            results = [b for b in results if city in b.location.lower()]
            break
    
    return results


# ─── 7. SMART DATE CONFLICT DETECTOR ─────────────────────────────────────────

INDIAN_HOLIDAYS_2026 = {
    "2026-01-01": "New Year's Day",
    "2026-01-14": "Makar Sankranti",
    "2026-01-26": "Republic Day",
    "2026-03-17": "Holi",
    "2026-04-02": "Good Friday",
    "2026-04-14": "Dr. Ambedkar Jayanti",
    "2026-04-21": "Ram Navami",
    "2026-05-01": "Labour Day / May Day",
    "2026-08-15": "Independence Day",
    "2026-08-19": "Janmashtami",
    "2026-10-02": "Gandhi Jayanti",
    "2026-10-24": "Dussehra",
    "2026-11-14": "Diwali",
    "2026-12-25": "Christmas Day",
    "2025-12-25": "Christmas Day",
    "2025-11-01": "Diwali",
    "2025-10-02": "Gandhi Jayanti",
    "2025-08-15": "Independence Day",
    "2025-01-26": "Republic Day",
}

def check_date_intelligence(booking_date_str: str, existing_bookings: list) -> dict:
    """
    Smart date analysis: holiday check, demand analysis, recommendations.
    """
    warnings = []
    tips = []
    demand_level = "Low"
    demand_color = "#4ade80"  # green
    
    try:
        booking_date = datetime.strptime(booking_date_str, "%Y-%m-%d").date()
    except:
        return {"warnings": [], "tips": [], "demand_level": "Unknown", "demand_color": "#888"}
    
    # 1. Holiday check
    holiday = INDIAN_HOLIDAYS_2026.get(booking_date_str)
    if holiday:
        warnings.append(f"🎉 {holiday} falls on this date — vendors may charge premium rates!")
        tips.append("Consider booking at least 3 weeks in advance to secure vendors.")
    
    # 2. Weekend check
    if booking_date.weekday() in [5, 6]:  # Sat, Sun
        warnings.append("📅 Weekend booking — venues are 30-40% more in demand!")
        tips.append("Book early or consider a weekday for better pricing.")
    
    # 3. Peak season (wedding season Nov–Feb)
    if booking_date.month in [11, 12, 1, 2]:
        warnings.append("❄️ Peak wedding season! Very high demand on this date.")
        tips.append("We strongly recommend booking 4-6 weeks ahead for best availability.")
        demand_level = "Very High"
        demand_color = "#ff4081"
    elif booking_date.month in [3, 4, 10]:
        demand_level = "High"
        demand_color = "#f59e0b"
    else:
        demand_level = "Moderate"
        demand_color = "#00eefb"
    
    # 4. How many other bookings on the same date
    same_day_count = sum(
        1 for b in existing_bookings
        if b.date_booked == booking_date_str
    )
    
    if same_day_count >= 3:
        warnings.append(f"⚠️ {same_day_count} other events already booked on this date!")
        tips.append("This date has very high demand. Book immediately to secure your slot.")
        demand_level = "Very High"
        demand_color = "#ff4081"
    elif same_day_count >= 1:
        warnings.append(f"📊 {same_day_count} other event(s) scheduled on this date.")
        demand_level = "High"
        demand_color = "#f59e0b"
    
    # 5. Too close to today
    today = date.today()
    days_away = (booking_date - today).days
    if 0 < days_away < 7:
        warnings.append("⏰ Very short notice (< 7 days)! Some vendors may not be available.")
        tips.append("Confirm vendor availability before completing your booking.")
    elif 7 <= days_away < 14:
        tips.append("⏳ Booking with less than 2 weeks notice — confirm details quickly.")
    
    if not warnings:
        tips.append("✅ This looks like a great date! Good availability expected.")
    
    return {
        "warnings": warnings,
        "tips": tips,
        "demand_level": demand_level,
        "demand_color": demand_color,
        "same_day_count": same_day_count,
        "is_holiday": bool(holiday),
        "holiday_name": holiday or "",
        "days_away": days_away if days_away >= 0 else 0
    }


# ─── 8. SENTIMENT ANALYSIS ON SPECIAL REQUIREMENTS ───────────────────────────

PREMIUM_KEYWORDS = [
    "luxury", "premium", "royal", "vip", "exclusive", "elite", "designer",
    "international", "imported", "celebrity", "gourmet", "michelin", "fine dining",
    "helicopter", "yacht", "orchestra", "live band", "fireworks", "pyrotechnics"
]

COMPLEXITY_KEYWORDS = [
    "multiple", "several", "many", "complex", "elaborate", "custom", "special",
    "unique", "specific", "particular", "various", "different", "diverse",
    "international guests", "dietary restrictions", "allergies", "wheelchair",
    "accessibility", "overnight", "multi-day", "two days", "3 days"
]

AUTO_TAGS = {
    "outdoor": ["outdoor", "garden", "terrace", "poolside", "beach", "lawn", "open air", "outside"],
    "vegetarian": ["veg", "vegetarian", "vegan", "jain", "plant-based", "no meat", "pure veg"],
    "live music": ["live music", "band", "orchestra", "musician", "singer", "dj", "music"],
    "photography": ["photo", "photography", "photographer", "videography", "video", "shoot"],
    "floral": ["floral", "flowers", "roses", "decoration", "decor", "centerpiece"],
    "kids friendly": ["kids", "children", "child", "baby", "toddler", "playground"],
    "dietary needs": ["gluten", "allergy", "diabetic", "halal", "kosher", "nut-free"],
    "themed": ["theme", "themed", "costume", "bollywood", "hollywood", "fairy", "vintage", "retro"],
    "transport": ["transport", "bus", "shuttle", "parking", "valet", "travel"],
    "accommodation": ["hotel", "accommodation", "stay", "overnight", "room", "lodge"],
}

def analyze_special_requirements(text: str) -> dict:
    """
    NLP analysis on special requirements text.
    Returns tags, sentiment, complexity level, alerts.
    """
    if not text or len(text.strip()) < 3:
        return {
            "tags": [],
            "sentiment": "neutral",
            "complexity": "Standard",
            "complexity_color": "#00eefb",
            "is_premium": False,
            "alerts": [],
            "word_count": 0
        }
    
    text_lower = text.lower()
    words = text_lower.split()
    
    # Auto-tagging
    detected_tags = []
    for tag, keywords in AUTO_TAGS.items():
        if any(kw in text_lower for kw in keywords):
            detected_tags.append(tag)
    
    # Premium detection
    premium_matches = [kw for kw in PREMIUM_KEYWORDS if kw in text_lower]
    is_premium = len(premium_matches) > 0
    
    # Complexity detection
    complexity_matches = [kw for kw in COMPLEXITY_KEYWORDS if kw in text_lower]
    word_count = len(words)
    
    if len(complexity_matches) >= 3 or word_count > 50 or is_premium:
        complexity = "Premium"
        complexity_color = "#9333ea"
    elif len(complexity_matches) >= 1 or word_count > 20:
        complexity = "Moderate"
        complexity_color = "#f59e0b"
    else:
        complexity = "Standard"
        complexity_color = "#4ade80"
    
    # Positive/negative sentiment (simple)
    positive_words = ["love", "would love", "eager", "excited", "happy", "please", "thank"]
    negative_words = ["no", "none", "avoid", "don't", "not", "never", "without"]
    
    pos_score = sum(1 for w in positive_words if w in text_lower)
    neg_score = sum(1 for w in negative_words if w in text_lower)
    
    if pos_score > neg_score:
        sentiment = "positive"
    elif neg_score > pos_score + 1:
        sentiment = "cautious"
    else:
        sentiment = "neutral"
    
    # Alerts for admin
    alerts = []
    if is_premium:
        alerts.append(f"💎 Premium requirements detected: {', '.join(premium_matches[:3])}")
    if "allergy" in text_lower or "allergic" in text_lower:
        alerts.append("⚠️ Dietary allergies mentioned — coordinate with catering team!")
    if "wheelchair" in text_lower or "accessibility" in text_lower or "disabled" in text_lower:
        alerts.append("♿ Accessibility requirements — ensure venue compliance!")
    if "overnight" in text_lower or "multi-day" in text_lower:
        alerts.append("🏨 Multi-day/overnight event — arrange accommodation coordination!")
    if word_count > 60:
        alerts.append("📝 Detailed requirements — assign dedicated event coordinator!")
    
    return {
        "tags": detected_tags,
        "sentiment": sentiment,
        "complexity": complexity,
        "complexity_color": complexity_color,
        "is_premium": is_premium,
        "alerts": alerts,
        "word_count": word_count,
        "premium_keywords": premium_matches[:3]
    }


# ─── VENUE MOOD ANALYZER (Feature 6) ─────────────────────────────────────────

VENUE_MOOD_MAP = {
    # location keyword → mood tags
    "mumbai": ["🌊 Coastal", "✨ Glamorous", "🌃 Urban Luxury", "🎭 Premium"],
    "bangalore": ["🌿 Green Luxury", "💻 Modern", "☕ Sophisticated", "🌸 Elegant"],
    "hyderabad": ["🏛️ Heritage", "✨ Regal", "🌟 Grand", "🎆 Festive"],
    "goa": ["🏖️ Beachside", "🌅 Romantic", "🌴 Tropical", "🎉 Vibrant"],
    "bhubaneswar": ["🏛️ Cultural", "🌺 Traditional", "🌿 Serene", "✨ Elegant"],
    "cuttack": ["🌊 Riverside", "🏛️ Heritage", "🌸 Traditional", "✨ Charming"],
    "delhi": ["👑 Majestic", "🏛️ Historical", "✨ Grand", "🌟 Imperial"],
    "jaipur": ["🏰 Royal", "✨ Luxury", "🌸 Romantic", "🎨 Artistic"],
    "kerala": ["🌴 Tropical", "🌊 Backwater", "🌿 Serene", "🧘 Peaceful"],
}

VENUE_TYPE_MOODS = {
    "palace": ["👑 Royal", "🏰 Historic", "✨ Majestic", "🌟 Opulent"],
    "beach": ["🏖️ Scenic", "🌅 Romantic", "🌊 Refreshing", "🌴 Tropical"],
    "garden": ["🌸 Floral", "🌿 Natural", "☀️ Outdoor", "🦋 Serene"],
    "hotel": ["🏨 Premium", "✨ Sophisticated", "🍽️ Gourmet", "💼 Professional"],
    "resort": ["🌴 Luxury Resort", "🏊 Leisure", "✨ Indulgent", "🌅 Scenic"],
    "hall": ["🎆 Grand", "💡 Elegant", "🎵 Festive", "✨ Classic"],
    "terrace": ["🌃 Skyline View", "🌙 Evening Ideal", "✨ Romantic", "🌟 Exclusive"],
    "ballroom": ["💃 Glamorous", "✨ Elite", "🎶 Grand", "👗 Formal"],
    "rooftop": ["🌃 Skyline", "🌙 Night Glam", "🍸 Chic", "✨ Modern"],
    "outdoor": ["☀️ Open Air", "🌿 Fresh", "🎪 Festive", "🌸 Natural"],
}

def analyze_venue_mood(location: str, event_type: str = "") -> list:
    """
    Returns mood tags for a venue based on location & type keywords.
    """
    tags = set()
    location_lower = location.lower()
    
    # Location-based moods
    for city, city_tags in VENUE_MOOD_MAP.items():
        if city in location_lower:
            tags.update(city_tags[:2])
            break
    
    # Venue type moods
    for venue_type, type_tags in VENUE_TYPE_MOODS.items():
        if venue_type in location_lower:
            tags.update(type_tags[:2])
            break
    
    # Event-type moods
    event_moods = {
        "Marriage": ["💍 Romantic", "🌸 Ethereal"],
        "Birthday": ["🎉 Festive", "🎈 Celebratory"],
        "Corporate": ["💼 Professional", "🏆 Prestigious"],
        "Meetup": ["🤝 Collaborative", "⚡ Energetic"],
    }
    if event_type in event_moods:
        tags.update(event_moods[event_type])
    
    # Defaults
    if not tags:
        tags.update(["✨ Premium", "🌟 Luxury", "🎆 Grand"])
    
    return list(tags)[:6]

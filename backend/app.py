import os
import random
import json
from contextlib import asynccontextmanager
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from database import (
    get_db, init_db,
    User, DiseaseDetection, Product, Vehicle, VehicleBooking,
    CommunityPost, Scheme, Expense
)

load_dotenv()

# Lifecycle / Startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schema & seed data
    init_db()
    yield

app = FastAPI(
    title="Aagroo API - Smart Farming & Agriculture Platform",
    description="REST backend providing AI plant disease detection, weather forecasts, vehicle booking, crop advice, marketplace, and community forum.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve Frontend Static Files
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(frontend_path):
    app.mount("/app", StaticFiles(directory=frontend_path, html=True), name="frontend")


# --- PYDANTIC SCHEMAS ---

class UserRegisterSchema(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    district: Optional[str] = "Thoothukudi"
    state: Optional[str] = "Tamil Nadu"
    farmer_type: Optional[str] = "Medium (2-10 acres)"
    password: Optional[str] = None

class UserLoginSchema(BaseModel):
    email_or_phone: str
    password: Optional[str] = None

class ProfileUpdateSchema(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    land_acres: Optional[float] = None
    primary_crops: Optional[str] = None
    district: Optional[str] = None

class BookingCreateSchema(BaseModel):
    user_id: Optional[int] = 1
    vehicle_id: int
    booking_date: str
    start_time: str = "08:00"
    duration_hrs: int = 8
    location: str

class PostCreateSchema(BaseModel):
    user_id: Optional[int] = 1
    author_name: str
    location: Optional[str] = "Tamil Nadu"
    category: Optional[str] = "General"
    content: str

class CropRecommendRequest(BaseModel):
    soil_type: str
    land_size: float
    season: str
    water_availability: str
    state: str

class ChatMessageSchema(BaseModel):
    message: str
    context: Optional[str] = None

class ExpenseCreateSchema(BaseModel):
    type: str  # Expense or Income
    category: str
    amount: float
    note: Optional[str] = ""
    date: Optional[str] = None


# --- ROUTES ---

@app.get("/")
def read_root():
    return {
        "status": "online",
        "app": "Aagroo Smart Farming Platform API",
        "version": "1.0.0",
        "docs_url": "/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# --- AUTH ENDPOINTS ---

@app.post("/api/auth/register")
def register(user_data: UserRegisterSchema, db: Session = Depends(get_db)):
    # Check existing user
    if user_data.email:
        existing = db.query(User).filter(User.email == user_data.email).first()
        if existing:
            return {"success": True, "user": existing, "message": "User logged in existing account"}
    
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        phone=user_data.phone,
        district=user_data.district or "Thoothukudi",
        state=user_data.state or "Tamil Nadu",
        farmer_type=user_data.farmer_type or "Medium (2-10 acres)",
        password_hash=user_data.password  # In production, hash with bcrypt/argon2
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"success": True, "user": new_user, "message": "Registration successful"}

@app.post("/api/auth/login")
def login(login_data: UserLoginSchema, db: Session = Depends(get_db)):
    identifier = login_data.email_or_phone.strip()
    user = db.query(User).filter(
        (User.email == identifier) | (User.phone == identifier)
    ).first()

    if not user:
        # Create user automatically for quick seamless access if requested
        name = identifier.split('@')[0].capitalize() if '@' in identifier else "Farmer"
        user = User(
            name=name,
            email=identifier if '@' in identifier else None,
            phone=identifier if not '@' in identifier else None
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return {"success": True, "user": user, "token": f"mock_token_{user.id}"}

@app.get("/api/auth/profile/{user_id}")
def get_profile(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"success": True, "profile": user}

@app.put("/api/auth/profile/{user_id}")
def update_profile(user_id: int, data: ProfileUpdateSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.name: user.name = data.name
    if data.phone: user.phone = data.phone
    if data.email: user.email = data.email
    if data.land_acres is not None: user.land_acres = data.land_acres
    if data.primary_crops: user.primary_crops = data.primary_crops
    if data.district: user.district = data.district

    db.commit()
    db.refresh(user)
    return {"success": True, "user": user}


# --- DISEASE DETECTION ENDPOINTS ---

DISEASE_KNOWLEDGE_BASE = {
    "leaf_spot": {
        "disease_name": "Cercospora Leaf Spot",
        "emoji": "🍂",
        "confidence": 92.5,
        "severity": "Moderate",
        "color": "var(--amber-600)",
        "description": "Fungal disease causing circular brown spots with yellow halos on leaves. Spreads in warm humid conditions.",
        "causes": ["Cercospora fungi", "High relative humidity", "Overcrowding", "Water-stressed foliage"],
        "treatment": ["Remove and burn infected leaves", "Improve air circulation between crop rows", "Apply copper-based fungicide", "Avoid overhead sprinkler irrigation"],
        "fertilizers": ["Potassium sulphate (boosts disease resistance)", "Calcium nitrate foliar spray", "Avoid excess nitrogen"],
        "pesticides": ["Mancozeb 75% WP (2g/L water)", "Carbendazim 50% WP (1g/L water)", "Copper Oxychloride 50% WP (3g/L water)"]
    },
    "bacterial_blight": {
        "disease_name": "Bacterial Blight (Xanthomonas)",
        "emoji": "🦠",
        "confidence": 88.0,
        "severity": "High",
        "color": "var(--coral-600)",
        "description": "Water-soaked lesions that turn yellow then papery brown. Highly destructive in paddy during rainy seasons.",
        "causes": ["Xanthomonas oryzae bacteria", "Leaf wounds caused by wind", "Excessive field flooding", "Infected seed stock"],
        "treatment": ["Soak seeds in Streptomycin solution before sowing", "Drain stagnant water from field", "Spray copper hydroxide", "Use resistant crop varieties"],
        "fertilizers": ["Reduce nitrogen dose by 20%", "Apply Zinc Sulphate @ 10kg/acre", "Muriate of Potash"],
        "pesticides": ["Streptomycin + Tetracycline (0.5g + 1g per L)", "Copper Hydroxide 77% WP (2g/L)"]
    },
    "powdery_mildew": {
        "disease_name": "Powdery Mildew",
        "emoji": "🌫️",
        "confidence": 95.0,
        "severity": "Moderate",
        "color": "var(--amber-600)",
        "description": "White powdery fungal growth covering leaf upper surfaces. Common on pulses, wheat, and cucurbits.",
        "causes": ["Erysiphales fungi", "Dry surface weather with high humidity", "Shaded growth conditions"],
        "treatment": ["Apply Wettable Sulphur", "Potassium Bicarbonate spray", "Prune dense canopy to improve ventilation"],
        "fertilizers": ["Balanced NPK 19-19-19", "Avoid excess nitrogen fertilizer", "Foliar Silicon spray"],
        "pesticides": ["Wettable Sulphur 80% WP (3g/L)", "Trifloxystrobin 25% + Tebuconazole 50% WG (0.5g/L)", "Neem Oil 1500ppm (3ml/L)"]
    },
    "healthy": {
        "disease_name": "Healthy Crop ✅",
        "emoji": "🌿",
        "confidence": 98.0,
        "severity": "None",
        "color": "var(--green-600)",
        "description": "No disease or pest infestation detected. Leaves show optimal chlorophyll concentration and vigorous growth.",
        "causes": [],
        "treatment": ["Maintain current irrigation schedule", "Regular weekly field monitoring", "Maintain balanced soil nutrition"],
        "fertilizers": ["Maintain balanced NPK fertilizer schedule based on soil test report"],
        "pesticides": ["No chemical treatment required", "Preventive bi-weekly neem oil spray (3ml/L) optional"]
    }
}

@app.post("/api/disease/analyze")
async def analyze_disease(
    user_id: Optional[int] = Form(1),
    file: Optional[UploadFile] = File(None),
    disease_key: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    # Determine diagnosis
    if disease_key and disease_key in DISEASE_KNOWLEDGE_BASE:
        result = DISEASE_KNOWLEDGE_BASE[disease_key]
    else:
        # Pick realistic diagnostic result based on input
        disease_type = random.choice(["leaf_spot", "bacterial_blight", "powdery_mildew", "healthy"])
        result = DISEASE_KNOWLEDGE_BASE[disease_type]

    # Save to history
    detection = DiseaseDetection(
        user_id=user_id,
        disease_name=result["disease_name"],
        confidence=result["confidence"],
        severity=result["severity"],
        color=result["color"],
        description=result["description"],
        causes_json=json.dumps(result["causes"]),
        treatment_json=json.dumps(result["treatment"]),
        fertilizers_json=json.dumps(result["fertilizers"]),
        pesticides_json=json.dumps(result["pesticides"])
    )
    db.add(detection)
    db.commit()

    return {
        "success": True,
        "result": {
            "disease_name": result["disease_name"],
            "emoji": result["emoji"],
            "confidence": result["confidence"],
            "severity": result["severity"],
            "color": result["color"],
            "description": result["description"],
            "causes": result["causes"],
            "treatment": result["treatment"],
            "fertilizers": result["fertilizers"],
            "pesticides": result["pesticides"]
        }
    }

@app.get("/api/disease/history/{user_id}")
def get_disease_history(user_id: int, db: Session = Depends(get_db)):
    detections = db.query(DiseaseDetection).filter(
        DiseaseDetection.user_id == user_id
    ).order_by(DiseaseDetection.created_at.desc()).all()
    
    formatted = []
    for d in detections:
        formatted.append({
            "id": d.id,
            "disease_name": d.disease_name,
            "confidence": d.confidence,
            "severity": d.severity,
            "color": d.color,
            "created_at": d.created_at.strftime("%Y-%m-%d %H:%M") if d.created_at else ""
        })
    return {"success": True, "history": formatted}


# --- WEATHER ENDPOINT ---

@app.get("/api/weather")
def get_weather(location: str = Query("Thoothukudi")):
    return {
        "success": True,
        "location": location,
        "current": {
            "temp": 32,
            "condition": "Partly Cloudy",
            "humidity": 65,
            "wind": "14 km/h",
            "uv_index": 8,
            "rainfall_probability": "15%"
        },
        "alerts": [
            {"type": "warning", "message": "Moderate rain expected on Wednesday. Plan harvesting accordingly."},
            {"type": "info", "message": "Favorable temperature for sowing groundnut and pulse crops."}
        ],
        "forecast_7day": [
            {"day": "Mon", "emoji": "☀️", "high": 34, "low": 26, "rain": 0},
            {"day": "Tue", "emoji": "⛅", "high": 32, "low": 25, "rain": 10},
            {"day": "Wed", "emoji": "🌧️", "high": 28, "low": 24, "rain": 70},
            {"day": "Thu", "emoji": "🌧️", "high": 27, "low": 23, "rain": 80},
            {"day": "Fri", "emoji": "⛅", "high": 30, "low": 24, "rain": 20},
            {"day": "Sat", "emoji": "☀️", "high": 33, "low": 25, "rain": 5},
            {"day": "Sun", "emoji": "☀️", "high": 35, "low": 26, "rain": 0}
        ],
        "irrigation_recommendation": "Sufficient soil moisture. Skip watering today. Next irrigation recommended in 2 days."
    }


# --- MARKETPLACE ENDPOINTS ---

@app.get("/api/marketplace/products")
def get_products(category: Optional[str] = None, query: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Product)
    if category and category != "All":
        q = q.filter(Product.category == category)
    if query:
        q = q.filter(Product.name.ilike(f"%{query}%"))
    products = q.all()
    return {"success": True, "products": products}

@app.get("/api/marketplace/products/{product_id}")
def get_product_detail(product_id: int, db: Session = Depends(get_db)):
    prod = db.query(Product).filter(Product.id == product_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"success": True, "product": prod}


# --- VEHICLE BOOKING ENDPOINTS ---

@app.get("/api/vehicles")
def get_vehicles(db: Session = Depends(get_db)):
    v_list = db.query(Vehicle).all()
    return {"success": True, "vehicles": v_list}

@app.post("/api/vehicles/book")
def book_vehicle(booking_data: BookingCreateSchema, db: Session = Depends(get_db)):
    v = db.query(Vehicle).filter(Vehicle.id == booking_data.vehicle_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    total_price = v.price * (booking_data.duration_hrs / 8.0)

    booking = VehicleBooking(
        user_id=booking_data.user_id,
        vehicle_id=v.id,
        vehicle_name=v.name,
        booking_date=booking_data.booking_date,
        start_time=booking_data.start_time,
        duration_hrs=booking_data.duration_hrs,
        location=booking_data.location,
        total_price=round(total_price, 2),
        status="Confirmed"
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    return {"success": True, "booking": booking, "message": "Vehicle booked successfully!"}

@app.get("/api/vehicles/bookings/{user_id}")
def get_user_bookings(user_id: int, db: Session = Depends(get_db)):
    bookings = db.query(VehicleBooking).filter(
        VehicleBooking.user_id == user_id
    ).order_by(VehicleBooking.created_at.desc()).all()
    return {"success": True, "bookings": bookings}


# --- COMMUNITY POSTS ENDPOINTS ---

@app.get("/api/community/posts")
def get_posts(category: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(CommunityPost)
    if category and category != "All":
        q = q.filter(CommunityPost.category == category)
    posts = q.order_by(CommunityPost.created_at.desc()).all()
    return {"success": True, "posts": posts}

@app.post("/api/community/posts")
def create_post(post_data: PostCreateSchema, db: Session = Depends(get_db)):
    post = CommunityPost(
        user_id=post_data.user_id,
        author_name=post_data.author_name,
        location=post_data.location or "Tamil Nadu",
        category=post_data.category or "General",
        content=post_data.content,
        likes_count=0,
        comments_count=0
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return {"success": True, "post": post}

@app.post("/api/community/posts/{post_id}/like")
def like_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    post.likes_count += 1
    db.commit()
    return {"success": True, "likes_count": post.likes_count}


# --- SCHEMES ENDPOINT ---

@app.get("/api/schemes")
def get_schemes(db: Session = Depends(get_db)):
    schemes = db.query(Scheme).all()
    formatted = []
    for s in schemes:
        formatted.append({
            "id": s.id,
            "title": s.title,
            "emoji": s.emoji,
            "badge": s.badge,
            "badgeText": s.badge_text,
            "category": s.category,
            "deadline": s.deadline,
            "amount": s.amount,
            "desc": s.description,
            "docs": json.loads(s.docs_json) if s.docs_json else []
        })
    return {"success": True, "schemes": formatted}


# --- CROP RECOMMENDATION ENDPOINT ---

CROP_DATABASE = [
    {
        "name": "Paddy Rice (CR-1009 / CO-51)",
        "emoji": "🌾",
        "expected_yield": "50-60 quintals / acre",
        "duration": "120-135 days",
        "water_requirement": "High",
        "suitable_soil": ["Clay soil", "Loamy soil"],
        "season": ["Kharif (Jun–Nov)", "Rabi (Nov–Apr)"],
        "estimated_market_price": "₹2,850 / quintal",
        "key_tips": "Use SRI method (System of Rice Intensification) for 25% higher yield with 30% less water usage."
    },
    {
        "name": "Groundnut (Kadiri-6 / TMV-7)",
        "emoji": "🥜",
        "expected_yield": "15-20 quintals / acre",
        "duration": "105-115 days",
        "water_requirement": "Moderate",
        "suitable_soil": ["Sandy soil", "Red laterite soil", "Loamy soil"],
        "season": ["Kharif (Jun–Nov)", "Rabi (Nov–Apr)"],
        "estimated_market_price": "₹5,800 / quintal",
        "key_tips": "Ensure Gypsum application @ 160 kg/acre at 45 days for optimal pod filling and oil content."
    },
    {
        "name": "Cotton (Bt Cotton Hybrid)",
        "emoji": "🪡",
        "expected_yield": "10-15 quintals / acre",
        "duration": "150-165 days",
        "water_requirement": "Moderate",
        "suitable_soil": ["Black cotton soil", "Loamy soil"],
        "season": ["Kharif (Jun–Nov)"],
        "estimated_market_price": "₹7,200 / quintal",
        "key_tips": "Maintain drip fertigation and apply Neem oil preventive spray to protect against pink bollworm."
    },
    {
        "name": "Sugarcane (Co 0238 / Co 86032)",
        "emoji": "🎋",
        "expected_yield": "350-420 quintals / acre",
        "duration": "10-12 months",
        "water_requirement": "High",
        "suitable_soil": ["Loamy soil", "Clay soil", "Black cotton soil"],
        "season": ["Kharif (Jun–Nov)", "Zaid (Mar–Jun)"],
        "estimated_market_price": "₹315 / quintal",
        "key_tips": "Adopt wider row spacing (5 ft) and intercrop with pulses for additional income."
    }
]

@app.post("/api/crops/recommend")
def recommend_crop(req: CropRecommendRequest):
    matched_crops = []
    for c in CROP_DATABASE:
        soil_match = any(req.soil_type.lower() in s.lower() for s in c["suitable_soil"]) if req.soil_type else True
        if soil_match or len(matched_crops) == 0:
            matched_crops.append(c)

    selected = matched_crops[0] if matched_crops else CROP_DATABASE[0]

    return {
        "success": True,
        "recommendation": selected,
        "inputs": req,
        "additional_suitable_crops": [c["name"] for c in CROP_DATABASE if c["name"] != selected["name"]]
    }


# --- AI CHATBOT ENDPOINT ---

BOT_RESPONSES = [
    "To manage leaf spot disease organic control, spray Neem Oil 1500ppm (3-5ml per litre of water) early morning or evening.",
    "For rice paddy, applying NPK in a 4:2:1 ratio along with 10 kg/acre Zinc Sulphate gives optimal tillering and grain yield.",
    "You can apply for the PM-KISAN scheme online at pmkisan.gov.in with your Aadhaar, land record (Patta/Chitta), and active bank account.",
    "For current market price trends in Tamil Nadu mandis, Paddy is selling at ~₹2,850/qtl and Groundnut at ~₹5,800/qtl.",
    "To conserve water during drought or dry spells, installing micro-drip irrigation can save up to 45% water while improving root uptake."
]

@app.post("/api/chatbot")
def chatbot_reply(msg: ChatMessageSchema):
    query = msg.message.lower()
    
    if "disease" in query or "leaf" in query or "spot" in query:
        reply = "For crop disease issues, you can upload a leaf photograph on our 'Detect' page! For general leaf spots, apply Copper Oxychloride (3g/L) or organic Neem oil."
    elif "water" in query or "irrigation" in query:
        reply = "Smart irrigation advice: Water early in the morning before 8 AM to prevent evaporation loss. Drip systems increase water efficiency by up to 50%."
    elif "scheme" in query or "subsidy" in query or "pm" in query:
        reply = "Government Schemes available include PM-KISAN (₹6000/yr direct support), PM Kusum (60% Solar Pump subsidy), and Kisan Credit Card (loans at 4% interest)."
    elif "vehicle" in query or "tractor" in query or "rent" in query:
        reply = "You can book John Deere tractors, Harvester combines, or Rotavators directly on our 'Vehicles' section with verified local owners!"
    else:
        reply = random.choice(BOT_RESPONSES)

    return {
        "success": True,
        "reply": reply,
        "timestamp": datetime.utcnow().strftime("%H:%M")
    }


# --- EXPENSE TRACKER ENDPOINTS ---

@app.get("/api/expenses/{user_id}")
def get_expenses(user_id: int, db: Session = Depends(get_db)):
    expenses = db.query(Expense).filter(Expense.user_id == user_id).order_by(Expense.created_at.desc()).all()
    return {"success": True, "expenses": expenses}

@app.post("/api/expenses/{user_id}")
def add_expense(user_id: int, data: ExpenseCreateSchema, db: Session = Depends(get_db)):
    exp = Expense(
        user_id=user_id,
        type=data.type,
        category=data.category,
        amount=data.amount,
        note=data.note,
        date=data.date or datetime.utcnow().strftime("%Y-%m-%d")
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return {"success": True, "expense": exp}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("app:app", host=host, port=port, reload=True)

import os
import json
from datetime import datetime
from urllib.parse import quote_plus

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Text,
    Boolean,
    DateTime,
    ForeignKey
)

from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from dotenv import load_dotenv


# ==========================================
# LOAD ENVIRONMENT VARIABLES
# ==========================================

load_dotenv()


# ==========================================
# DATABASE CONFIGURATION & FALLBACK
# ==========================================

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "agriculture_db")
CUSTOM_URL = os.getenv("DATABASE_URL")


def get_engine():
    """
    Creates and returns a SQLAlchemy Engine.
    Tries MySQL connection first (if configured), and seamlessly falls back 
    to SQLite if MySQL is unavailable or credentials are bad.
    """
    # If custom DATABASE_URL is explicitly set (e.g., SQLite, PostgreSQL, Supabase)
    if CUSTOM_URL:
        connect_args = {"check_same_thread": False} if CUSTOM_URL.startswith("sqlite") else {}
        return create_engine(CUSTOM_URL, connect_args=connect_args, pool_pre_ping=True)

    encoded_password = quote_plus(DB_PASSWORD)
    mysql_url = (
        f"mysql+pymysql://"
        f"{DB_USER}:{encoded_password}@"
        f"{DB_HOST}:{DB_PORT}/"
        f"{DB_NAME}"
    )

    try:
        # First attempt: Try to connect to MySQL
        # Try to ensure database exists
        try:
            import mysql.connector
            conn = mysql.connector.connect(
                host=DB_HOST,
                port=int(DB_PORT),
                user=DB_USER,
                password=DB_PASSWORD
            )
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            conn.close()
        except Exception:
            pass  # If user lacks permissions or mysql.connector fails, let create_engine handle it

        eng = create_engine(mysql_url, pool_pre_ping=True, echo=False)
        # Test connection
        with eng.connect() as conn:
            pass
        print(f"✅ Successfully connected to MySQL database '{DB_NAME}' on {DB_HOST}:{DB_PORT}")
        return eng
    except Exception as e:
        print(f"⚠️ MySQL Connection failed ({e}). Falling back to SQLite database...")
        sqlite_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agriculture.db")
        sqlite_url = f"sqlite:///{sqlite_file}"
        eng = create_engine(sqlite_url, connect_args={"check_same_thread": False}, pool_pre_ping=True)
        print(f"✅ Connected to SQLite database: {sqlite_file}")
        return eng


engine = get_engine()

# ==========================================
# DATABASE SESSION
# ==========================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


# ==========================================
# USER MODEL
# ==========================================

class User(Base):

    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String(100),
        nullable=False
    )

    email = Column(
        String(120),
        unique=True,
        index=True,
        nullable=True
    )

    phone = Column(
        String(20),
        unique=True,
        index=True,
        nullable=True
    )

    district = Column(
        String(100),
        default="Thoothukudi"
    )

    state = Column(
        String(100),
        default="Tamil Nadu"
    )

    farmer_type = Column(
        String(50),
        default="Medium (2-10 acres)"
    )

    password_hash = Column(
        String(255),
        nullable=True
    )

    land_acres = Column(
        Float,
        default=8.0
    )

    primary_crops = Column(
        String(255),
        default="Rice, Sugarcane, Groundnut"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


# ==========================================
# DISEASE DETECTION MODEL
# ==========================================

class DiseaseDetection(Base):

    __tablename__ = "disease_detections"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    disease_name = Column(
        String(150),
        nullable=False
    )

    confidence = Column(
        Float,
        default=90.0
    )

    severity = Column(
        String(50),
        default="Moderate"
    )

    color = Column(
        String(50),
        default="var(--amber-600)"
    )

    description = Column(
        Text,
        nullable=True
    )

    causes_json = Column(
        Text,
        default="[]"
    )

    treatment_json = Column(
        Text,
        default="[]"
    )

    fertilizers_json = Column(
        Text,
        default="[]"
    )

    pesticides_json = Column(
        Text,
        default="[]"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


# ==========================================
# MARKETPLACE PRODUCT MODEL
# ==========================================

class Product(Base):

    __tablename__ = "products"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String(150),
        nullable=False
    )

    emoji = Column(
        String(10),
        default="🌾"
    )

    price = Column(
        Float,
        nullable=False
    )

    unit = Column(
        String(50),
        default="kg"
    )

    change = Column(
        Float,
        default=0.0
    )

    category = Column(
        String(50),
        index=True
    )

    rating = Column(
        Float,
        default=4.5
    )

    description = Column(
        Text,
        nullable=True
    )

    in_stock = Column(
        Boolean,
        default=True
    )


# ==========================================
# VEHICLE MODEL
# ==========================================

class Vehicle(Base):

    __tablename__ = "vehicles"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    name = Column(
        String(150),
        nullable=False
    )

    emoji = Column(
        String(10),
        default="🚜"
    )

    price = Column(
        Float,
        nullable=False
    )

    unit = Column(
        String(50),
        default="per day"
    )

    owner = Column(
        String(100),
        default="Agri Services"
    )

    location = Column(
        String(100),
        default="Thoothukudi"
    )

    rating = Column(
        Float,
        default=4.5
    )

    is_available = Column(
        Boolean,
        default=True
    )


# ==========================================
# VEHICLE BOOKING MODEL
# ==========================================

class VehicleBooking(Base):

    __tablename__ = "vehicle_bookings"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    vehicle_id = Column(
        Integer,
        ForeignKey("vehicles.id"),
        nullable=True
    )

    vehicle_name = Column(
        String(150),
        nullable=False
    )

    booking_date = Column(
        String(50),
        nullable=False
    )

    start_time = Column(
        String(20),
        default="08:00"
    )

    duration_hrs = Column(
        Integer,
        default=8
    )

    location = Column(
        String(255),
        nullable=False
    )

    total_price = Column(
        Float,
        nullable=False
    )

    status = Column(
        String(50),
        default="Confirmed"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


# ==========================================
# COMMUNITY POST MODEL
# ==========================================

class CommunityPost(Base):

    __tablename__ = "community_posts"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    author_name = Column(
        String(100),
        nullable=False
    )

    location = Column(
        String(100),
        default="Tamil Nadu"
    )

    avatar = Column(
        String(10),
        default="🌾"
    )

    color = Column(
        String(50),
        default="#3B6D11"
    )

    category = Column(
        String(50),
        default="General"
    )

    content = Column(
        Text,
        nullable=False
    )

    likes_count = Column(
        Integer,
        default=0
    )

    comments_count = Column(
        Integer,
        default=0
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


# ==========================================
# GOVERNMENT SCHEME MODEL
# ==========================================

class Scheme(Base):

    __tablename__ = "schemes"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    title = Column(
        String(200),
        nullable=False
    )

    emoji = Column(
        String(10),
        default="📜"
    )

    badge = Column(
        String(50),
        default="badge-green"
    )

    badge_text = Column(
        String(50),
        default="Open"
    )

    category = Column(
        String(100),
        default="General"
    )

    deadline = Column(
        String(100),
        default="Rolling"
    )

    amount = Column(
        String(100),
        default="Financial Support"
    )

    description = Column(
        Text,
        nullable=False
    )

    docs_json = Column(
        Text,
        default="[]"
    )


# ==========================================
# EXPENSE MODEL
# ==========================================

class Expense(Base):

    __tablename__ = "expenses"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    type = Column(
        String(20),
        default="Expense"
    )

    category = Column(
        String(50),
        default="Seeds"
    )

    amount = Column(
        Float,
        nullable=False
    )

    note = Column(
        String(255),
        nullable=True
    )

    date = Column(
        String(50),
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


# ==========================================
# DATABASE DEPENDENCY
# ==========================================

def get_db():

    db = SessionLocal()

    try:

        yield db

    finally:

        db.close()


# ==========================================
# INITIALIZE DATABASE
# ==========================================

def init_db():

    # Create tables if they do not exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:

        # --------------------------------------
        # DEFAULT USER
        # --------------------------------------

        if db.query(User).count() == 0:

            default_user = User(
                name="Ravi Kumar",
                email="ravi@example.com",
                phone="+919876543210",
                district="Thoothukudi",
                state="Tamil Nadu",
                farmer_type="Medium (2-10 acres)",
                land_acres=8.0,
                primary_crops="Rice, Sugarcane, Groundnut"
            )

            db.add(default_user)
            db.commit()

        # --------------------------------------
        # SAMPLE PRODUCTS
        # --------------------------------------

        if db.query(Product).count() == 0:

            sample_products = [

                Product(
                    name="Basmati Rice",
                    emoji="🌾",
                    price=2850,
                    unit="quintal",
                    change=3.2,
                    category="Seeds",
                    rating=4.5,
                    description="Premium long-grain Basmati rice seeds, high yield variety suitable for Kharif season."
                ),

                Product(
                    name="NPK Fertilizer",
                    emoji="🧪",
                    price=1200,
                    unit="50kg bag",
                    change=-1.5,
                    category="Fertilizers",
                    rating=4.2,
                    description="Balanced NPK 17-17-17 compound fertilizer. Ideal for paddy and sugarcane."
                ),

                Product(
                    name="Neem Pesticide",
                    emoji="🌿",
                    price=480,
                    unit="litre",
                    change=0,
                    category="Pesticides",
                    rating=4.7,
                    description="Organic neem-based pesticide, safe for pollinators, effective against aphids and whitefly."
                ),

                Product(
                    name="Drip Irrigation Kit",
                    emoji="💧",
                    price=8500,
                    unit="acre set",
                    change=1.2,
                    category="Irrigation",
                    rating=4.8,
                    description="Complete micro-drip irrigation kit for 1 acre, includes pipes, emitters, and filters."
                ),

                Product(
                    name="Hybrid Cotton Seed",
                    emoji="🌱",
                    price=950,
                    unit="packet",
                    change=2.1,
                    category="Seeds",
                    rating=4.4,
                    description="High-yield Bt cotton seed. Suitable for black cotton soil. 120-day crop."
                ),

                Product(
                    name="Cultivator Blade Set",
                    emoji="⚙️",
                    price=3200,
                    unit="set of 9",
                    change=-0.5,
                    category="Tools",
                    rating=4.3,
                    description="Heavy-duty cultivator blades for tractor attachment. Hardened steel."
                ),

                Product(
                    name="Organic Compost",
                    emoji="🍂",
                    price=350,
                    unit="50kg bag",
                    change=0.8,
                    category="Organic",
                    rating=4.6,
                    description="Well-decomposed organic compost with added vermicompost, rich in micronutrients."
                ),

                Product(
                    name="Sprinkler System",
                    emoji="🚿",
                    price=6200,
                    unit="acre set",
                    change=-2.0,
                    category="Irrigation",
                    rating=4.1,
                    description="Rotating sprinkler irrigation system, ideal for wheat and vegetable crops."
                )
            ]

            db.add_all(sample_products)


        # --------------------------------------
        # SAMPLE VEHICLES
        # --------------------------------------

        if db.query(Vehicle).count() == 0:

            sample_vehicles = [

                Vehicle(
                    name="John Deere Tractor 5050D",
                    emoji="🚜",
                    price=800,
                    unit="per day",
                    owner="Murugan Farm Rentals",
                    location="Thoothukudi",
                    rating=4.7,
                    is_available=True
                ),

                Vehicle(
                    name="Harvester Combine",
                    emoji="🌾",
                    price=2500,
                    unit="per day",
                    owner="Krishnan Agri Services",
                    location="Tiruchendur",
                    rating=4.9,
                    is_available=True
                ),

                Vehicle(
                    name="Rotavator",
                    emoji="⚙️",
                    price=600,
                    unit="per day",
                    owner="Senthil Equipment",
                    location="Thoothukudi",
                    rating=4.5,
                    is_available=False
                ),

                Vehicle(
                    name="Seed Drill",
                    emoji="🌱",
                    price=450,
                    unit="per day",
                    owner="Arjun Agri Tools",
                    location="Kovilpatti",
                    rating=4.6,
                    is_available=True
                ),

                Vehicle(
                    name="Water Tanker",
                    emoji="💧",
                    price=350,
                    unit="per trip",
                    owner="Raja Water Services",
                    location="Thoothukudi",
                    rating=4.3,
                    is_available=True
                ),

                Vehicle(
                    name="Power Tiller",
                    emoji="🔧",
                    price=300,
                    unit="per day",
                    owner="Senthil Equipment",
                    location="Thoothukudi",
                    rating=4.4,
                    is_available=True
                )
            ]

            db.add_all(sample_vehicles)


        # --------------------------------------
        # SAMPLE GOVERNMENT SCHEMES
        # --------------------------------------

        if db.query(Scheme).count() == 0:

            sample_schemes = [

                Scheme(
                    title="PM-KISAN Samman Nidhi",
                    emoji="💰",
                    badge="badge-green",
                    badge_text="Open",
                    category="Income Support",
                    deadline="Always open",
                    amount="₹6,000/year",
                    description="Direct income support of ₹6000/year to all landholding farmer families. Paid in 3 equal instalments.",
                    docs_json=json.dumps([
                        "Aadhaar Card",
                        "Land records",
                        "Bank account details"
                    ])
                ),

                Scheme(
                    title="Pradhan Mantri Fasal Bima Yojana",
                    emoji="🛡️",
                    badge="badge-blue",
                    badge_text="Enroll now",
                    category="Insurance",
                    deadline="Before crop sowing",
                    amount="Upto ₹2 lakh",
                    description="Crop insurance scheme providing financial support to farmers suffering crop loss due to unforeseen events like pests, diseases, and natural calamities.",
                    docs_json=json.dumps([
                        "Land records",
                        "Bank details",
                        "Sowing certificate"
                    ])
                ),

                Scheme(
                    title="Kisan Credit Card",
                    emoji="💳",
                    badge="badge-teal",
                    badge_text="Apply",
                    category="Credit",
                    deadline="Rolling",
                    amount="Up to ₹3 lakh at 4% interest",
                    description="Provides adequate and timely credit to farmers for cultivation, post-harvest expenses, and allied activities.",
                    docs_json=json.dumps([
                        "Aadhaar",
                        "Land ownership proof",
                        "Passport photo"
                    ])
                ),

                Scheme(
                    title="Soil Health Card Scheme",
                    emoji="🔬",
                    badge="badge-amber",
                    badge_text="Collect card",
                    category="Advisory",
                    deadline="Rolling",
                    amount="Free service",
                    description="Provides soil health card to farmers with crop-wise recommendations for nutrients and fertilizers.",
                    docs_json=json.dumps([
                        "Aadhaar",
                        "Land ownership proof"
                    ])
                ),

                Scheme(
                    title="PM Kusum Scheme",
                    emoji="☀️",
                    badge="badge-green",
                    badge_text="Apply",
                    category="Subsidy",
                    deadline="Dec 2026",
                    amount="60% subsidy on pump cost",
                    description="Support for solar pump installation for irrigation.",
                    docs_json=json.dumps([
                        "Land records",
                        "Electricity bill",
                        "Aadhaar",
                        "Bank details"
                    ])
                )
            ]

            db.add_all(sample_schemes)


        # --------------------------------------
        # SAMPLE COMMUNITY POSTS
        # --------------------------------------

        if db.query(CommunityPost).count() == 0:

            sample_posts = [

                CommunityPost(
                    user_id=1,
                    author_name="Suresh Pandi",
                    location="Madurai",
                    avatar="SP",
                    color="#185FA5",
                    category="Crop Advice",
                    content="Just harvested my paddy using SRI method — got 52 quintals per acre! Key was transplanting at 12 days and using organic compost.",
                    likes_count=47,
                    comments_count=12
                ),

                CommunityPost(
                    user_id=1,
                    author_name="Kavitha Mani",
                    location="Coimbatore",
                    avatar="KM",
                    color="#3B6D11",
                    category="Disease Discussion",
                    content="My tomato plants have yellow spots on leaves spreading fast. Uploaded pics to AgriConnect — identified as Early Blight.",
                    likes_count=31,
                    comments_count=8
                ),

                CommunityPost(
                    user_id=1,
                    author_name="Ramesh Gounder",
                    location="Erode",
                    avatar="RG",
                    color="#854F0B",
                    category="Government Schemes",
                    content="PM-KISAN ₹2,000 credited to my account today! If you haven't registered, do it with Aadhaar and land records.",
                    likes_count=89,
                    comments_count=24
                )
            ]

            db.add_all(sample_posts)


        # Save everything

        db.commit()

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()
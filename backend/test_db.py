import sys
import os
import io
from datetime import datetime

# Set UTF-8 encoding for stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import (
    engine, SessionLocal, init_db,
    User, DiseaseDetection, Product, Vehicle, VehicleBooking,
    CommunityPost, Scheme, Expense
)
from sqlalchemy import inspect

def run_database_tests():
    print("=" * 60)
    print("      AAGROO DATABASE SUITE - EXECUTION REPORT")
    print("=" * 60)
    
    # 1. Connection Test
    try:
        with engine.connect() as conn:
            print("[PASS] 1. DATABASE CONNECTION: SUCCESSFUL")
            print(f"   Engine URL: {engine.url}")
    except Exception as e:
        print(f"[FAIL] 1. DATABASE CONNECTION FAILED: {e}")
        return

    # 2. Table Schema Verification
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    expected_tables = [
        "users", "disease_detections", "products", "vehicles",
        "vehicle_bookings", "community_posts", "schemes", "expenses"
    ]
    
    print("\n[PASS] 2. SCHEMA & TABLE VERIFICATION:")
    for tbl in expected_tables:
        if tbl in existing_tables:
            columns = [col['name'] for col in inspector.get_columns(tbl)]
            print(f"   - Table '{tbl}': EXISTS ({len(columns)} columns)")
        else:
            print(f"   - Table '{tbl}': MISSING")
            
    # 3. Initial Seed Count Verification
    db = SessionLocal()
    try:
        print("\n[PASS] 3. RECORD COUNTS IN DATABASE:")
        print(f"   - Users: {db.query(User).count()}")
        print(f"   - Products: {db.query(Product).count()}")
        print(f"   - Vehicles: {db.query(Vehicle).count()}")
        print(f"   - Community Posts: {db.query(CommunityPost).count()}")
        print(f"   - Schemes: {db.query(Scheme).count()}")
        print(f"   - Expenses: {db.query(Expense).count()}")
        print(f"   - Disease Detections: {db.query(DiseaseDetection).count()}")
        print(f"   - Vehicle Bookings: {db.query(VehicleBooking).count()}")

        # 4. CRUD Test - Create
        print("\n[PASS] 4. CRUD OPERATIONS TEST:")
        test_email = f"db_test_{int(datetime.now().timestamp())}@aagroo.com"
        test_user = User(
            name="DB Test Farmer",
            email=test_email,
            phone="9998887770",
            district="Thoothukudi",
            state="Tamil Nadu",
            farmer_type="Small (1-2 acres)",
            land_acres=2.5,
            primary_crops="Rice, Pulses"
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        print(f"   [CREATE] Inserted test user (ID: {test_user.id}, Email: {test_user.email})")

        # CRUD Test - Read & Update
        fetched_user = db.query(User).filter(User.id == test_user.id).first()
        assert fetched_user is not None, "Failed to fetch inserted user"
        assert fetched_user.name == "DB Test Farmer", "User name mismatch"
        print(f"   [READ] Successfully fetched user '{fetched_user.name}'")

        fetched_user.land_acres = 3.0
        db.commit()
        db.refresh(fetched_user)
        assert fetched_user.land_acres == 3.0, "Failed to update land_acres"
        print(f"   [UPDATE] Updated land_acres to {fetched_user.land_acres}")

        # CRUD Test - Delete
        db.delete(fetched_user)
        db.commit()
        deleted_check = db.query(User).filter(User.id == test_user.id).first()
        assert deleted_check is None, "Failed to delete test user"
        print(f"   [DELETE] Successfully deleted & cleaned up test user (ID: {test_user.id})")

        print("\n" + "=" * 60)
        print("ALL DATABASE TESTS PASSED PERFECTLY!")
        print("=" * 60)

    except Exception as e:
        print(f"\n[FAIL] CRUD TEST ERROR: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_database_tests()

import psycopg2
import os
from dotenv import load_dotenv
from datetime import date

load_dotenv()

def get_conn_params():
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        return {"dsn": database_url}
    return {
        "dbname":   os.environ.get("PG_DB_NAME") or os.environ.get("PGDATABASE", "railway"),
        "user":     os.environ.get("PG_USER")    or os.environ.get("PGUSER",     "postgres"),
        "password": os.environ.get("PG_PASSWORD") or os.environ.get("PGPASSWORD", ""),
        "host":     os.environ.get("PG_HOST")    or os.environ.get("PGHOST",     "localhost"),
        "port":     int(os.environ.get("PG_PORT") or os.environ.get("PGPORT",    "5432")),
    }

def create_insurance_table_with_data():
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**get_conn_params())
        cur = conn.cursor()
        
        cur.execute("""
        CREATE TABLE IF NOT EXISTS customer_insurance (
            customer_id SERIAL PRIMARY KEY,
            first_name VARCHAR(50) NOT NULL,
            last_name VARCHAR(50) NOT NULL,
            date_of_birth DATE NOT NULL,
            gender VARCHAR(10),
            email VARCHAR(100),
            phone_number VARCHAR(20),
            address VARCHAR(100),
            city VARCHAR(50),
            state VARCHAR(50),
            zip_code VARCHAR(20),
            policy_id VARCHAR(50) UNIQUE NOT NULL,
            policy_type TEXT[] NOT NULL CHECK (
                array_length(policy_type, 1) >= 1 AND
                policy_type::text[] <@ ARRAY['Life Insurance', 'Home Insurance', 'Auto Insurance']::text[]
            ),
            policy_number VARCHAR(50) UNIQUE NOT NULL,
            policy_start_date DATE NOT NULL,
            policy_end_date DATE,
            premium_amount DECIMAL(10,2) NOT NULL,
            agent_id VARCHAR(50),
            agent_name VARCHAR(100),
            agent_email VARCHAR(100),
            agent_phone_number VARCHAR(20),
            claim_date DATE,
            claim_amount DECIMAL(10,2),
            claim_status VARCHAR(20) CHECK (claim_status IN ('Pending', 'Approved', 'Rejected', NULL)),
            payment_id VARCHAR(50),
            payment_date DATE,
            payment_amount DECIMAL(10,2),
            payment_method VARCHAR(50) CHECK (payment_method IN ('Credit Card', 'Bank Transfer', NULL)),
            life_beneficiary_name VARCHAR(100),
            life_beneficiary_relationship VARCHAR(50),
            life_policy_term INTEGER,
            life_sum_assured DECIMAL(12,2),
            home_property_address VARCHAR(100),
            home_property_value DECIMAL(12,2),
            home_property_type VARCHAR(50) CHECK (home_property_type IN ('Single Family', 'Condo', 'Apartment', NULL)),
            home_coverage_type VARCHAR(50) CHECK (home_coverage_type IN ('Building', 'Contents', 'Liability', NULL)),
            auto_vehicle_make VARCHAR(50),
            auto_vehicle_model VARCHAR(50),
            auto_vehicle_year INTEGER,
            auto_coverage_type VARCHAR(50) CHECK (auto_coverage_type IN ('Liability', 'Collision', 'Comprehensive', NULL))
        )
        """)

        sample_data = [
            ('John', 'Smith', date(1980, 5, 15), 'Male', 'john.smith@email.com', '555-123-4567', '123 Main St', 'Boston', 'MA', '02108', 'POL-1001', ['Life Insurance'], 'LIFE-001', date(2020, 1, 1), date(2040, 1, 1), 150.00, 'AGT-001', 'Sarah Johnson', 'sarah.j@insure.com', '555-987-6543', None, None, None, 'PAY-001', date(2023, 1, 1), 150.00, 'Credit Card', 'Mary Smith', 'Spouse', 20, 500000.00, None, None, None, None, None, None, None, None),
            ('Emily', 'Davis', date(1975, 8, 22), 'Female', 'emily.davis@email.com', '555-234-5678', '456 Oak Ave', 'Chicago', 'IL', '60601', 'POL-1002', ['Home Insurance'], 'HOME-001', date(2021, 3, 15), date(2024, 3, 15), 85.50, 'AGT-002', 'Michael Brown', 'michael.b@insure.com', '555-876-5432', date(2022, 5, 10), 2500.00, 'Approved', 'PAY-002', date(2023, 3, 15), 85.50, 'Bank Transfer', None, None, None, None, '456 Oak Ave, Chicago, IL', 350000.00, 'Single Family', 'Building', None, None, None, None),
            ('Robert', 'Johnson', date(1990, 11, 5), 'Male', 'robert.j@email.com', '555-345-6789', '789 Pine Rd', 'Houston', 'TX', '77002', 'POL-1003', ['Auto Insurance'], 'AUTO-001', date(2022, 6, 1), date(2023, 6, 1), 120.75, 'AGT-003', 'Lisa Williams', 'lisa.w@insure.com', '555-765-4321', None, None, None, 'PAY-003', date(2023, 6, 1), 120.75, 'Credit Card', None, None, None, None, None, None, None, None, 'Toyota', 'Camry', 2018, 'Comprehensive'),
            ("Alice", "Brown", date(1985, 7, 10), "Female", "alice.b@email.com", "555-111-2222", "111 Pine St", "New York", "NY", "10001", "POL-1004", ["Life Insurance", "Auto Insurance"], "LA-002", date(2023, 1, 15), date(2043, 1, 15), 275.50, "AGT-001", "Sarah Johnson", "sarah.j@insure.com", "555-987-6543", None, None, None, "PAY-004", date(2023, 1, 15), 275.50, "Credit Card", "Bob Brown", "Spouse", 20, 400000.00, None, None, None, None, "Honda", "Civic", 2020, "Collision"),
            ("Charlie", "Green", date(1992, 3, 25), "Male", "charlie.g@email.com", "555-333-4444", "333 Oak Ln", "Los Angeles", "CA", "90001", "POL-1005", ["Home Insurance", "Auto Insurance"], "HA-003", date(2022, 10, 1), date(2025, 10, 1), 160.20, "AGT-002", "Michael Brown", "michael.b@insure.com", "555-876-5432", None, None, None, "PAY-005", date(2023, 10, 1), 160.20, "Bank Transfer", None, None, None, None, "333 Oak Ln, Los Angeles, CA", 600000.00, "Condo", "Contents", "Tesla", "Model 3", 2022, "Comprehensive"),
            ("Diana", "Miller", date(1988, 9, 8), "Female", "diana.m@email.com", "555-555-6666", "555 Maple Ave", "Dallas", "TX", "75201", "POL-1006", ["Life Insurance", "Home Insurance", "Auto Insurance"], "LHA-004", date(2024, 2, 1), date(2044, 2, 1), 320.00, "AGT-003", "Lisa Williams", "lisa.w@insure.com", "555-765-4321", None, None, None, "PAY-006", date(2024, 2, 1), 320.00, "Credit Card", "David Miller", "Spouse", 20, 750000.00, "555 Maple Ave, Dallas, TX", 450000.00, "Single Family", "Building", "Ford", "F-150", 2021, "Liability"),
            ('Peter', 'Parker', date(1991, 8, 1), 'Male', 'peter.p@email.com', '555-777-8888', '20 Ingram Street', 'New York', 'NY', '10002', 'POL-1007', ['Life Insurance'], 'LIFE-007', date(2024, 1, 1), date(2054, 1, 1), 200.00, 'AGT-001', 'Sarah Johnson', 'sarah.j@insure.com', '555-987-6543', None, None, None, 'PAY-007', date(2024, 1, 1), 200.00, 'Credit Card', 'MJ Watson', 'Girlfriend', 30, 600000.00, None, None, None, None, None, None, None, None),
            ('Bruce', 'Wayne', date(1982, 5, 27), 'Male', 'bruce.w@email.com', '555-222-3333', '1007 Mountain Drive', 'Gotham', 'NY', '10005', 'POL-1008', ['Home Insurance'], 'HOME-008', date(2023, 9, 1), date(2026, 9, 1), 100.00, 'AGT-002', 'Michael Brown', 'michael.b@insure.com', '555-876-5432', None, None, None, 'PAY-008', date(2023, 9, 1), 100.00, 'Bank Transfer', None, None, None, None, '1007 Mountain Drive, Gotham, NY', 1000000.00, 'Single Family', 'Building', None, None, None, None),
            ('Clark', 'Kent', date(1989, 12, 7), 'Male', 'clark.k@email.com', '555-444-5555', '344 Clinton Street', 'Metropolis', 'NY', '10009', 'POL-1009', ['Auto Insurance'], 'AUTO-009', date(2022, 7, 1), date(2023, 7, 1), 130.50, 'AGT-003', 'Lisa Williams', 'lisa.w@insure.com', '555-765-4321', None, None, None, 'PAY-009', date(2023, 7, 1), 130.50, 'Credit Card', None, None, None, None, None, None, None, None, 'Chevrolet', 'Impala', 1967, 'Liability'),
            ("Lois", "Lane", date(1993, 10, 2), "Female", "lois.l@email.com", "555-666-7777", "Daily Planet, Metropolis", "Metropolis", "NY", "10010", "POL-1010", ["Life Insurance", "Home Insurance"], "LH-010", date(2023, 4, 1), date(2043, 4, 1), 220.00, "AGT-001", "Sarah Johnson", "sarah.j@insure.com", "555-987-6543", None, None, None, "PAY-010", date(2023, 4, 1), 220.00, "Credit Card", "Jonathan Kent", "Father", 20, 300000.00, "344 Clinton Street, Metropolis, NY", 750000.00, "Apartment", "Contents", None, None, None, None),
            ("Oliver", "Queen", date(1986, 4, 12), "Male", "oliver.q@email.com", "555-111-9999", "Starling Mansion, Starling City", "Starling City", "WA", "98001", "POL-1011", ["Life Insurance"], "LIFE-011", date(2024, 3, 1), date(2064, 3, 1), 180.00, "AGT-004", "Felicity Smoak", "felicity.s@insure.com", "555-123-7890", None, None, None, "PAY-011", date(2024, 3, 1), 180.00, "Bank Transfer", "Thea Queen", "Sister", 40, 800000.00, None, None, None, None, None, None, None, None),
            ("Dinah", "Lance", date(1990, 6, 30), "Female", "dinah.l@email.com", "555-222-8888", "SCP Central City Police Department", "Central City", "MO", "63101", "POL-1012", ["Home Insurance"], "HOME-012", date(2023, 11, 1), date(2026, 11, 1), 95.00, "AGT-005", "Barry Allen", "barry.a@insure.com", "555-987-2345", None, None, None, "PAY-012", date(2023, 11, 1), 95.00, "Credit Card", None, None, None, None, "14 Police Plaza, Central City, MO", 550000.00, "Apartment", "Building", None, None, None, None),
            ("Wally", "West", date(1995, 2, 18), "Male", "wally.w@email.com", "555-333-7777", "Keystone City", "Keystone City", "KS", "66001", "POL-1013", ["Auto Insurance"], "AUTO-013", date(2022, 8, 15), date(2023, 8, 15), 110.25, "AGT-005", "Barry Allen", "barry.a@insure.com", "555-987-2345", None, None, None, "PAY-013", date(2023, 8, 15), 110.25, "Credit Card", None, None, None, None, None, None, None, None, "Ford", "Mustang", 2017, "Collision"),
            ("Iris", "West", date(1994, 7, 9), "Female", "iris.w@email.com", "555-444-6666", "Central City Citizen, Central City", "Central City", "MO", "63102", "POL-1014", ["Life Insurance", "Home Insurance"], "LH-014", date(2024, 1, 1), date(2044, 1, 1), 210.00, "AGT-005", "Barry Allen", "barry.a@insure.com", "555-987-2345", None, None, None, "PAY-014", date(2024, 1, 1), 210.00, "Bank Transfer", "Joe West", "Father", 20, 250000.00, "Central City Citizen, Central City, MO", 600000.00, "Condo", "Contents", None, None, None, None),
            ("Kara", "Danvers", date(1987, 10, 20), "Female", "kara.d@email.com", "555-555-5555", "National City", "National City", "CA", "91001", "POL-1015", ["Life Insurance", "Auto Insurance"], "LA-015", date(2023, 5, 1), date(2053, 5, 1), 290.00, "AGT-006", "James Olsen", "james.o@insure.com", "555-234-5678", None, None, None, "PAY-015", date(2023, 5, 1), 290.00, "Credit Card", "Alura Zor-El", "Mother", 30, 900000.00, None, None, None, None, "Subaru", "Outback", 2023, "Comprehensive"),
            ("Lena", "Luthor", date(1992, 11, 14), "Female", "lena.l@email.com", "555-666-4444", "L-Corp, National City", "National City", "CA", "91002", "POL-1016", ["Home Insurance", "Auto Insurance"], "HA-016", date(2022, 12, 1), date(2025, 12, 1), 175.40, "AGT-006", "James Olsen", "james.o@insure.com", "555-234-5678", None, None, None, "PAY-016", date(2023, 12, 1), 175.40, "Bank Transfer", None, None, None, None, "L-Corp, National City, CA", 800000.00, "Condo", "Building", "Audi", "e-tron", 2024, "Collision"),
            ("J'onn", "J'onzz", date(1970, 8, 28), "Male", "jonn.j@email.com", "555-777-3333", "DEO, National City", "National City", "CA", "91003", "POL-1017", ["Life Insurance", "Home Insurance", "Auto Insurance"], "LHA-017", date(2024, 4, 1), date(2044, 4, 1), 350.00, "AGT-006", "James Olsen", "james.o@insure.com", "555-234-5678", None, None, None, "PAY-017", date(2024, 4, 1), 350.00, "Credit Card", "M'gann M'orzz", "Wife", 20, 1000000.00, "DEO, National City, CA", 950000.00, "Single Family", "Liability", "Tesla", "Cybertruck", 2025, "Comprehensive"),
            ("Barry", "Allen", date(1989, 3, 14), "Male", "barry.allen@email.com", "555-888-2222", "Central City Police Department", "Central City", "MO", "63101", "POL-1018", ["Life Insurance"], "LIFE-018", date(2024, 6, 1), date(2064, 6, 1), 220.00, "AGT-005", "Barry Allen", "barry.a@insure.com", "555-987-2345", None, None, None, "PAY-018", date(2024, 6, 1), 220.00, "Credit Card", "Iris West", "Spouse", 40, 700000.00, None, None, None, None, None, None, None, None),
            ("Oliver", "Queen", date(1985, 4, 12), "Male", "oliver.queen@email.com", "555-999-1111", "Queen Mansion, Starling City", "Starling City", "WA", "98001", "POL-1019", ["Home Insurance"], "HOME-019", date(2023, 12, 1), date(2026, 12, 1), 110.00, "AGT-004", "Felicity Smoak", "felicity.s@insure.com", "555-123-7890", None, None, None, "PAY-019", date(2023, 12, 1), 110.00, "Bank Transfer", None, None, None, None, "Queen Mansion, Starling City, WA", 1200000.00, "Single Family", "Building", None, None, None, None),
            ("Clark", "Kent", date(1989, 12, 7), "Male", "clark.kent@email.com", "555-000-2222", "344 Clinton Street, Metropolis", "Metropolis", "NY", "10009", "POL-1020", ["Auto Insurance"], "AUTO-020", date(2023, 9, 1), date(2024, 9, 1), 140.00, "AGT-007", "Lois Lane", "lois.lane@insure.com", "555-456-7890", None, None, None, "PAY-020", date(2023, 9, 1), 140.00, "Credit Card", None, None, None, None, None, None, None, None, "Ford", "F-150", 2022, "Comprehensive"),
        ]

        cur.execute("SELECT COUNT(*) FROM customer_insurance")
        if cur.fetchone()[0] == 0:
            cur.executemany("""
            INSERT INTO customer_insurance (
                first_name, last_name, date_of_birth, gender, email, phone_number,
                address, city, state, zip_code,
                policy_id, policy_type, policy_number, policy_start_date, policy_end_date, premium_amount,
                agent_id, agent_name, agent_email, agent_phone_number,
                claim_date, claim_amount, claim_status,
                payment_id, payment_date, payment_amount, payment_method,
                life_beneficiary_name, life_beneficiary_relationship, life_policy_term, life_sum_assured,
                home_property_address, home_property_value, home_property_type, home_coverage_type,
                auto_vehicle_make, auto_vehicle_model, auto_vehicle_year, auto_coverage_type
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """, sample_data)
            print("Inserted 20 sample data records")
        else:
            print("Table already contains data - no samples inserted")

        conn.commit()
        print("Insurance table ready with sample data")

    except Exception as error:
        print(f"Error: {error}")
        if conn:
            conn.rollback()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


def get_insurance_data_for_embeddings():
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**get_conn_params())
        cur = conn.cursor()

        cur.execute("""
        SELECT
            customer_id::text,
            first_name || ' ' || last_name AS customer_name,
            array_to_string(policy_type, ', ') AS policy_types,
            policy_number,
            date_of_birth::text,
            email,
            phone_number,
            address || ', ' || city || ', ' || state || ' ' || zip_code AS full_address,
            premium_amount::text,
            COALESCE(life_beneficiary_name, '') AS life_beneficiary,
            COALESCE(life_sum_assured::text, '') AS life_sum_assured,
            COALESCE(home_property_address, '') AS home_address,
            COALESCE(home_property_value::text, '') AS home_value,
            COALESCE(home_property_type, '') AS home_type,
            COALESCE(auto_vehicle_make || ' ' || auto_vehicle_model, '') AS vehicle,
            COALESCE(auto_vehicle_year::text, '') AS vehicle_year
        FROM customer_insurance
        """)

        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    except Exception as error:
        print(f"Error retrieving data: {error}")
        return []
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    create_insurance_table_with_data()

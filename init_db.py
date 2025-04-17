from datetime import datetime
from database import db, execute_with_retry, log_database_operation
import logging
from werkzeug.security import generate_password_hash

logger = logging.getLogger(__name__)

def initialize_database():
    try:
        logger.info("Starting database initialization...")
        
        # Clear existing collections
        logger.info("Clearing existing collections...")
        execute_with_retry(lambda: db.users.delete_many({}))
        execute_with_retry(lambda: db.microscopes.delete_many({}))
        execute_with_retry(lambda: db.bookings.delete_many({}))
        log_database_operation('clear_collections', True)

        # Insert sample microscopes
        logger.info("Inserting sample microscopes...")
        microscopes = [
        {
            'name': 'Confocal Microscope',
            'type': 'Laser Scanning',
            'description': 'High-resolution imaging with optical sectioning capability',
            'location': 'Room 101',
            'status': 'available',
            'image_url': 'images/microscope_1.jpg'
        },
        {
            'name': 'Electron Microscope',
            'type': 'Transmission',
            'description': 'Ultra-high resolution imaging for nanoscale structures',
            'location': 'Room 102',
            'status': 'available',
            'image_url': 'images/microscope_2.jpg'
        },
        {
            'name': 'Fluorescence Microscope',
            'type': 'Widefield',
            'description': 'Ideal for live cell imaging and fluorescence studies',
            'location': 'Room 103',
            'status': 'available',
            'image_url': 'images/microscope_3.jpg'
        }
    ]

        result = execute_with_retry(lambda: db.microscopes.insert_many(microscopes))
        log_database_operation('insert_microscopes', True)
        logger.info(f"Inserted {len(result.inserted_ids)} microscopes")

        # Insert sample user with properly hashed password
        logger.info("Inserting sample user...")
        user_result = execute_with_retry(lambda: db.users.insert_one({
            'email': 'admin@example.com',
            'name': 'Admin User',
            'password': generate_password_hash('admin123'),  # Properly hash the password
            'otp_verified': True  # Set to True so admin can bypass OTP verification
        }))
        log_database_operation('insert_user', True)
        logger.info(f"Inserted user with ID: {user_result.inserted_id}")

        logger.info("Database initialization completed successfully!")
        return True
    except Exception as e:
        log_database_operation('initialize_database', False, str(e))
        logger.error(f"Error during database initialization: {e}")
        return False

if __name__ == '__main__':
    try:
        success = initialize_database()
        if success:
            print("Database initialized successfully!")
        else:
            print("Database initialization failed. Check the logs for details.")
    except Exception as e:
        print(f"Fatal error during initialization: {e}")
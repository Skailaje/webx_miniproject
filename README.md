# Microscope Booking System

A web application for booking microscope slots in a research facility. Built with Flask, MongoDB, and modern web technologies.

## Features

- User authentication (login/register)
- Real-time booking system
- Dashboard for managing bookings
- Responsive design
- Real-time updates using Socket.IO
- Secure session management

## Prerequisites

- Python 3.8+
- MongoDB
- pip (Python package manager)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd microscope-booking-system
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory with the following variables:
```
SECRET_KEY=your-secret-key
MONGODB_URI=mongodb://localhost:27017/
```

5. Initialize the database with sample data:
```bash
python init_db.py
```

## Running the Application

1. Start MongoDB:
```bash
mongod
```

2. Run the Flask application:
```bash
python app.py
```

3. Open your browser and navigate to:
```
http://localhost:5000
```

## Project Structure

```
microscope-booking-system/
├── app.py                 # Main application file
├── requirements.txt       # Python dependencies
├── static/                # Static files
│   ├── css/
│   │   └── style.css     # Custom styles
│   └── js/
│       └── main.js       # Client-side JavaScript
├── templates/             # HTML templates
│   ├── base.html         # Base template
│   ├── home.html         # Home page
│   ├── login.html        # Login page
│   ├── register.html     # Registration page
│   ├── dashboard.html    # User dashboard
│   ├── book.html         # Booking page
│   └── thank_you.html    # Confirmation page
└── README.md             # Project documentation
```

## Security Considerations

- Passwords are stored securely (implement proper hashing in production)
- CSRF protection is enabled
- Session management is handled securely
- Input validation on all forms

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
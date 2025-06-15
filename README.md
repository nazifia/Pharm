# PharmApp - Pharmacy Management System

A comprehensive pharmacy management system built with Django that supports both retail and wholesale operations.

## Features

### Inventory Management
- Track retail and wholesale inventory separately
- Real-time stock updates
- Stock level alerts
- Stock transfer between retail and wholesale
- Stock adjustment capabilities
- Batch and expiry date tracking

### Sales Management
- Retail sales processing
- Wholesale order management
- Receipt generation and printing
- Sales history tracking
- Customer management

### Procurement
- Supplier management
- Purchase order creation
- Stock receiving
- Procurement history
- Automated stock updates upon receiving

### Financial Management
- Expense tracking
- Sales reports
- Procurement reports
- Stock value reports
- Profit/Loss calculations

### User Management
- Role-based access control
- User authentication
- Activity logging
- Secure password management

### Offline Capabilities #Comming Soon
<!-- - Progressive Web App (PWA) support
- Offline data synchronization
- Offline receipt generation
- Automatic sync when online -->

## Technical Stack

- **Backend**: Django
- **Frontend**: HTML, CSS, JavaScript
- **Database**: SQLite (default)
- **Additional Libraries**:
  - HTMX for dynamic interactions
  - Font Awesome for icons
  - WhiteNoise for static file serving
  - Django CORS headers
  - HTML2PDF.js for PDF generation

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd pharmapp
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up the database:
```bash
python manage.py migrate
```

5. Create a superuser:
```bash
python manage.py createsuperuser
```

6. Collect static files:
```bash
python manage.py collectstatic
```

7. Run the development server:
```bash
python manage.py runserver
```

## Project Structure

```
pharmapp/
├── store/              # Retail operations
├── wholesale/          # Wholesale operations
├── userauth/           # User authentication
├── customer/           # Customer management
├── supplier/           # Supplier management
├── static/             # Static files
├── templates/          # HTML templates
├── media/             # User-uploaded files
└── pharmapp/          # Project settings
```

## Usage

1. Access the admin interface at `/admin`
2. Log in with superuser credentials
3. Start managing inventory, sales, and procurement
4. Access retail operations through the store module
5. Access wholesale operations through the wholesale module

## Offline Support

The application supports offline operations through:
- Service Worker implementation
- IndexedDB for local storage
- Background sync when online
- PWA installation capability

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the repository or contact the development team.

## Authors

- [Your Name/Team]

## Acknowledgments

- Font Awesome for icons
- Django community
- All contributors to the project
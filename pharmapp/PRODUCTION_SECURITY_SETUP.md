# Production Security Setup Guide

This guide explains how to securely configure your Django application for production deployment.

## 🔐 Environment Variables Setup

### 1. Install Dependencies
```bash
pip install python-decouple==3.8
```

### 2. Create Environment File
```bash
# Copy the example file
cp .env.example .env

# Edit the .env file with your production values
```

### 3. Generate Secure SECRET_KEY
```bash
python generate_secret_key.py
```

Add the generated key to your `.env` file:
```
SECRET_KEY=your-generated-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

### 4. Required Environment Variables

| Variable | Description | Production Value |
|----------|-------------|------------------|
| `SECRET_KEY` | Django secret key | Generate with `python generate_secret_key.py` |
| `DEBUG` | Debug mode | `False` |
| `ALLOWED_HOSTS` | Allowed domains | Comma-separated list of your domains |

### 5. Optional Environment Variables

```bash
# Database Configuration
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_HOST=localhost
DB_PORT=5432

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

## 🛡️ Security Features Enabled in Production

When `DEBUG=False`, the following security settings are automatically enabled:

- **HTTPS Redirect**: All traffic redirected to HTTPS
- **Secure Cookies**: Session and CSRF cookies only sent over HTTPS
- **XSS Protection**: Browser XSS filtering enabled
- **Content Type Protection**: MIME type sniffing protection
- **HSTS**: HTTP Strict Transport Security (1 year)
- **Frame Protection**: Clickjacking protection with X-Frame-Options

## 🚀 Deployment Checklist

- [ ] Set `DEBUG=False` in environment
- [ ] Generate and set `SECRET_KEY`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Ensure HTTPS is configured
- [ ] Set up production database
- [ ] Configure backup strategy
- [ ] Set up monitoring and logging
- [ ] Test all functionality in staging

## 🔄 Testing Production Settings

To test your production configuration locally:

```bash
# Windows PowerShell
$env:DEBUG="False"
$env:SECRET_KEY="your-test-secret-key"
python manage.py check --deploy

# Linux/Mac
export DEBUG=False
export SECRET_KEY="your-test-secret-key"
python manage.py check --deploy
```

## ⚠️ Important Notes

1. **Never commit `.env` files** to version control (already in .gitignore)
2. **Use different SECRET_KEY** for each environment
3. **Always use HTTPS** in production
4. **Regularly update dependencies** for security patches
5. **Monitor Django security releases**

## 🔍 Security Validation

Run the deployment check to validate your security setup:

```bash
python manage.py check --deploy
```

This will warn you about any security misconfigurations that need to be addressed.

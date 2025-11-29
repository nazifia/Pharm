# PythonAnywhere Deployment Guide with Offline Support

## Overview

This guide covers deploying PharmApp to PythonAnywhere while maintaining full offline-first functionality. The offline features work **client-side** in users' browsers, while PythonAnywhere hosts the Django backend.

## How Offline Works with PythonAnywhere

```
┌──────────────────────────────────────────────────────────┐
│ Scenario 1: User Visits Site (Online)                    │
├──────────────────────────────────────────────────────────┤
│ 1. User visits https://yourusername.pythonanywhere.com   │
│ 2. Service Worker installs in user's browser             │
│ 3. App shell and data cached to IndexedDB                │
│ 4. User can now work offline                             │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│ Scenario 2: User Works Offline                           │
├──────────────────────────────────────────────────────────┤
│ 1. User loses internet connection                        │
│ 2. App loads from cache (service worker)                 │
│ 3. Data served from IndexedDB                            │
│ 4. Changes queued in pending actions                     │
│ 5. User sees "Offline" indicator                         │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│ Scenario 3: User Reconnects                              │
├──────────────────────────────────────────────────────────┤
│ 1. Internet connection restored                          │
│ 2. Service worker detects online status                  │
│ 3. Background sync triggers                              │
│ 4. Pending actions sent to PythonAnywhere server         │
│ 5. Server processes and saves to database                │
│ 6. User sees "Synced" notification                       │
└──────────────────────────────────────────────────────────┘
```

## Prerequisites

1. PythonAnywhere account (Free or Paid tier)
2. Your PharmApp code ready
3. GitHub repository (recommended for easy deployment)

## Step-by-Step Deployment

### Step 1: Create PythonAnywhere Account

1. Go to https://www.pythonanywhere.com
2. Sign up for an account (Free tier works, but Paid tier recommended for MySQL)
3. Verify your email

### Step 2: Upload Your Code

**Option A: Using Git (Recommended)**

1. Open a Bash console in PythonAnywhere
2. Clone your repository:
```bash
git clone https://github.com/yourusername/pharmapp.git
cd pharmapp
```

**Option B: Upload Files**

1. Use the "Files" tab in PythonAnywhere
2. Upload your project as a ZIP file
3. Unzip in the console:
```bash
cd ~
unzip pharmapp.zip
cd pharmapp
```

### Step 3: Set Up Virtual Environment

```bash
# Create virtual environment
mkvirtualenv pharmapp --python=python3.10

# Activate it (done automatically after creation)
# Install dependencies
pip install -r requirements.txt

# If you don't have requirements.txt, install manually:
pip install django python-decouple django-cors-headers whitenoise
```

### Step 4: Create .env File

```bash
cd ~/pharmapp/pharmapp
nano .env
```

Add the following:
```env
SECRET_KEY=your-super-secret-key-here-change-this
DEBUG=False
ALLOWED_HOSTS=yourusername.pythonanywhere.com,localhost,127.0.0.1

# For MySQL (Paid accounts)
# DB_NAME=yourusername$pharmapp_db
# DB_USER=yourusername
# DB_PASSWORD=your_mysql_password
# DB_HOST=yourusername.mysql.pythonanywhere-services.com
# DB_PORT=3306
```

**Generate a secure secret key:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Step 5: Update Settings for PythonAnywhere

Edit `pharmapp/settings.py`:

```python
# Add at the top
import os
from pathlib import Path

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

# Update ALLOWED_HOSTS
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=Csv())

# Add PythonAnywhere to CORS origins
CORS_ALLOWED_ORIGINS = [
    "https://yourusername.pythonanywhere.com",
    "capacitor://localhost",
    "http://localhost",
]

# Static files configuration
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

# For MySQL on PythonAnywhere (Paid tier)
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': config('DB_NAME'),
#         'USER': config('DB_USER'),
#         'PASSWORD': config('DB_PASSWORD'),
#         'HOST': config('DB_HOST'),
#         'PORT': config('DB_PORT', cast=int),
#         'OPTIONS': {
#             'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
#         }
#     }
# }
```

### Step 6: Database Setup

**For SQLite (Free tier):**
```bash
cd ~/pharmapp
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

**For MySQL (Paid tier):**
1. Go to "Databases" tab in PythonAnywhere
2. Create a new MySQL database
3. Note the connection details
4. Update .env with MySQL credentials
5. Uncomment MySQL DATABASES configuration in settings.py
6. Run migrations:
```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

### Step 7: Configure Web App

1. Go to "Web" tab in PythonAnywhere dashboard
2. Click "Add a new web app"
3. Choose "Manual configuration"
4. Select Python 3.10 (or your version)
5. Click through to create the app

### Step 8: Configure WSGI File

1. In the "Web" tab, click on WSGI configuration file
2. Replace the contents with:

```python
import os
import sys

# Add your project directory to the sys.path
path = '/home/yourusername/pharmapp'
if path not in sys.path:
    sys.path.insert(0, path)

# Set environment variables
os.environ['DJANGO_SETTINGS_MODULE'] = 'pharmapp.settings'

# Activate virtual environment
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

**Replace `yourusername` with your actual PythonAnywhere username!**

### Step 9: Configure Virtual Environment

In the "Web" tab:
1. Scroll to "Virtualenv" section
2. Enter: `/home/yourusername/.virtualenvs/pharmapp`
3. Click the checkmark

### Step 10: Configure Static Files

In the "Web" tab, under "Static files":

| URL          | Directory                                    |
|--------------|----------------------------------------------|
| /static/     | /home/yourusername/pharmapp/staticfiles      |
| /media/      | /home/yourusername/pharmapp/media            |

### Step 11: Enable HTTPS (Required for Service Workers!)

**IMPORTANT:** Service Workers ONLY work over HTTPS (or localhost).

PythonAnywhere provides HTTPS by default at:
- `https://yourusername.pythonanywhere.com` ✅

For custom domains (Paid accounts):
1. Go to "Web" tab
2. Add your custom domain
3. Enable HTTPS (Let's Encrypt certificate)

### Step 12: Reload Web App

1. Go to "Web" tab
2. Click the big green "Reload" button
3. Wait for reload to complete

### Step 13: Test Deployment

1. Visit `https://yourusername.pythonanywhere.com`
2. Open browser DevTools (F12)
3. Check Console for service worker registration
4. Verify no errors

### Step 14: Test Offline Functionality

1. **While online:**
   - Log in to the app
   - Navigate around to cache pages
   - Add some data (item, customer, etc.)

2. **Go offline:**
   - Open DevTools (F12) → Network tab
   - Select "Offline" from throttling dropdown
   - Refresh the page - it should still load!
   - Try adding data - it should queue

3. **Go back online:**
   - Change "Offline" to "No throttling"
   - Watch the sync indicator
   - Verify data synced to server

## Offline Functionality Checklist

After deployment, verify these work:

- [ ] Service Worker registers successfully
- [ ] App loads while offline
- [ ] Connection status indicator shows correct state
- [ ] Data caches to IndexedDB
- [ ] Actions queue when offline
- [ ] Automatic sync when reconnected
- [ ] Manual sync button works
- [ ] Pending actions counter shows
- [ ] Notifications display correctly
- [ ] No console errors

## Important PythonAnywhere Considerations

### 1. Service Worker Scope

Update `sw.js` cache names for your domain:
```javascript
const CACHE_NAME = 'pharmapp-pythonanywhere-v1';
```

### 2. HTTPS is Mandatory

Service Workers require HTTPS. PythonAnywhere provides this automatically.

### 3. Static Files

Always run `collectstatic` after code changes:
```bash
cd ~/pharmapp
python manage.py collectstatic --noinput
```

Then reload the web app.

### 4. Database Limitations

**Free Tier:**
- SQLite only
- Limited storage
- Not recommended for production

**Paid Tier:**
- MySQL available
- Better performance
- Recommended for production

### 5. Session Timeout

PythonAnywhere may timeout inactive sessions. Configure:
```python
# In settings.py
SESSION_COOKIE_AGE = 1200  # 20 minutes
SESSION_SAVE_EVERY_REQUEST = True
```

### 6. CORS Configuration

Ensure CORS is properly configured for offline sync:
```python
CORS_ALLOWED_ORIGINS = [
    "https://yourusername.pythonanywhere.com",
]

CORS_ALLOW_METHODS = [
    'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'
]
```

## Updating Your App

### Quick Update Process

```bash
# SSH into PythonAnywhere or use console

# Pull latest code
cd ~/pharmapp
git pull origin main

# Activate virtual environment
workon pharmapp

# Install any new dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Reload web app (via dashboard or):
touch /var/www/yourusername_pythonanywhere_com_wsgi.py
```

## Troubleshooting

### Service Worker Not Registering

**Symptoms:** Console shows service worker errors

**Solutions:**
1. Ensure you're using HTTPS
2. Check service worker path is correct: `/static/js/sw.js`
3. Verify static files are collected
4. Check browser DevTools → Application → Service Workers

### Offline Mode Not Working

**Symptoms:** App doesn't load when offline

**Solutions:**
1. Visit site while online first
2. Navigate to pages you want cached
3. Wait for service worker to install
4. Check cache in DevTools → Application → Cache Storage

### Sync Not Working

**Symptoms:** Changes don't sync when back online

**Solutions:**
1. Check API endpoints are accessible
2. Verify CSRF token configuration
3. Check browser console for errors
4. Test API endpoints directly: `https://yourusername.pythonanywhere.com/api/health/`

### Static Files Not Loading

**Symptoms:** CSS/JS missing, 404 errors

**Solutions:**
```bash
# Collect static files
python manage.py collectstatic --noinput

# Verify static files mapping in Web tab
# URL: /static/
# Directory: /home/yourusername/pharmapp/staticfiles
```

## Performance Optimization for PythonAnywhere

### 1. Enable Compression

Already configured via WhiteNoise in settings.py:
```python
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

### 2. Database Connection Pooling

```python
DATABASES = {
    'default': {
        # ... other settings ...
        'CONN_MAX_AGE': 60,  # Reuse connections
    }
}
```

### 3. Cache Configuration

Use file-based caching on PythonAnywhere:
```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/home/yourusername/pharmapp/cache',
    }
}
```

### 4. Optimize Service Worker

Update cache expiration in `sw.js`:
```javascript
// Cache for longer on production
const CACHE_MAX_AGE = 86400; // 24 hours
```

## Custom Domain Setup (Paid Accounts)

1. Go to "Web" tab
2. Add custom domain (e.g., `pharmapp.com`)
3. Update DNS records:
   ```
   CNAME: www -> yourusername.pythonanywhere.com
   A: @ -> (IP provided by PythonAnywhere)
   ```
4. Enable HTTPS (Let's Encrypt)
5. Update settings.py:
   ```python
   ALLOWED_HOSTS = ['pharmapp.com', 'www.pharmapp.com', 'yourusername.pythonanywhere.com']
   ```

## Progressive Web App (PWA) Setup

Your app is already PWA-ready! Users can install it:

### On Desktop (Chrome/Edge):
1. Visit your site
2. Click install icon in address bar
3. App installs as standalone application

### On Mobile (iOS/Android):
1. Visit your site in Safari/Chrome
2. Tap "Add to Home Screen"
3. App installs like native app

### Manifest Configuration

Verify `static/manifest.json` has correct URLs:
```json
{
    "name": "PharmApp",
    "short_name": "PharmApp",
    "start_url": "https://yourusername.pythonanywhere.com/",
    "scope": "https://yourusername.pythonanywhere.com/",
    "display": "standalone",
    "background_color": "#ffffff",
    "theme_color": "#4285f4",
    "icons": [
        {
            "src": "/static/img/icon-192x192.png",
            "sizes": "192x192",
            "type": "image/png"
        },
        {
            "src": "/static/img/icon-512x512.png",
            "sizes": "512x512",
            "type": "image/png"
        }
    ]
}
```

## Monitoring and Logs

### View Error Logs

1. Go to "Web" tab
2. Click "Error log"
3. Check for Django errors

### View Access Logs

1. Go to "Web" tab
2. Click "Server log"
3. Monitor traffic

### Django Logs

Add to settings.py:
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': '/home/yourusername/pharmapp/django_errors.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}
```

## Security Checklist

- [ ] `DEBUG = False` in production
- [ ] Strong `SECRET_KEY`
- [ ] HTTPS enabled
- [ ] `ALLOWED_HOSTS` configured
- [ ] CSRF protection enabled
- [ ] XSS protection enabled
- [ ] Database credentials in .env
- [ ] .env file not in git
- [ ] Admin URL changed (optional)
- [ ] Regular backups enabled

## Backup Strategy

### Database Backup (SQLite)

```bash
# Download from Files tab
# Or use console:
cd ~/pharmapp
cp db.sqlite3 db_backup_$(date +%Y%m%d).sqlite3
```

### Database Backup (MySQL)

```bash
mysqldump -u yourusername -h yourusername.mysql.pythonanywhere-services.com 'yourusername$dbname' > backup.sql
```

### Automated Backups

Create scheduled task in PythonAnywhere:
```bash
#!/bin/bash
cd ~/pharmapp
python manage.py dumpdata > backup_$(date +%Y%m%d_%H%M%S).json
```

## Cost Considerations

### Free Tier:
- ✅ Good for testing
- ❌ SQLite only
- ❌ Limited CPU
- ❌ Daily timeout

### Paid Tier ($5/month):
- ✅ MySQL database
- ✅ More CPU seconds
- ✅ Always-on
- ✅ Custom domains
- ✅ SSH access
- ✅ Better for production

## Support and Resources

- **PythonAnywhere Help:** https://help.pythonanywhere.com/
- **Django Deployment:** https://help.pythonanywhere.com/pages/DeployExistingDjangoProject/
- **Service Workers:** https://developers.google.com/web/fundamentals/primers/service-workers
- **PWA Guide:** https://web.dev/progressive-web-apps/

## Conclusion

Your PharmApp is now:
- ✅ Hosted on PythonAnywhere (always accessible)
- ✅ Works offline on users' devices
- ✅ Automatically syncs when reconnected
- ✅ Installable as Progressive Web App
- ✅ Secure with HTTPS
- ✅ Production-ready

Users can access the app from **any device with a browser**, and after the first visit, they can continue working even without internet connection. All changes sync automatically when they reconnect!

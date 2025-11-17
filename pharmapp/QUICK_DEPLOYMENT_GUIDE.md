# Quick Deployment Guide - PythonAnywhere

## TL;DR - 5 Minute Deploy

```bash
# 1. In PythonAnywhere Bash console
git clone https://github.com/yourusername/pharmapp.git
cd pharmapp

# 2. Create virtual environment
mkvirtualenv pharmapp --python=python3.10
pip install -r requirements.txt

# 3. Create .env file
nano pharmapp/.env
# Add: SECRET_KEY, DEBUG=False, ALLOWED_HOSTS

# 4. Setup database
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput

# 5. Configure Web app in dashboard
# - Set WSGI file path
# - Set virtualenv path
# - Set static files mapping
# - Reload

# Done! Visit https://yourusername.pythonanywhere.com
```

## .env Template

```env
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourusername.pythonanywhere.com,localhost,127.0.0.1
```

Generate secret key:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## WSGI Configuration

```python
import os
import sys

path = '/home/yourusername/pharmapp'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'pharmapp.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

## Static Files Mapping

| URL      | Directory                                |
|----------|------------------------------------------|
| /static/ | /home/yourusername/pharmapp/staticfiles  |
| /media/  | /home/yourusername/pharmapp/media        |

## Virtualenv Path

```
/home/yourusername/.virtualenvs/pharmapp
```

## Update Deployed App

```bash
cd ~/pharmapp
git pull
workon pharmapp
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
# Reload web app in dashboard
```

## Test Offline Functionality

1. Visit your site: `https://yourusername.pythonanywhere.com`
2. Log in and navigate around
3. Open DevTools (F12) → Network → Select "Offline"
4. Refresh - app should still work!
5. Add data - should queue for sync
6. Go online - should auto-sync

## Troubleshooting Quick Fixes

**Service worker not loading:**
```bash
python manage.py collectstatic --noinput --clear
# Reload web app
```

**Static files 404:**
- Check static files mapping in Web tab
- Verify path: `/home/yourusername/pharmapp/staticfiles`

**App not loading:**
- Check error log in Web tab
- Verify .env file exists
- Check ALLOWED_HOSTS includes your domain

**Database errors:**
```bash
python manage.py migrate
# Reload web app
```

## Important Notes

✅ **HTTPS is automatic** - PythonAnywhere provides it
✅ **Offline works immediately** - No extra config needed
✅ **Service worker** - Works over HTTPS only
✅ **First visit must be online** - To cache the app
✅ **After that** - Users can work offline

## Support

- Full guide: See `PYTHONANYWHERE_DEPLOYMENT.md`
- Offline guide: See `OFFLINE_FUNCTIONALITY_GUIDE.md`
- PythonAnywhere help: https://help.pythonanywhere.com/

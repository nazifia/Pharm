# Database Switching Guide

This guide provides instructions for switching between SQLite and MySQL databases in PharmApp.

## Current Configuration

The application is configured to support both SQLite (default) and MySQL databases with easy switching options in `pharmapp/settings.py`.

## Option 1: SQLite (Default Configuration)

**Use Case:** Development, testing, small deployments

**Advantages:**
- No external database server required
- Easy setup and maintenance
- File-based, portable
- Zero configuration

**Current Status:** ✅ Active (default)

## Option 2: MySQL

**Use Case:** Production, large deployments, multiple users, high concurrency

**Advantages:**
- Better performance for concurrent users
- More robust and scalable
- Advanced features (stored procedures, triggers)
- Better for large datasets

## Switching Instructions

### From SQLite to MySQL

1. **Prerequisites:**
   ```bash
   # MySQL server should be installed and running
   # mysqlclient is already in requirements.txt
   pip install mysqlclient
   ```

2. **Set up MySQL Database:**
   ```bash
   python mysql_setup.py
   ```
   This will create:
   - Database: `pharmapp_db`
   - User: `pharmapp_user`
   - Password: `pharmapp_password`

3. **Update Settings:**
   - Open `pharmapp/settings.py`
   - Comment out the SQLite DATABASES configuration (lines ~233-251)
   - Uncomment the MySQL DATABASES configuration (lines ~254-278)
   - Replace `your_password_here` with `pharmapp_password`

4. **Migrate Data (Optional):**
   ```bash
   python migrate_sqlite_to_mysql.py
   ```
   This will transfer all existing data from SQLite to MySQL.

5. **Apply Migrations:**
   ```bash
   python manage.py migrate
   ```

6. **Test the Application:**
   ```bash
   python manage.py runserver
   ```

### From MySQL to SQLite

1. **Backup MySQL Data (if needed):**
   ```bash
   python manage.py dumpdata --natural-foreign --natural-primary -e --indent=2 > mysql_backup.json
   ```

2. **Update Settings:**
   - Open `pharmapp/settings.py`
   - Comment out the MySQL DATABASES configuration
   - Uncomment the SQLite DATABASES configuration

3. **Apply Migrations:**
   ```bash
   python manage.py migrate
   ```

4. **Restore Data (if needed):**
   ```bash
   python manage.py loaddata mysql_backup.json
   ```

## Configuration Details

### SQLite Configuration
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {
            'timeout': 20,
            'check_same_thread': False,
        },
        'CONN_MAX_AGE': 60,
    },
    'offline': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'offline.sqlite3',
        'OPTIONS': {
            'timeout': 20,
            'check_same_thread': False,
        },
        'CONN_MAX_AGE': 60,
    }
}
```

### MySQL Configuration
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'pharmapp_db',
        'USER': 'pharmapp_user',
        'PASSWORD': 'pharmapp_password',  # Change this
        'HOST': 'localhost',
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
        'CONN_MAX_AGE': 60,
    },
    'offline': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'offline.sqlite3',
        'OPTIONS': {
            'timeout': 20,
            'check_same_thread': False,
        },
        'CONN_MAX_AGE': 60,
    }
}
```

## Quick Switch Commands

### Check Current Database
```python
# In Django shell
python manage.py shell
>>> from django.db import connection
>>> connection.vendor
# Returns 'sqlite' for SQLite, 'mysql' for MySQL
```

### Test Database Connection
```bash
# SQLite
python -c "import sqlite3; print('SQLite connection OK')"

# MySQL
python -c "import MySQLdb; MySQLdb.connect(user='pharmapp_user', passwd='password', db='pharmapp_db'); print('MySQL connection OK')"
```

## Important Notes

1. **Offline Database:** The offline database always remains SQLite regardless of the primary database choice.

2. **Migration:** Always create backups before switching databases.

3. **Performance:** MySQL is recommended for production environments with multiple users.

4. **Compatibility:** All features work with both databases; MySQL provides better performance for concurrent operations.

5. **Data Integrity:** Test thoroughly after switching to ensure all data is preserved and functionality works correctly.

## Troubleshooting

### MySQL Connection Issues
```bash
# Check MySQL service
sudo systemctl status mysql  # Linux
brew services list | grep mysql  # macOS

# Check user permissions
mysql -u root -p -e "SELECT User, Host FROM mysql.user WHERE User='pharmapp_user';"
```

### Migration Issues
```bash
# Reset migrations if needed
python manage.py migrate appname zero
python manage.py migrate appname
```

### Character Encoding Issues
Ensure MySQL is configured with UTF-8 support:
```sql
CREATE DATABASE pharmapp_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

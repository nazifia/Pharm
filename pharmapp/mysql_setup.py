#!/usr/bin/env python
"""
MySQL Database Setup Script for PharmApp

This script helps set up MySQL database for the PharmApp project.
Run this script to create the database and user needed for MySQL configuration.

Prerequisites:
- MySQL server installed and running
- MySQL root access

Usage:
    python mysql_setup.py

Then update settings.py to use MySQL configuration (Option 2)
"""

import os
import sys
import getpass
import subprocess

def run_mysql_command(command, password=None):
    """Run MySQL command with optional password"""
    try:
        if password:
            cmd = f"mysql -u root -p{password} -e \"{command}\""
        else:
            cmd = f"mysql -u root -e \"{command}\""
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    except Exception as e:
        return False, str(e)

def setup_mysql_database():
    """Set up MySQL database and user for PharmApp"""
    print("=== MySQL Database Setup for PharmApp ===\n")
    
    # Get MySQL root password
    print("Please enter MySQL root password (leave blank if no password):")
    try:
        root_password = getpass.getpass()
    except:
        root_password = ""
    
    # Test connection
    print("\nTesting MySQL connection...")
    success, output = run_mysql_command("SHOW DATABASES;", root_password)
    if not success:
        print(f"❌ Failed to connect to MySQL: {output}")
        return False
    
    print("✅ MySQL connection successful!")
    
    # Database configuration
    db_name = "pharmapp_db"
    db_user = "pharmapp_user"
    db_password = "pharmapp_password"
    
    print(f"\nCreating database '{db_name}'...")
    success, output = run_mysql_command(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;", root_password)
    if not success:
        print(f"❌ Failed to create database: {output}")
        return False
    print("✅ Database created successfully!")
    
    print(f"\nCreating user '{db_user}'...")
    success, output = run_mysql_command(f"CREATE USER IF NOT EXISTS '{db_user}'@'localhost' IDENTIFIED BY '{db_password}';", root_password)
    if not success and "already exists" not in output:
        print(f"❌ Failed to create user: {output}")
        return False
    print("✅ User created successfully!")
    
    print(f"\nGranting privileges to user '{db_user}'...")
    success, output = run_mysql_command(f"GRANT ALL PRIVILEGES ON {db_name}.* TO '{db_user}'@'localhost';", root_password)
    if not success:
        print(f"❌ Failed to grant privileges: {output}")
        return False
    
    success, output = run_mysql_command("FLUSH PRIVILEGES;", root_password)
    if not success:
        print(f"❌ Failed to flush privileges: {output}")
        return False
    print("✅ Privileges granted successfully!")
    
    print("\n=== Setup Complete! ===")
    print(f"\nDatabase Details:")
    print(f"  Database Name: {db_name}")
    print(f"  Username: {db_user}")
    print(f"  Password: {db_password}")
    print(f"  Host: localhost")
    print(f"  Port: 3306")
    
    print(f"\nNext Steps:")
    print(f"1. Open pharmapp/settings.py")
    print(f"2. Comment out the SQLite DATABASES configuration")
    print(f"3. Uncomment the MySQL DATABASES configuration")
    print(f"4. Replace 'your_password_here' with '{db_password}'")
    print(f"5. Run: python manage.py migrate")
    print(f"6. Run: python manage.py createsuperuser (if needed)")
    print(f"7. Run: python manage.py runserver")
    
    return True

def create_data_migration_script():
    """Create a script to migrate data from SQLite to MySQL"""
    script_content = '''#!/usr/bin/env python
"""
Data Migration Script: SQLite to MySQL

This script migrates data from SQLite to MySQL.
Run after setting up MySQL and updating settings.py.

Usage:
    1. Make sure MySQL is configured in settings.py
    2. Run: python migrate_sqlite_to_mysql.py
"""

import os
import sys
import django
from django.core.management import execute_from_command_line
from django.db import connection
from django.core.management.commands.dumpdata import Command as DumpDataCommand
from django.core.management.commands.loaddata import Command as LoadDataCommand

def migrate_data():
    """Migrate data from SQLite to MySQL"""
    print("=== Data Migration: SQLite to MySQL ===")
    
    # Backup current SQLite data
    print("\\n1. Creating backup of SQLite data...")
    try:
        execute_from_command_line(['manage.py', 'dumpdata', '--natural-foreign', '--natural-primary', '-e', '--indent=2', 'sqlite_data.json'])
        print("✅ SQLite data backed up to sqlite_data.json")
    except Exception as e:
        print(f"❌ Failed to backup SQLite data: {e}")
        return False
    
    # Switch to MySQL and migrate schema
    print("\\n2. Applying migrations to MySQL...")
    try:
        execute_from_command_line(['manage.py', 'migrate'])
        print("✅ MySQL schema migrated successfully")
    except Exception as e:
        print(f"❌ Failed to migrate MySQL schema: {e}")
        return False
    
    # Load data into MySQL
    print("\\n3. Loading data into MySQL...")
    try:
        execute_from_command_line(['manage.py', 'loaddata', 'sqlite_data.json'])
        print("✅ Data loaded into MySQL successfully")
    except Exception as e:
        print(f"❌ Failed to load data into MySQL: {e}")
        return False
    
    # Clean up backup file
    try:
        os.remove('sqlite_data.json')
        print("✅ Backup file cleaned up")
    except:
        pass
    
    print("\\n=== Migration Complete! ===")
    print("Your data has been successfully migrated from SQLite to MySQL.")
    return True

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
    django.setup()
    migrate_data()
'''
    
    with open('migrate_sqlite_to_mysql.py', 'w') as f:
        f.write(script_content)
    
    print("✅ Created migration script: migrate_sqlite_to_mysql.py")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--create-migration-script':
        create_data_migration_script()
    else:
        setup_mysql_database()
        
        print(f"\nWould you like to create a data migration script? (y/n): ", end="")
        response = input().lower().strip()
        if response in ['y', 'yes']:
            create_data_migration_script()
            print("\nRun 'python migrate_sqlite_to_mysql.py' after configuring MySQL in settings.py")

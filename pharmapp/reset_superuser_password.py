#!/usr/bin/env python
"""
Script to reset superuser password
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from userauth.models import User

def reset_superuser_password():
    try:
        # Find the superuser
        superuser = User.objects.filter(is_superuser=True).first()
        
        if not superuser:
            print("❌ No superuser found in the system.")
            return False
            
        print(f"✅ Found superuser: {superuser.username}")
        print(f"📱 Mobile: {superuser.mobile}")
        print(f"🔄 Is active: {superuser.is_active}")
        
        # Set a new password
        new_password = "nazz2020"
        superuser.set_password(new_password)
        superuser.save()
        
        print(f"✅ Password reset successfully!")
        print(f"🔑 New password: {new_password}")
        print(f"📱 Login with mobile: {superuser.mobile}")
        print(f"🔑 Password: {new_password}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error resetting password: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔄 Resetting superuser password...")
    success = reset_superuser_password()
    
    if success:
        print("\n🎉 Password reset complete!")
        print("You can now log in with:")
        print("Mobile: 08032194090")
        print("Password: nazz2020")
    else:
        print("\n❌ Password reset failed!")

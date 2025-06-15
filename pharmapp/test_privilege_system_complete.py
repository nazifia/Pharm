#!/usr/bin/env python
"""
Complete test of the privilege management system
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from userauth.models import Profile, UserPermission
import json

User = get_user_model()

def test_complete_privilege_system():
    """Test the complete privilege management system"""
    print("🧪 Testing Complete Privilege Management System")
    print("=" * 50)
    
    # Create test client
    client = Client()
    
    # Create admin user
    admin_user, created = User.objects.get_or_create(
        username='test_admin_complete',
        defaults={
            'mobile': '9991112222',
            'email': 'admin_complete@test.com',
            'is_active': True
        }
    )
    if created:
        admin_user.set_password('testpass123')
        admin_user.save()
        print(f"✅ Created admin user: {admin_user.username}")
    
    # Create admin profile
    admin_profile, created = Profile.objects.get_or_create(
        user=admin_user,
        defaults={
            'full_name': 'Test Admin Complete',
            'user_type': 'Admin'
        }
    )
    
    # Create test user
    test_user, created = User.objects.get_or_create(
        username='test_user_complete',
        defaults={
            'mobile': '8881112222',
            'email': 'user_complete@test.com',
            'is_active': True
        }
    )
    if created:
        test_user.set_password('testpass123')
        test_user.save()
        print(f"✅ Created test user: {test_user.username}")
    
    # Create test user profile
    test_profile, created = Profile.objects.get_or_create(
        user=test_user,
        defaults={
            'full_name': 'Test User Complete',
            'user_type': 'Salesperson'
        }
    )
    
    # Login as admin
    login_success = client.login(username='test_admin_complete', password='testpass123')
    print(f"Admin login successful: {login_success}")
    
    if not login_success:
        print("❌ Failed to login as admin")
        return
    
    print("\n📋 Testing API Endpoint")
    print("-" * 30)
    
    # Test API endpoint
    api_url = f'/api/user-permissions/{test_user.id}/'
    response = client.get(api_url)
    print(f"API endpoint status: {response.status_code}")
    
    if response.status_code == 200:
        data = json.loads(response.content)
        print(f"✅ API working - User: {data['user']['username']}")
        print(f"✅ Permissions loaded: {len(data['permissions'])} permissions")
        
        # Check some specific permissions
        permissions = data['permissions']
        sample_perms = list(permissions.keys())[:3]
        for perm in sample_perms:
            perm_data = permissions[perm]
            print(f"   {perm}: granted={perm_data['granted']}, source={perm_data['source']}")
    else:
        print(f"❌ API failed with status {response.status_code}")
        return
    
    print("\n📝 Testing Permission Assignment")
    print("-" * 30)
    
    # Test permission assignment via POST
    privilege_url = '/privilege-management/'
    
    # Prepare form data to grant a specific permission
    test_permission = 'manage_users'
    form_data = {
        'selected_user_id': test_user.id,
        f'permission_{test_permission}': 'on',  # Grant this permission
        'csrfmiddlewaretoken': client.cookies['csrftoken'].value if 'csrftoken' in client.cookies else ''
    }
    
    # Get CSRF token first
    get_response = client.get(privilege_url)
    if get_response.status_code == 200:
        print("✅ Privilege management page accessible")
        
        # Extract CSRF token from the response
        csrf_token = None
        if hasattr(get_response, 'context') and get_response.context:
            csrf_token = get_response.context.get('csrf_token')
        
        if not csrf_token:
            # Try to get it from cookies
            csrf_token = client.cookies.get('csrftoken')
            if csrf_token:
                csrf_token = csrf_token.value
        
        if csrf_token:
            form_data['csrfmiddlewaretoken'] = csrf_token
            
            # Submit the form
            post_response = client.post(privilege_url, form_data)
            print(f"Permission assignment status: {post_response.status_code}")
            
            if post_response.status_code in [200, 302]:  # Success or redirect
                print("✅ Permission assignment submitted successfully")
                
                # Verify the permission was actually saved
                try:
                    user_perm = UserPermission.objects.get(user=test_user, permission=test_permission)
                    print(f"✅ Permission saved: {test_permission} = {user_perm.granted}")
                    print(f"   Granted by: {user_perm.granted_by.username}")
                    print(f"   Notes: {user_perm.notes}")
                    
                    # Test if the user actually has the permission now
                    has_permission = test_user.has_permission(test_permission)
                    print(f"✅ User actually has permission: {has_permission}")
                    
                except UserPermission.DoesNotExist:
                    print("❌ Permission was not saved to database")
            else:
                print(f"❌ Permission assignment failed with status {post_response.status_code}")
        else:
            print("❌ Could not get CSRF token")
    else:
        print(f"❌ Could not access privilege management page: {get_response.status_code}")
    
    print("\n🎉 Test completed!")
    
    # Cleanup
    print("\n🧹 Cleaning up test data...")
    UserPermission.objects.filter(user=test_user).delete()
    if created:
        admin_user.delete()
        test_user.delete()
    print("   Test data cleaned up")

if __name__ == '__main__':
    try:
        test_complete_privilege_system()
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

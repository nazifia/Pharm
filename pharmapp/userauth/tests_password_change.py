from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from userauth.models import Profile, PasswordChangeHistory
from userauth.models import USER_PERMISSIONS

User = get_user_model()


class PasswordChangeTestCase(TestCase):
    """Test cases for password change functionality"""
    
    def setUp(self):
        """Set up test data"""
        # Create admin user (superuser)
        self.admin_user = User(
            username='admin',
            mobile='08011111111',
            email='admin@test.com'
        )
        self.admin_user.set_password('adminpass123')
        self.admin_user.is_superuser = True
        self.admin_user.save()
        
        # Check if profile already exists before creating
        if Profile.objects.filter(user=self.admin_user).exists():
            self.admin_profile = Profile.objects.get(user=self.admin_user)
        else:
            self.admin_profile = Profile.objects.create(
                user=self.admin_user,
                full_name='Admin User',
                user_type='Admin'
            )
        
        # Create manager user
        self.manager_user = User(
            username='manager',
            mobile='08022222222',
            email='manager@test.com'
        )
        self.manager_user.set_password('managerpass123')
        self.manager_user.save()
        
        # Check if profile already exists before creating
        if Profile.objects.filter(user=self.manager_user).exists():
            self.manager_profile = Profile.objects.get(user=self.manager_user)
        else:
            self.manager_profile = Profile.objects.create(
                user=self.manager_user,
                full_name='Manager User',
                user_type='Manager'
            )
        
        # Create regular user
        self.regular_user = User(
            username='regular',
            mobile='08033333333',
            email='regular@test.com'
        )
        self.regular_user.set_password('regularpass123')
        self.regular_user.save()
        
        # Check if profile already exists before creating
        if Profile.objects.filter(user=self.regular_user).exists():
            self.regular_profile = Profile.objects.get(user=self.regular_user)
        else:
            self.regular_profile = Profile.objects.create(
                user=self.regular_user,
                full_name='Regular User',
                user_type='Salesperson'
            )
        
        self.client = Client()
    
    def test_admin_permissions(self):
        """Test that admin has password management permission"""
        # Check if Admin role has manage_user_passwords permission
        admin_perms = USER_PERMISSIONS.get('Admin', [])
        self.assertIn('manage_user_passwords', admin_perms)
        
        # Check if user has_permission method works
        self.assertTrue(self.admin_user.has_permission('manage_user_passwords'))
    
    def test_manager_permissions(self):
        """Test that manager has password management permission"""
        # Check if Manager role has manage_user_passwords permission
        manager_perms = USER_PERMISSIONS.get('Manager', [])
        print(f"Manager permissions from USER_PERMISSIONS: {manager_perms}")
        self.assertIn('manage_user_passwords', manager_perms)
        
        # Check if user has_permission method works
        has_perm = self.manager_user.has_permission('manage_user_passwords')
        print(f"Manager has_permission result: {has_perm}")
        
        # Debug the profile user type
        print(f"Manager profile user type: {self.manager_profile.user_type}")
        self.assertTrue(has_perm)
    
    def test_regular_user_no_permission(self):
        """Test that regular user doesn't have password management permission"""
        # Check if Salesperson role has manage_user_passwords permission
        salesperson_perms = USER_PERMISSIONS.get('Salesperson', [])
        self.assertNotIn('manage_user_passwords', salesperson_perms)
        
        # Check if user has_permission method works
        self.assertFalse(self.regular_user.has_permission('manage_user_passwords'))
    
    def test_admin_can_access_password_change_page(self):
        """Test that admin can access password change page"""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('userauth:change_user_password', args=[self.regular_user.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Change Password')
    
    def test_manager_can_access_password_change_page(self):
        """Test that manager can access password change page"""
        self.client.login(username='manager', password='managerpass123')
        response = self.client.get(reverse('userauth:change_user_password', args=[self.regular_user.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Change Password')
    
    def test_regular_user_cannot_access_password_change_page(self):
        """Test that regular user cannot access password change page"""
        self.client.login(username='regular', password='regularpass123')
        response = self.client.get(reverse('userauth:change_user_password', args=[self.regular_user.id]))
        
        # Should be redirected to dashboard with permission error message
        self.assertEqual(response.status_code, 302)  # Redirect due to permission denied
    
    def test_password_change_form_submission(self):
        """Test successful password change form submission"""
        self.client.login(username='admin', password='adminpass123')
        
        form_data = {
            'new_password': 'newsecurepass456',
            'confirm_password': 'newsecurepass456',
            'change_reason': 'Security audit requirement',
            'confirmChange': True
        }
        
        response = self.client.post(
            reverse('userauth:change_user_password', args=[self.regular_user.id]),
            form_data,
            follow=True
        )
        
        # Should show success message
        self.assertContains(response, 'Password for regular has been changed successfully.')
        
        # Check that password was actually changed
        self.regular_user.refresh_from_db()
        self.assertTrue(self.regular_user.check_password('newsecurepass456'))
        
        # Check that password change history was created
        change_history = PasswordChangeHistory.objects.filter(
            user=self.regular_user,
            changed_by=self.admin_user
        ).first()
        
        self.assertIsNotNone(change_history)
        self.assertEqual(change_history.change_reason, 'Security audit requirement')
    
    def test_cannot_change_own_password(self):
        """Test that user cannot change their own password through admin interface"""
        self.client.login(username='admin', password='adminpass123')
        
        form_data = {
            'new_password': 'newpass123',
            'confirm_password': 'newpass123',
            'change_reason': 'Self test',
            'confirmChange': True
        }
        
        response = self.client.post(
            reverse('userauth:change_user_password', args=[self.admin_user.id]),
            form_data,
            follow=True
        )
        
        # Should show error message
        self.assertContains(response, 'You cannot change your own password')
    
    def test_password_form_validation(self):
        """Test password form validation"""
        self.client.login(username='admin', password='adminpass123')
        
        # Test weak password
        form_data = {
            'new_password': 'weak',
            'confirm_password': 'weak',
            'change_reason': 'Test weak password',
            'confirmChange': True
        }
        
        response = self.client.post(
            reverse('userauth:change_user_password', args=[self.regular_user.id]),
            form_data
        )
        
        # Should show validation error (form should not be valid, so status 200 with errors)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Password must be at least 8 characters long')
        
        # Test mismatched passwords
        form_data = {
            'new_password': 'strongpass123',
            'confirm_password': 'differentpass456',
            'change_reason': 'Test mismatch',
            'confirmChange': True
        }
        
        response = self.client.post(
            reverse('userauth:change_user_password', args=[self.regular_user.id]),
            form_data
        )
        
        # Should show validation error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Passwords do not match')
    
    def test_password_history_access(self):
        """Test password history page access"""
        self.client.login(username='admin', password='adminpass123')
        response = self.client.get(reverse('userauth:password_change_history', args=[self.regular_user.id]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Password Change History')

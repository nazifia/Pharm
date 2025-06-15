#!/usr/bin/env python
"""
Test script for template filters
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmapp.settings')
django.setup()

def test_template_filters():
    """Test the custom template filters"""
    print("🏷️ Testing Template Filters...")

    try:
        from store.templatetags.custom_filters import replace, format_permission, has_permission, get_user_role

        # Test format_permission filter
        test_permission = "manage_users"
        formatted = format_permission(test_permission)
        expected = "Manage Users"
        if formatted == expected:
            print(f"  ✓ format_permission works: '{test_permission}' -> '{formatted}'")
        else:
            print(f"  ✗ format_permission failed: expected '{expected}', got '{formatted}'")
            return False

        # Test replace filter
        test_string = "hello_world"
        replaced = replace(test_string, "_, ")
        expected = "hello world"
        if replaced == expected:
            print(f"  ✓ replace filter works: '{test_string}' -> '{replaced}'")
        else:
            print(f"  ✗ replace filter failed: expected '{expected}', got '{replaced}'")
            return False

        # Test replace filter with different args
        test_string2 = "test-string-here"
        replaced2 = replace(test_string2, "-,_")
        expected2 = "test_string_here"
        if replaced2 == expected2:
            print(f"  ✓ replace filter works with different args: '{test_string2}' -> '{replaced2}'")
        else:
            print(f"  ✗ replace filter failed: expected '{expected2}', got '{replaced2}'")
            return False

        print("  ✓ All template filters working correctly!")
        return True

    except Exception as e:
        print(f"  ✗ Template filter test failed: {e}")
        return False

def test_template_loading():
    """Test that templates can be loaded without errors"""
    print("\n📄 Testing Template Loading...")

    try:
        from django.template.loader import get_template

        # Test loading templates that use custom filters
        templates_to_test = [
            'userauth/user_details.html',
            'userauth/privilege_management.html',
            '403.html'
        ]

        for template_name in templates_to_test:
            try:
                template = get_template(template_name)
                print(f"  ✓ {template_name} loaded successfully")
            except Exception as e:
                print(f"  ✗ {template_name} failed to load: {e}")
                return False

        print("  ✓ All templates loaded successfully!")
        return True

    except Exception as e:
        print(f"  ✗ Template loading test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 TESTING TEMPLATE FILTERS AND TEMPLATES")
    print("=" * 50)

    all_tests_passed = True

    if not test_template_filters():
        all_tests_passed = False

    if not test_template_loading():
        all_tests_passed = False

    if all_tests_passed:
        print("\n🎉 ALL TEMPLATE TESTS PASSED!")
        print("The template filter issue has been resolved.")
        print("✅ Templates are ready to use!")
    else:
        print("\n❌ SOME TEMPLATE TESTS FAILED!")
        return False

    return True

if __name__ == '__main__':
    success = main()
    if not success:
        sys.exit(1)

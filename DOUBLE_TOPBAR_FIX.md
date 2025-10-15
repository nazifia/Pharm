# Double Topbar/Sidebar Issue - Troubleshooting Guide

## Possible Causes

### 1. Browser Cache Issue
**Most Common Cause**
- Old cached version of the page with duplicate elements
- **Solution**: Hard refresh the page
  - Windows/Linux: `Ctrl + Shift + R` or `Ctrl + F5`
  - Mac: `Cmd + Shift + R`
  - Or clear browser cache completely

### 2. Browser Extension Interference
- Ad blockers or page modifiers might be duplicating elements
- **Solution**: Try in incognito/private mode or disable extensions

### 3. JavaScript Duplication
- A script might be cloning the topbar/sidebar
- **Solution**: Check browser console for errors (F12)

### 4. Template Nesting Issue
- Page might be loaded inside another page context
- **Solution**: Check if URL is being loaded in iframe or HTMX container

### 5. Multiple Base Template Inheritance
- Template might be extending base.html multiple times
- **Solution**: Verify template structure

## Quick Fixes to Try

### Fix 1: Clear Browser Cache
```bash
# In browser:
1. Press F12 to open DevTools
2. Right-click the refresh button
3. Select "Empty Cache and Hard Reload"
```

### Fix 2: Check for JavaScript Errors
```bash
# In browser:
1. Press F12
2. Go to Console tab
3. Look for any errors (red text)
4. Share the errors if any
```

### Fix 3: Verify Page Structure
```bash
# In browser DevTools:
1. Press F12
2. Go to Elements tab
3. Search for "navbar-nav" (Ctrl+F in Elements)
4. Count how many times it appears
5. Should appear only ONCE
```

### Fix 4: Check if Page is in iframe
```javascript
// Run this in browser console (F12 -> Console):
console.log('Is in iframe:', window.self !== window.top);
console.log('Number of navbars:', document.querySelectorAll('.navbar-nav').length);
console.log('Number of sidebars:', document.querySelectorAll('#accordionSidebar').length);
```

## If Issue Persists

### Check Template Structure
The template should have this structure:
```html
{% extends "partials/base.html" %}
{% block content %}
    <!-- Your content here -->
{% endblock %}
```

### Verify No Duplicate Includes
Make sure the template doesn't have:
- Multiple `{% extends %}` tags
- Nested base template includes
- Duplicate sidebar/topbar includes

### Check for HTMX Issues
If the page is loaded via HTMX, it might be loading the full page into a container that already has the base layout.

**Solution**: Create a partial template without base.html for HTMX requests.

## Diagnostic Steps

1. **View Page Source** (Ctrl+U)
   - Count occurrences of `<nav class="navbar"`
   - Count occurrences of `<ul class="navbar-nav bg-gradient-primary sidebar"`
   - Should each appear only ONCE

2. **Check Network Tab**
   - Press F12 -> Network tab
   - Reload page
   - Check if page is being loaded multiple times

3. **Check for Duplicate IDs**
   - In DevTools Elements tab, search for `id="wrapper"`
   - Should appear only ONCE
   - If appears multiple times, that's the issue

## Temporary Workaround

If you need to use the page immediately while troubleshooting:

1. Use browser's "Reader Mode" if available
2. Or use incognito/private browsing mode
3. Or try a different browser

## Reporting the Issue

If none of the above fixes work, please provide:
1. Screenshot of the page
2. Screenshot of browser console (F12 -> Console)
3. Screenshot of Elements tab showing the duplicate elements
4. Browser name and version
5. Any error messages in console

## Prevention

To prevent this issue in the future:
1. Always clear cache after template changes
2. Use hard refresh (Ctrl+Shift+R) when testing
3. Check browser console for errors regularly
4. Avoid nesting pages that extend base.html


# 💊 Dispensing Features Guide

## Overview
The pharmacy application provides comprehensive dispensing management features to track, analyze, and manage medication dispensing activities by users. This guide covers all available dispensing features and how to access them.

## 🚀 Quick Access Points

### **1. Sidebar Navigation**
The main sidebar now includes a dedicated **"Dispensing Management"** section:

#### **Dispensing Operations:**
- **Dispense Items** - Main dispensing interface
- **Dispensing Log** - Complete dispensing history

#### **User Analytics:**
- **User Summary** - Performance overview by user
- **Detailed Reports** - Comprehensive dispensing breakdown

### **2. Dashboard Quick Access**
The dashboard features a **"Dispensing Management"** card with:
- **View Log** button - Direct access to dispensing log
- **User Summary** button - Quick user analytics access

### **3. Store Interface Links**
Both retail and wholesale interfaces include quick access buttons:
- **Dispensing Log** - View all dispensing activities
- **User Summary** - Analyze user performance

## 📊 Available Features

### **1. Dispensing Log**
**URL:** `/store/dispensing_log/`

**Features:**
- ✅ Real-time search and filtering
- ✅ Filter by item name, date, status, and user
- ✅ Auto-complete search suggestions
- ✅ HTMX-powered live updates
- ✅ Export and print capabilities
- ✅ **Permission-based access**: Admins/Managers see all users, others see only their own data

**Information Displayed:**
- User who dispensed the item
- Item name, brand, and unit
- Quantity dispensed
- Rate and total amount
- Status (Dispensed, Returned, Partially Returned)
- Return information
- Timestamp

### **2. User Dispensing Summary**
**URL:** `/store/user_dispensing_summary/`

**Features:**
- ✅ Performance metrics by user
- ✅ Date range filtering
- ✅ User-specific filtering (for admins/managers)
- ✅ Net calculations (dispensed - returned)
- ✅ Sortable by performance metrics
- ✅ **Permission-based access**: Shows "My Summary" for regular users, "All Users" for admins/managers

**Metrics Displayed:**
- Items dispensed count and amount
- Items returned count and amount
- Net dispensed quantity and amount
- Performance comparison between users

### **3. User Dispensing Details**
**URL:** `/store/user_dispensing_details/`

**Features:**
- ✅ Detailed breakdown of all dispensing activities
- ✅ Filter by user, date range, and status
- ✅ Individual transaction details
- ✅ Comprehensive audit trail
- ✅ **Permission-based access**: Regular users see only their own data

**Information Displayed:**
- Complete dispensing history
- Individual transaction details
- User-specific activity breakdown
- Status-based filtering

### **4. My Dispensing Details** (New!)
**URL:** `/store/my_dispensing_details/`

**Features:**
- ✅ Personal dispensing history for any user
- ✅ Quick access to own dispensing data
- ✅ Same filtering capabilities as main details view
- ✅ **Available to all users** - everyone can view their own dispensing history

**Information Displayed:**
- Personal dispensing activities only
- Individual transaction history
- Personal performance metrics
- Own return/dispensing patterns

## 🔍 How to Access Features

### **Method 1: Sidebar Navigation**
1. Open the main sidebar
2. Expand **"Dispensing Management"**
3. Choose your desired feature:
   - **Dispense Items** → Dispensing interface
   - **Dispensing Log** → Complete log
   - **User Summary** → Performance analytics
   - **Detailed Reports** → Comprehensive breakdown

### **Method 2: Dashboard**
1. Go to Dashboard (`/dashboard/`)
2. Look for **"Dispensing Management"** card
3. Click **"View Log"** or **"User Summary"**

### **Method 3: Store/Wholesale Interface**
1. Go to Store (`/store/`) or Wholesale (`/wholesales/`)
2. Look for action buttons section
3. Click **"Dispensing Log"** or **"User Summary"**

### **Method 4: Reports Section**
1. Open sidebar → **"Reports & Analytics"**
2. Under **"General Reports"** find:
   - **Dispensing Log**
   - **User Dispensing Summary**
   - **User Dispensing Details**

## 🎯 Use Cases

### **For Pharmacists:**
- Track daily dispensing activities
- Monitor medication distribution
- Review dispensing history

### **For Managers:**
- Analyze user performance
- Monitor dispensing trends
- Generate compliance reports

### **For Administrators:**
- Comprehensive audit trails
- User activity monitoring
- Performance analytics

## 🔧 Advanced Features

### **Search & Filtering:**
- **Item Name Search** - Type first few letters for auto-complete
- **Date Filtering** - Filter by specific dates
- **Status Filtering** - Filter by dispensing status
- **User Filtering** - Focus on specific users

### **Export Options:**
- **Print A4** - Professional printouts
- **Live Updates** - Real-time data refresh
- **Responsive Design** - Works on all devices

## 📱 Mobile Access
All dispensing features are fully responsive and accessible on:
- Desktop computers
- Tablets
- Mobile phones
- Touch devices

## 🔗 Direct URLs
For quick bookmarking:
- **Dispensing Log:** `http://127.0.0.1:8000/dispensing_log/`
- **User Summary:** `http://127.0.0.1:8000/user_dispensing_summary/`
- **User Details:** `http://127.0.0.1:8000/user_dispensing_details/`
- **My Details:** `http://127.0.0.1:8000/my_dispensing_details/` (Personal access)

## 🔐 Permission System

### **For Superusers & Staff:**
- ✅ **Full system access** - Can view all users' dispensing data
- ✅ **Administrative privileges** - Complete control over dispensing features
- ✅ **User management** - Filter and analyze any user's data
- ✅ **System-wide analytics** - Access to all dispensing metrics
- ✅ **Comprehensive reporting** - Generate reports for entire organization

### **For Administrators & Managers:**
- ✅ View all users' dispensing data
- ✅ Filter by any user in the system
- ✅ Access comprehensive analytics
- ✅ Generate reports for all staff
- ✅ User selection dropdowns available

### **For Regular Users (Pharmacists, Pharm-Tech, Salesperson):**
- ✅ View only their own dispensing data
- ✅ Access personal performance metrics
- ✅ Filter their own dispensing history
- ✅ Generate personal reports
- ✅ Quick access via "My Details" links

### **Permission Hierarchy:**
1. **Superusers** (`is_superuser=True`) - Full access to everything
2. **Staff Users** (`is_staff=True`) - Full access to dispensing features
3. **Admin Users** (`profile.user_type='Admin'`) - Full dispensing access
4. **Manager Users** (`profile.user_type='Manager'`) - Full dispensing access
5. **Other Users** - Limited to personal data only

## 💡 Tips for Best Use

1. **Regular Monitoring:** Check dispensing logs daily for accuracy
2. **User Training:** Use user summary to identify training needs
3. **Performance Review:** Analyze detailed reports for insights
4. **Compliance:** Maintain audit trails for regulatory requirements
5. **Quick Access:** Bookmark frequently used features

## 🆘 Troubleshooting

**Can't find dispensing features?**
- Check sidebar → "Dispensing Management"
- Look for dashboard quick access cards
- Use Reports & Analytics section

**Need specific user data?**
- Use User Dispensing Summary for overview
- Use User Dispensing Details for comprehensive data
- Apply filters for targeted results

**Want historical data?**
- Use date range filters
- Check dispensing log with date filters
- Export data for external analysis

---

**Note:** All dispensing features require user authentication and appropriate permissions. Contact your system administrator if you cannot access certain features.

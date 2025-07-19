/**
 * Enhanced Privilege Management System
 * Advanced user permission and role management with bulk operations
 */

class EnhancedPrivilegeManager {
    constructor() {
        this.selectedUserId = null;
        this.selectedUsers = new Set();
        this.currentUserPermissions = {};
        this.allPermissions = {};
        this.permissionCategories = {
            'user-management': ['manage_users', 'edit_user_profiles', 'access_admin_panel'],
            'inventory-management': ['manage_inventory', 'perform_stock_check', 'transfer_stock', 'adjust_prices'],
            'sales-management': ['process_sales', 'process_returns', 'process_split_payments', 'manage_customers'],
            'reports-management': ['view_reports', 'view_financial_reports', 'view_activity_logs', 'view_sales_history']
        };
        this.roleTemplates = {
            'Admin': ['manage_users', 'view_financial_reports', 'manage_system_settings', 'access_admin_panel', 'manage_inventory', 'dispense_medication', 'process_sales', 'view_reports', 'approve_procurement', 'manage_customers', 'manage_suppliers', 'manage_expenses', 'adjust_prices', 'process_returns', 'approve_returns', 'transfer_stock', 'view_activity_logs', 'perform_stock_check', 'edit_user_profiles', 'manage_payment_methods', 'process_split_payments', 'override_payment_status', 'pause_resume_procurement', 'search_items'],
            'Manager': ['manage_inventory', 'dispense_medication', 'process_sales', 'view_reports', 'approve_procurement', 'manage_customers', 'manage_suppliers', 'manage_expenses', 'adjust_prices', 'process_returns', 'approve_returns', 'transfer_stock', 'view_activity_logs', 'perform_stock_check', 'manage_payment_methods', 'process_split_payments', 'override_payment_status', 'pause_resume_procurement', 'search_items'],
            'Pharmacist': ['manage_inventory', 'dispense_medication', 'process_sales', 'manage_customers', 'process_returns', 'transfer_stock', 'view_sales_history', 'view_procurement_history', 'perform_stock_check', 'process_split_payments', 'search_items'],
            'Pharm-Tech': ['manage_inventory', 'process_sales', 'manage_customers', 'process_returns', 'transfer_stock', 'view_sales_history', 'view_procurement_history', 'perform_stock_check', 'process_split_payments', 'search_items'],
            'Salesperson': ['process_sales', 'manage_customers', 'view_sales_history', 'process_split_payments', 'search_items']
        };
        
        this.init();
    }

    init() {
        this.bindEventListeners();
        this.loadPermissionData();
        this.updateStatistics();
        this.setupUserCheckboxes();
    }

    bindEventListeners() {
        // User search
        const userSearch = document.getElementById('user-search');
        if (userSearch) {
            userSearch.addEventListener('input', this.debounce(() => this.searchUsers(), 300));
        }

        // Role filter
        const roleFilter = document.getElementById('role-filter');
        if (roleFilter) {
            roleFilter.addEventListener('change', () => this.filterUsersByRole());
        }

        // User checkboxes for bulk operations
        document.querySelectorAll('.user-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => this.handleUserSelection(e));
        });

        // Permission checkboxes
        document.querySelectorAll('.permission-list input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', () => this.handlePermissionChange());
        });
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // User Selection and Management
    selectUser(userId) {
        this.selectedUserId = userId;

        // Update UI
        document.querySelectorAll('.user-item').forEach(item => {
            item.classList.remove('selected');
        });

        const selectedItem = document.querySelector(`[data-user-id="${userId}"]`);
        if (selectedItem) {
            selectedItem.classList.add('selected');
        }

        // Load user permissions
        this.loadUserPermissions(userId);

        // Show permission management panel
        document.getElementById('selected-user-info').style.display = 'block';
        document.getElementById('permission-actions').style.display = 'block';
        document.getElementById('permissions-summary-section').style.display = 'block';
    }

    handleUserSelection(event) {
        const userId = parseInt(event.target.value);
        
        if (event.target.checked) {
            this.selectedUsers.add(userId);
        } else {
            this.selectedUsers.delete(userId);
        }

        this.updateBulkActionsVisibility();
        this.updateSelectedUsersDisplay();
    }

    updateBulkActionsVisibility() {
        const bulkActions = document.getElementById('bulk-actions');
        if (bulkActions) {
            bulkActions.style.display = this.selectedUsers.size > 0 ? 'block' : 'none';
        }
    }

    updateSelectedUsersDisplay() {
        const countElement = document.getElementById('selected-users-count');
        if (countElement) {
            countElement.textContent = this.selectedUsers.size;
        }

        const listElement = document.getElementById('selected-users-list');
        if (listElement) {
            listElement.innerHTML = '';
            this.selectedUsers.forEach(userId => {
                const userItem = document.querySelector(`[data-user-id="${userId}"]`);
                if (userItem) {
                    const userName = userItem.querySelector('.user-info h6').textContent;
                    const userRole = userItem.dataset.role;
                    
                    const userElement = document.createElement('div');
                    userElement.className = 'selected-user-item';
                    userElement.innerHTML = `
                        <div class="d-flex justify-content-between align-items-center">
                            <span>${userName} <small class="text-muted">(${userRole})</small></span>
                            <button class="btn btn-sm btn-outline-danger" onclick="privilegeManager.removeFromSelection(${userId})">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    `;
                    listElement.appendChild(userElement);
                }
            });
        }
    }

    removeFromSelection(userId) {
        this.selectedUsers.delete(userId);
        const checkbox = document.querySelector(`input[value="${userId}"]`);
        if (checkbox) {
            checkbox.checked = false;
        }
        this.updateBulkActionsVisibility();
        this.updateSelectedUsersDisplay();
    }

    // Search and Filter Functions
    searchUsers() {
        const searchTerm = document.getElementById('user-search').value.toLowerCase();
        const userItems = document.querySelectorAll('.user-item');

        userItems.forEach(item => {
            const userName = item.querySelector('.user-info h6').textContent.toLowerCase();
            const userRole = item.dataset.role.toLowerCase();
            
            if (userName.includes(searchTerm) || userRole.includes(searchTerm)) {
                item.style.display = 'flex';
            } else {
                item.style.display = 'none';
            }
        });
    }

    filterUsersByRole() {
        const selectedRole = document.getElementById('role-filter').value;
        const userItems = document.querySelectorAll('.user-item');

        userItems.forEach(item => {
            if (!selectedRole || item.dataset.role === selectedRole) {
                item.style.display = 'flex';
            } else {
                item.style.display = 'none';
            }
        });
    }

    // Permission Management
    loadUserPermissions(userId) {
        fetch(`/api/user-permissions/${userId}/`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.currentUserPermissions = data.permissions;
                    this.updatePermissionUI(data.user);
                    this.setPermissionCheckboxes(data.permissions);
                    this.updateCurrentPermissionsDisplay(data.user, data.permissions);
                } else {
                    this.showError('Failed to load user permissions');
                }
            })
            .catch(error => {
                console.error('Error loading user permissions:', error);
                this.showError('Error loading user permissions');
            });
    }

    updatePermissionUI(user) {
        document.getElementById('selected-user-name').textContent = user.full_name || user.username;
        document.getElementById('selected-user-role').textContent = user.user_type;
        document.getElementById('selected-user-avatar').textContent = (user.full_name || user.username).charAt(0).toUpperCase();
    }

    setPermissionCheckboxes(permissions) {
        // Clear all checkboxes first
        document.querySelectorAll('.permission-list input[type="checkbox"]').forEach(checkbox => {
            checkbox.checked = false;
        });

        // Set permissions
        Object.entries(permissions).forEach(([permission, granted]) => {
            const checkbox = document.getElementById(permission);
            if (checkbox) {
                checkbox.checked = granted;
            }
        });
    }

    updateCurrentPermissionsDisplay(user, permissions) {
        const displayDiv = document.getElementById('current-permissions-display');

        // Debug logging (remove in production)
        console.log('updateCurrentPermissionsDisplay called with:', { user, permissions });
        console.log('Role templates:', this.roleTemplates);

        if (!user || !permissions) {
            displayDiv.innerHTML = '<p class="text-muted text-center">Select a user to view their current permissions.</p>';
            return;
        }

        // Get user's role permissions for comparison
        const rolePermissions = this.roleTemplates[user.user_type] || [];

        // Categorize permissions based on the actual API response structure
        const allGrantedPermissions = [];
        const roleBasedPermissions = [];
        const individuallyGrantedPermissions = [];
        const individuallyRevokedPermissions = [];

        // Process all permissions
        Object.entries(permissions).forEach(([permission, isGranted]) => {
            const isRolePermission = rolePermissions.includes(permission);

            if (isGranted) {
                allGrantedPermissions.push(permission);
                if (isRolePermission) {
                    roleBasedPermissions.push(permission);
                } else {
                    // This permission is granted but not in role - individually granted
                    individuallyGrantedPermissions.push(permission);
                }
            } else if (isRolePermission) {
                // This is a role permission that has been individually revoked
                individuallyRevokedPermissions.push(permission);
            }
        });

        let html = `
            <div class="user-permissions-summary">
                <h6>Permissions for: <span class="badge bg-primary">${user.full_name || user.username}</span>
                <small class="text-muted">(${user.user_type})</small></h6>
        `;

        // Show all granted permissions first
        if (allGrantedPermissions.length > 0) {
            html += `
                <div class="permission-category mb-3">
                    <h6 class="text-success"><i class="fas fa-check-circle"></i> All Active Permissions (${allGrantedPermissions.length})</h6>
                    <div class="permission-badges">
            `;
            allGrantedPermissions.forEach(permission => {
                const displayName = permission.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                const isFromRole = rolePermissions.includes(permission);
                const badgeClass = isFromRole ? 'bg-success' : 'bg-info';
                const tooltip = isFromRole ? 'From Role' : 'Individually Granted';
                html += `<span class="badge ${badgeClass} me-1 mb-1" title="${tooltip}">${displayName}</span>`;
            });
            html += `</div></div>`;
        }

        // Role-based permissions breakdown
        if (roleBasedPermissions.length > 0) {
            html += `
                <div class="permission-category mb-3">
                    <h6 class="text-success"><i class="fas fa-user-tag"></i> From Role Template (${roleBasedPermissions.length})</h6>
                    <div class="permission-badges">
            `;
            roleBasedPermissions.forEach(permission => {
                const displayName = permission.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                html += `<span class="badge bg-success me-1 mb-1">${displayName}</span>`;
            });
            html += `</div></div>`;
        }

        // Individually granted permissions
        if (individuallyGrantedPermissions.length > 0) {
            html += `
                <div class="permission-category mb-3">
                    <h6 class="text-info"><i class="fas fa-plus-circle"></i> Individually Granted (${individuallyGrantedPermissions.length})</h6>
                    <div class="permission-badges">
            `;
            individuallyGrantedPermissions.forEach(permission => {
                const displayName = permission.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                html += `<span class="badge bg-info me-1 mb-1">${displayName}</span>`;
            });
            html += `</div></div>`;
        }

        // Individually revoked permissions
        if (individuallyRevokedPermissions.length > 0) {
            html += `
                <div class="permission-category mb-3">
                    <h6 class="text-danger"><i class="fas fa-minus-circle"></i> Individually Revoked (${individuallyRevokedPermissions.length})</h6>
                    <div class="permission-badges">
            `;
            individuallyRevokedPermissions.forEach(permission => {
                const displayName = permission.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                html += `<span class="badge bg-danger me-1 mb-1">${displayName}</span>`;
            });
            html += `</div></div>`;
        }

        // Show message if no permissions
        if (allGrantedPermissions.length === 0) {
            html += `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle"></i> This user currently has no active permissions.
                </div>
            `;
        }

        // Summary statistics
        const totalGranted = allGrantedPermissions.length;
        const totalRevoked = individuallyRevokedPermissions.length;
        const fromRole = roleBasedPermissions.length;
        const individual = individuallyGrantedPermissions.length;

        html += `
            <div class="permission-summary-stats mt-3">
                <div class="row">
                    <div class="col-md-3">
                        <div class="stat-item text-center">
                            <h5 class="text-success">${totalGranted}</h5>
                            <small class="text-muted">Total Active</small>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="stat-item text-center">
                            <h5 class="text-primary">${fromRole}</h5>
                            <small class="text-muted">From Role</small>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="stat-item text-center">
                            <h5 class="text-info">${individual}</h5>
                            <small class="text-muted">Individual</small>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="stat-item text-center">
                            <h5 class="text-danger">${totalRevoked}</h5>
                            <small class="text-muted">Revoked</small>
                        </div>
                    </div>
                </div>
            </div>
        `;

        html += `
            <div class="mt-3">
                <p class="text-info"><i class="fas fa-info-circle"></i> Use the permission management panel above to modify permissions for this user.</p>
            </div>
        </div>`;

        displayDiv.innerHTML = html;
    }

    handlePermissionChange() {
        // Mark that permissions have been modified
        const saveButton = document.querySelector('[onclick="savePermissions()"]');
        if (saveButton) {
            saveButton.classList.add('btn-warning');
            saveButton.innerHTML = '<i class="fas fa-save"></i> Save Changes*';
        }
    }

    // Category Management
    toggleCategoryPermissions(categoryId, selectAll) {
        const permissions = this.permissionCategories[categoryId] || [];
        
        permissions.forEach(permission => {
            const checkbox = document.getElementById(permission);
            if (checkbox) {
                checkbox.checked = selectAll;
            }
        });

        this.handlePermissionChange();
    }

    // Role Templates
    applyRoleTemplate() {
        if (!this.selectedUserId) {
            this.showError('Please select a user first');
            return;
        }

        const userItem = document.querySelector(`[data-user-id="${this.selectedUserId}"]`);
        const userRole = userItem ? userItem.dataset.role : null;

        if (!userRole || !this.roleTemplates[userRole]) {
            this.showError('No template available for this role');
            return;
        }

        // Clear all permissions first
        document.querySelectorAll('.permission-list input[type="checkbox"]').forEach(checkbox => {
            checkbox.checked = false;
        });

        // Apply role template
        const rolePermissions = this.roleTemplates[userRole];
        rolePermissions.forEach(permission => {
            const checkbox = document.getElementById(permission);
            if (checkbox) {
                checkbox.checked = true;
            }
        });

        this.handlePermissionChange();
        this.showSuccess(`Applied ${userRole} template successfully`);
    }

    // Save and Reset Functions
    savePermissions() {
        if (!this.selectedUserId) {
            this.showError('No user selected');
            return;
        }

        const permissions = {};
        document.querySelectorAll('.permission-list input[type="checkbox"]').forEach(checkbox => {
            permissions[checkbox.id] = checkbox.checked;
        });

        fetch('/api/save-user-permissions/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken(),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                user_id: this.selectedUserId,
                permissions: permissions
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showSuccess('Permissions saved successfully');
                this.resetSaveButton();
                this.updateStatistics();
                // Reload user permissions to update summary
                this.loadUserPermissions(this.selectedUserId);
            } else {
                this.showError('Failed to save permissions: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error saving permissions:', error);
            this.showError('Error saving permissions');
        });
    }

    resetPermissions() {
        if (!this.selectedUserId) {
            this.showError('No user selected');
            return;
        }

        this.setPermissionCheckboxes(this.currentUserPermissions);
        this.resetSaveButton();
    }

    resetSaveButton() {
        const saveButton = document.querySelector('[onclick="savePermissions()"]');
        if (saveButton) {
            saveButton.classList.remove('btn-warning');
            saveButton.classList.add('btn-success');
            saveButton.innerHTML = '<i class="fas fa-save"></i> Save Changes';
        }
    }

    // Bulk Operations
    openBulkOperationsModal() {
        if (this.selectedUsers.size === 0) {
            this.showError('Please select users first');
            return;
        }

        this.updateSelectedUsersDisplay();
        new bootstrap.Modal(document.getElementById('bulkOperationsModal')).show();
    }

    executeBulkOperations() {
        const roleTemplate = document.getElementById('bulk-role-template').value;
        const statusChange = document.getElementById('bulk-status-change').value;

        if (!roleTemplate && !statusChange) {
            this.showError('Please select at least one operation');
            return;
        }

        const operations = {
            user_ids: Array.from(this.selectedUsers),
            role_template: roleTemplate,
            status_change: statusChange
        };

        fetch('/api/bulk-operations/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken(),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(operations)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showSuccess(`Bulk operations completed successfully. ${data.affected_users} users updated.`);
                bootstrap.Modal.getInstance(document.getElementById('bulkOperationsModal')).hide();
                this.clearSelection();
                this.refreshUserList();
            } else {
                this.showError('Bulk operations failed: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error executing bulk operations:', error);
            this.showError('Error executing bulk operations');
        });
    }

    clearSelection() {
        this.selectedUsers.clear();
        document.querySelectorAll('.user-checkbox').forEach(checkbox => {
            checkbox.checked = false;
        });
        this.updateBulkActionsVisibility();
    }

    // Permission Matrix
    showPermissionMatrix() {
        fetch('/api/permission-matrix/')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.buildPermissionMatrix(data.matrix);
                    new bootstrap.Modal(document.getElementById('permissionMatrixModal')).show();
                } else {
                    this.showError('Failed to load permission matrix');
                }
            })
            .catch(error => {
                console.error('Error loading permission matrix:', error);
                this.showError('Error loading permission matrix');
            });
    }

    buildPermissionMatrix(matrixData) {
        const tbody = document.getElementById('permission-matrix-body');
        const table = document.querySelector('.permission-matrix-table');
        
        // Clear existing content
        tbody.innerHTML = '';
        
        // Build header with permissions
        const thead = table.querySelector('thead tr');
        const existingHeaders = thead.querySelectorAll('th');
        
        // Remove permission headers (keep User and Role)
        for (let i = existingHeaders.length - 1; i >= 2; i--) {
            existingHeaders[i].remove();
        }
        
        // Add permission headers
        matrixData.permissions.forEach(permission => {
            const th = document.createElement('th');
            th.textContent = permission.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            th.style.writingMode = 'vertical-rl';
            th.style.textOrientation = 'mixed';
            thead.appendChild(th);
        });

        // Build rows
        matrixData.users.forEach(user => {
            const row = document.createElement('tr');
            
            // User name
            const userCell = document.createElement('td');
            userCell.textContent = user.name;
            row.appendChild(userCell);
            
            // User role
            const roleCell = document.createElement('td');
            roleCell.textContent = user.role;
            row.appendChild(roleCell);
            
            // Permission cells
            matrixData.permissions.forEach(permission => {
                const permCell = document.createElement('td');
                const hasPermission = user.permissions.includes(permission);
                permCell.innerHTML = hasPermission ? 
                    '<i class="fas fa-check text-success"></i>' : 
                    '<i class="fas fa-times text-danger"></i>';
                row.appendChild(permCell);
            });
            
            tbody.appendChild(row);
        });
    }

    // Utility Functions
    loadPermissionData() {
        fetch('/api/all-permissions/')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.allPermissions = data.permissions;
                }
            })
            .catch(error => console.error('Error loading permission data:', error));
    }

    updateStatistics() {
        fetch('/api/privilege-statistics/')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('total-users-count').textContent = data.total_users;
                    document.getElementById('active-users-count').textContent = data.active_users || 0;
                    document.getElementById('total-permissions-count').textContent = data.total_permissions;
                    document.getElementById('active-roles-count').textContent = data.active_roles;
                    document.getElementById('granted-permissions-count').textContent = data.granted_permissions || 0;
                    document.getElementById('revoked-permissions-count').textContent = data.revoked_permissions || 0;
                }
            })
            .catch(error => console.error('Error loading statistics:', error));
    }

    // Grant Permission Function
    grantPermission(permission) {
        if (!this.selectedUserId) {
            this.showError('Please select a user first');
            return;
        }

        fetch('/api/grant-user-permission/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken(),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                user_id: this.selectedUserId,
                permission: permission
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showSuccess(data.message);
                // Update the checkbox
                const checkbox = document.getElementById(permission);
                if (checkbox) {
                    checkbox.checked = true;
                }
                this.handlePermissionChange();
                this.updateStatistics();
                // Reload user permissions to update summary
                this.loadUserPermissions(this.selectedUserId);
            } else {
                this.showError('Failed to grant permission: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error granting permission:', error);
            this.showError('Error granting permission');
        });
    }

    // Revoke Permission Function
    revokePermission(permission) {
        if (!this.selectedUserId) {
            this.showError('Please select a user first');
            return;
        }

        // Confirm revocation
        if (!confirm(`Are you sure you want to revoke the "${permission.replace(/_/g, ' ')}" permission?`)) {
            return;
        }

        fetch('/api/revoke-user-permission/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRFToken(),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                user_id: this.selectedUserId,
                permission: permission
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                this.showSuccess(data.message);
                // Update the checkbox
                const checkbox = document.getElementById(permission);
                if (checkbox) {
                    checkbox.checked = false;
                }
                this.handlePermissionChange();
                this.updateStatistics();
                // Reload user permissions to update summary
                this.loadUserPermissions(this.selectedUserId);
            } else {
                this.showError('Failed to revoke permission: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error revoking permission:', error);
            this.showError('Error revoking permission');
        });
    }

    refreshUserList() {
        // Reload the page to refresh user list
        window.location.reload();
    }

    setupUserCheckboxes() {
        document.querySelectorAll('.user-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => this.handleUserSelection(e));
        });
    }

    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showNotification(message, type) {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = `toast-notification ${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
                <span>${message}</span>
            </div>
        `;
        
        // Add styles
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#28a745' : '#dc3545'};
            color: white;
            padding: 15px 20px;
            border-radius: 5px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            z-index: 9999;
            animation: slideIn 0.3s ease;
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // Export Functions
    exportPermissions() {
        fetch('/api/export-permissions/')
            .then(response => response.blob())
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `permissions_export_${new Date().toISOString().split('T')[0]}.csv`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
            })
            .catch(error => {
                console.error('Error exporting permissions:', error);
                this.showError('Error exporting permissions');
            });
    }
}

// Initialize the privilege manager
let privilegeManager;
document.addEventListener('DOMContentLoaded', function() {
    privilegeManager = new EnhancedPrivilegeManager();
});

// Global functions for template usage
function selectUser(userId) {
    privilegeManager?.selectUser(userId);
}

function toggleCategoryPermissions(categoryId, selectAll) {
    privilegeManager?.toggleCategoryPermissions(categoryId, selectAll);
}

function savePermissions() {
    privilegeManager?.savePermissions();
}

function resetPermissions() {
    privilegeManager?.resetPermissions();
}

function applyRoleTemplate() {
    privilegeManager?.applyRoleTemplate();
}

function openBulkOperationsModal() {
    privilegeManager?.openBulkOperationsModal();
}

function executeBulkOperations() {
    privilegeManager?.executeBulkOperations();
}

function showPermissionMatrix() {
    privilegeManager?.showPermissionMatrix();
}

function exportPermissions() {
    privilegeManager?.exportPermissions();
}

function searchUsers() {
    privilegeManager?.searchUsers();
}

function filterUsersByRole() {
    privilegeManager?.filterUsersByRole();
}

function grantPermission(permission) {
    privilegeManager?.grantPermission(permission);
}

function revokePermission(permission) {
    privilegeManager?.revokePermission(permission);
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    
    .toast-content {
        display: flex;
        align-items: center;
        gap: 10px;
    }
`;
document.head.appendChild(style);

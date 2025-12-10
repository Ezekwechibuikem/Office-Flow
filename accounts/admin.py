from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Department, Unit, EmployeeSuspension


# ============================================================================
# DEPARTMENT ADMIN
# ============================================================================
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    """
    Admin interface for managing departments
    
    Features:
        - List view shows name, code, head, unit count, status
        - Can filter by active/inactive
        - Search by name or code
        - Shows timestamps in view mode only (readonly)
    """
    
    list_display = [
        'name',           # Department name
        'code',           # Short code (IT, HR, etc.)
        'head',           # Who leads this department
        'get_unit_count', # How many units in this dept
        'is_active'       # Active status
    ]
    
    list_filter = [
        'is_active',      # Filter by active/inactive
    ]
    
    search_fields = [
        'name',           # Search by name
        'code'            # Search by code
    ]
    
    readonly_fields = [
        'created_at',     # Can't edit creation time
        'updated_at'      # Can't edit update time
    ]
    
    fieldsets = (
        ('Department Info', {
            'fields': ('name', 'code', 'description')
        }),
        ('Leadership', {
            'fields': ('head',)
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )


# ============================================================================
# UNIT ADMIN
# ============================================================================
@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    """
    Admin interface for managing units within departments
    
    Features:
        - List view shows unit name, code, department, supervisor, status
        - Can filter by department and active status
        - Search by unit name, code, or department name
        - Organized by department then unit name
    """
    
    list_display = [
        'name',           # Unit name
        'code',           # Short code (NET, DEV, etc.)
        'department',     # Which department it belongs to
        'supervisor',     # Who supervises this unit
        'is_active'       # Active status
    ]
    
    list_filter = [
        'is_active',      # Filter by active/inactive
        'department'      # Filter by department
    ]
    
    search_fields = [
        'name',                # Search by unit name
        'code',                # Search by unit code
        'department__name'     # Search by department name (double underscore = foreign key lookup)
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('Unit Info', {
            'fields': ('name', 'code', 'department', 'description')
        }),
        ('Leadership', {
            'fields': ('supervisor',),
            'description': 'The person who supervises this unit'
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )


# ============================================================================
# EMPLOYEE SUSPENSION ADMIN
# ============================================================================
@admin.register(EmployeeSuspension)
class EmployeeSuspensionAdmin(admin.ModelAdmin):
    """
    Admin interface for managing employee suspensions
    
    Features:
        - List view shows employee, dates, who suspended them, status
        - Can filter by active status and dates
        - Search by employee name or email
        - Shows if suspension is currently active
    
    Important:
        - When creating suspension, employee_status automatically becomes 'SUSPENDED'
        - When suspension expires, status should be manually changed back to 'ACTIVE'
          (TODO: Add scheduled job to auto-update expired suspensions)
    """
    
    list_display = [
        'employee',            # Who is suspended
        'start_date',          # Suspension start
        'end_date',            # Suspension end
        'suspended_by',        # Who issued suspension
        'is_active',           # Active status
        'is_currently_active'  # Is it active TODAY?
    ]
    
    list_filter = [
        'is_active',           # Filter by active/inactive
        'start_date',          # Filter by start date
        'end_date'             # Filter by end date
    ]
    
    search_fields = [
        'employee__first_name',  # Search by employee first name
        'employee__last_name',   # Search by employee last name
        'employee__email'        # Search by employee email
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('Employee', {
            'fields': ('employee',),
            'description': 'Select the employee to suspend'
        }),
        ('Suspension Period', {
            'fields': ('start_date', 'end_date', 'reason'),
            'description': 'Set suspension dates and provide detailed reason'
        }),
        ('Administrative', {
            'fields': ('suspended_by', 'is_active'),
            'description': 'Who issued this suspension and current status'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)  # Collapsed by default
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """
        Override save to automatically set suspended_by to current user
        if not already set (when creating new suspension)
        """
        if not change:  # If creating new (not editing existing)
            if not obj.suspended_by:
                obj.suspended_by = request.user
        super().save_model(request, obj, form, change)


# ============================================================================
# CUSTOM USER ADMIN (YOUR EXISTING ONE - SLIGHTLY IMPROVED)
# ============================================================================
class CustomUserAdmin(UserAdmin):
    """
    Admin interface for managing users (employees)
    
    Features:
        - Email-based authentication (no username)
        - Comprehensive employee information organized in sections
        - Can filter by department, approval level, status, etc.
        - Search by email, name, employee ID, phone
        - Shows full name in list (not just email)
    
    Sections:
        - Authentication: Email, password
        - Personal Information: Name, DOB, contact, address
        - Professional Information: Employee ID, position, skills
        - Employment Details: Department, unit, contract type
        - Organizational Structure: Reports to, approval level
        - Financial Information: Bank details for payroll
        - Emergency Contact: Emergency contact details
        - Profile: Profile picture
        - Permissions: Django admin permissions
        - Important Dates: Timestamps
    """
    
    model = CustomUser
    
    # ========== LIST VIEW ==========
    list_display = [
        'email',             # Login email
        'get_full_name',     # Full name (method from model)
        'employee_id',       # Employee ID number
        'department',        # Which department (NOW shows Department object)
        'unit',              # Which unit (NOW shows Unit object)
        'position',          # Job title
        'approval_level',    # Approval authority
        'employee_status',   # Current status
        'is_active'          # Can login?
    ]
    
    # ========== FILTERS ==========
    list_filter = [
        'is_staff',          # Django admin access
        'is_active',         # Account active
        'department',        # Filter by department (NOW uses FK)
        'unit',              # Filter by unit (NOW uses FK)
        'approval_level',    # Filter by approval level
        'employee_status',   # Filter by status
        'contract_type'      # Filter by contract type
    ]
    
    # ========== SEARCH ==========
    search_fields = [
        'email',             # Search by email
        'first_name',        # Search by first name
        'last_name',         # Search by last name
        'employee_id',       # Search by employee ID
        'phone_number'       # Search by phone
    ]
    
    # ========== ORDERING ==========
    ordering = ['-created_at']  # Newest first
    
    # ========== VIEW/EDIT FORM ==========
    fieldsets = (
        ('Authentication', {
            'fields': ('email', 'work_email', 'password'),
            'description': 'Login credentials and work email'
        }),
        ('Personal Information', {
            'fields': (
                'first_name', 'middle_name', 'last_name', 
                'gender', 'date_of_birth', 'marital_status',
                'phone_number', 'alternate_phone',
                'address', 'city', 'state', 'country',
                'nationality', 'state_of_origin', 'religion'
            ),
            'description': 'Personal and contact information'
        }),
        ('Professional Information', {
            'fields': (
                'employee_id', 'position',
                'bio', 'skills', 'languages'
            ),
            'description': 'Job-related information and skills'
        }),
        ('Employment Details', {
            'fields': (
                'department', 'unit', 'contract_type',
                'date_joined', 'employee_status', 'work_schedule',
                'office_location'
            ),
            'description': 'Department, unit, and employment details'
        }),
        ('Organizational Structure', {
            'fields': ('reports_to', 'approval_level'),
            'description': 'Reporting structure and approval authority'
        }),
        ('Financial Information', {
            'fields': ('bank_name', 'account_number', 'account_name', 'tax_id'),
            'description': 'Bank details for payroll (will be used in payroll module)',
            'classes': ('collapse',)  # Collapsed by default for security
        }),
        ('Emergency Contact', {
            'fields': (
                'emergency_contact_name', 'emergency_contact_relationship',
                'emergency_contact_phone', 'emergency_contact_address'
            ),
            'description': 'Emergency contact information'
        }),
        ('Profile', {
            'fields': ('profile_picture',),
            'description': 'Profile photo'
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'description': 'Django admin and system permissions',
            'classes': ('collapse',)  # Collapsed by default
        }),
        ('Important Dates', {
            'fields': ('last_login', 'created_at', 'updated_at'),
            'description': 'Account activity timestamps',
            'classes': ('collapse',)  # Collapsed by default
        }),
    )
    
    # ========== ADD NEW USER FORM ==========
    # Simplified form when creating a new user
    add_fieldsets = (
        ('Required Information', {
            'classes': ('wide',),
            'fields': (
                'email',           # Email (for login)
                'first_name',      # First name
                'last_name',       # Last name
                'password1',       # Password
                'password2'        # Password confirmation
            ),
            'description': 'Basic information required to create an account'
        }),
        ('Employee Details', {
            'classes': ('wide',),
            'fields': (
                'employee_id',     # Employee ID
                'department',      # Department (FK)
                'unit',            # Unit (FK)
                'position'         # Job title
            ),
            'description': 'Employment information'
        }),
        ('Permissions', {
            'classes': ('wide',),
            'fields': (
                'is_staff',        # Can access admin

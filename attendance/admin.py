from django.contrib import admin
from django.utils.html import format_html
from .models import Holiday, AttendanceSettings, Attendance, AttendanceApprovalRequest


# ============================================================================
# HOLIDAY ADMIN
# ============================================================================
@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    """
    Admin interface for managing public holidays
    
    Features:
        - List view shows holiday name, date, and active status
        - Can filter by active status and year
        - Search by holiday name
        - Ordered by most recent date first
    
    Usage:
        - Add holidays like Independence Day, Christmas, Eid, etc.
        - On these days, employees cannot clock in
        - Attendance status automatically becomes 'HOLIDAY'
    """
    
    list_display = [
        'name',           # Holiday name
        'date',           # Holiday date
        'is_active',      # Active status
        'created_at'      # When added
    ]
    
    list_filter = [
        'is_active',      # Filter by active/inactive
        'date'            # Filter by year
    ]
    
    search_fields = [
        'name',           # Search by holiday name
        'description'     # Search in description
    ]
    
    ordering = ['-date']  # Most recent first
    
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Holiday Information', {
            'fields': ('name', 'date', 'description'),
            'description': 'Add public holidays when no work is expected'
        }),
        ('Status', {
            'fields': ('is_active', 'created_at')
        }),
    )
    
    # Add quick action to activate/deactivate multiple holidays
    actions = ['activate_holidays', 'deactivate_holidays']
    
    def activate_holidays(self, request, queryset):
        """Bulk activate selected holidays"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} holiday(s) activated.')
    activate_holidays.short_description = "Activate selected holidays"
    
    def deactivate_holidays(self, request, queryset):
        """Bulk deactivate selected holidays"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} holiday(s) deactivated.')
    deactivate_holidays.short_description = "Deactivate selected holidays"


# ============================================================================
# ATTENDANCE SETTINGS ADMIN
# ============================================================================
@admin.register(AttendanceSettings)
class AttendanceSettingsAdmin(admin.ModelAdmin):
    """
    Admin interface for attendance configuration
    
    Features:
        - Configure work hours (9am - 5pm)
        - Set clock-in deadline (9:00 AM)
        - Set clock-out deadline (6:01 PM)
        - Enable/disable enforcement rules
    
    IMPORTANT:
        - Only ONE settings record should be active at a time
        - All attendance records follow these settings
        - Changes apply to new attendance records immediately
    """
    
    list_display = [
        'work_start_time',              # Clock-in deadline
        'work_end_time',                # Standard end time
        'clock_out_deadline',           # Clock-out deadline
        'standard_work_hours',          # Expected hours per day
        'is_active',                    # Active status
        'updated_at'                    # Last modified
    ]
    
    list_filter = [
        'is_active',
    ]
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Work Time Configuration', {
            'fields': (
                'work_start_time',
                'work_end_time',
                'clock_out_deadline',
                'standard_work_hours'
            ),
            'description': '''
                <strong>Important:</strong><br>
                - <strong>Work Start Time:</strong> Clock-in deadline (e.g., 09:00 AM)<br>
                - <strong>Work End Time:</strong> Standard work end (e.g., 05:00 PM)<br>
                - <strong>Clock-out Deadline:</strong> Must clock out by this time (e.g., 06:01 PM)<br>
                - <strong>Standard Work Hours:</strong> Expected hours per day (e.g., 8.00)
            '''
        }),
        ('Enforcement Rules', {
            'fields': (
                'auto_mark_absent_after_deadline',
                'require_clock_out'
            ),
            'description': 'Configure automatic marking rules'
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )
    
    def has_add_permission(self, request):
        """
        Limit to only one active settings record
        If active settings exist, don't allow creating new one
        """
        if AttendanceSettings.objects.filter(is_active=True).exists():
            return False
        return super().has_add_permission(request)


# ============================================================================
# ATTENDANCE ADMIN
# ============================================================================
@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    """
    Admin interface for viewing and managing attendance records
    
    Features:
        - View all attendance records with status colors
        - Filter by date, status, department, unit
        - Search by employee name or ID
        - View hours worked and approval status
        - Can manually edit if needed (with caution)
    
    Color Coding:
        - PRESENT: Green
        - ABSENT: Red
        - ON_LEAVE: Blue
        - WEEKEND: Gray
        - HOLIDAY: Purple
        - SUSPENDED: Orange
    """
    
    list_display = [
        'employee',                     # Employee name
        'date',                         # Attendance date
        'clock_in_time',                # Clock-in time
        'clock_out_time',               # Clock-out time
        'hours_worked',                 # Hours worked
        'colored_status',               # Status with color
        'has_pending_approval_request'  # Pending request?
    ]
    
    list_filter = [
        'employeeDayStatus',            # Filter by status
        'date',                         # Filter by date
        'employee__department',         # Filter by department
        'employee__unit',               # Filter by unit
        'has_pending_approval_request'  # Filter by pending requests
    ]
    
    search_fields = [
        'employee__first_name',         # Search by first name
        'employee__last_name',          # Search by last name
        'employee__email',              # Search by email
        'employee__employee_id'         # Search by employee ID
    ]
    
    ordering = ['-date', 'employee']    # Most recent first, then by employee
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'hours_worked'                  # Auto-calculated, shouldn't edit manually
    ]
    
    fieldsets = (
        ('Employee & Date', {
            'fields': ('employee', 'date')
        }),
        ('Clock Times', {
            'fields': ('clock_in_time', 'clock_out_time'),
            'description': 'Employee clock-in and clock-out times'
        }),
        ('Status & Hours', {
            'fields': ('employeeDayStatus', 'hours_worked', 'has_pending_approval_request'),
            'description': 'Auto-calculated status and hours worked'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def colored_status(self, obj):
        """
        Display status with color coding for easy visual identification
        
        Colors:
            - PRESENT: Green (success)
            - ABSENT: Red (danger)
            - ON_LEAVE: Blue (info)
            - WEEKEND: Gray (secondary)
            - HOLIDAY: Purple (warning variant)
            - SUSPENDED: Orange (warning)
        """
        colors = {
            'PRESENT': '#28a745',    # Green
            'ABSENT': '#dc3545',     # Red
            'ON_LEAVE': '#007bff',   # Blue
            'WEEKEND': '#6c757d',    # Gray
            'HOLIDAY': '#6f42c1',    # Purple
            'SUSPENDED': '#fd7e14'   # Orange
        }
        color = colors.get(obj.employeeDayStatus, '#000000')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_employeeDayStatus_display()  # Get display name from choices
        )
    colored_status.short_description = 'Status'
    
    def get_queryset(self, request):
        """
        Optimize queries by selecting related employee data
        Prevents N+1 query problem
        """
        queryset = super().get_queryset(request)
        queryset = queryset.select_related('employee', 'employee__department', 'employee__unit')
        return queryset
    
    # Quick actions for bulk operations
    actions = ['mark_as_present', 'export_to_csv']
    
    def mark_as_present(self, request, queryset):
        """
        Bulk action to mark selected attendance records as PRESENT
        Use with caution - should normally go through approval workflow
        """
        # Only allow for superusers or HR_ADMIN
        if not request.user.is_superuser and request.user.approval_level != 'HR_ADMIN':
            self.message_user(request, 'Only HR Admin can bulk mark as present.', level='error')
            return
        
        updated = queryset.update(employeeDayStatus='PRESENT')
        self.message_user(request, f'{updated} record(s) marked as PRESENT.')
    mark_as_present.short_description = "Mark selected as PRESENT (HR only)"


# ============================================================================
# ATTENDANCE APPROVAL REQUEST ADMIN
# ============================================================================
@admin.register(AttendanceApprovalRequest)
class AttendanceApprovalRequestAdmin(admin.ModelAdmin):
    """
    Admin interface for reviewing attendance approval requests
    
    Three-tier approval workflow:
        1. Employee submits request (PENDING)
        2. Supervisor reviews (SUPERVISOR_APPROVED or REJECTED)
        3. HR reviews (HR_APPROVED or REJECTED)
    
    Features:
        - View all requests with color-coded status
        - Filter by status, employee, date
        - Separate views for supervisor and HR reviews
        - Can view supporting documents
        - Shows full approval trail (who approved when)
    """
    
    list_display = [
        'employee',                 # Who submitted
        'attendance_date',          # Which date
        'colored_status',           # Request status with color
        'supervisor_info',          # Supervisor review info
        'hr_info',                  # HR review info
        'created_at'                # When submitted
    ]
    
    list_filter = [
        'status',                   # Filter by status
        'attendance__date',         # Filter by attendance date
        'created_at'                # Filter by submission date
    ]
    
    search_fields = [
        'employee__first_name',     # Search by first name
        'employee__last_name',      # Search by last name
        'employee__email',          # Search by email
        'reason'                    # Search in reason text
    ]
    
    ordering = ['-created_at']      # Most recent first
    
    readonly_fields = [
        'employee',
        'attendance',
        'reason',
        'supporting_documents',
        'supervisor_reviewed_by',
        'supervisor_review_notes',
        'supervisor_reviewed_at',
        'hr_reviewed_by',
        'hr_review_notes',
        'hr_reviewed_at',
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        ('Request Details', {
            'fields': (
                'employee',
                'attendance',
                'reason',
                'supporting_documents',
                'status'
            ),
            'description': 'Employee request to change ABSENT to PRESENT'
        }),
        ('Supervisor Review', {
            'fields': (
                'supervisor_reviewed_by',
                'supervisor_review_notes',
                'supervisor_reviewed_at'
            ),
            'description': 'First-level approval by unit supervisor'
        }),
        ('HR Review', {
            'fields': (
                'hr_reviewed_by',
                'hr_review_notes',
                'hr_reviewed_at'
            ),
            'description': 'Final approval by HR Admin (marks attendance PRESENT)'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def attendance_date(self, obj):
        """Display the attendance date instead of full attendance object"""
        return obj.attendance.date
    attendance_date.short_description = 'Attendance Date'
    attendance_date.admin_order_field = 'attendance__date'  # Allow sorting
    
    def colored_status(self, obj):
        """
        Display status with color coding
        
        Colors:
            - PENDING: Orange (awaiting supervisor)
            - SUPERVISOR_APPROVED: Blue (awaiting HR)
            - HR_APPROVED: Green (approved, marked present)
            - REJECTED: Red (denied)
        """
        colors = {
            'PENDING': '#fd7e14',               # Orange
            'SUPERVISOR_APPROVED': '#007bff',   # Blue
            'HR_APPROVED': '#28a745',           # Green
            'REJECTED': '#dc3545'               # Red
        }
        color = colors.get(obj.status, '#000000')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    colored_status.short_description = 'Status'
    
    def supervisor_info(self, obj):
        """Display supervisor review information in compact format"""
        if obj.supervisor_reviewed_by:
            return format_html(
                '{}<br><small style="color: gray;">{}</small>',
                obj.supervisor_reviewed_by.get_short_name(),
                obj.supervisor_reviewed_at.strftime('%Y-%m-%d %H:%M') if obj.supervisor_reviewed_at else '-'
            )
        return '-'
    supervisor_info.short_description = 'Supervisor Review'
    
    def hr_info(self, obj):
        """Display HR review information in compact format"""
        if obj.hr_reviewed_by:
            return format_html(
                '{}<br><small style="color: gray;">{}</small>',
                obj.hr_reviewed_by.get_short_name(),
                obj.hr_reviewed_at.strftime('%Y-%m-%d %H:%M') if obj.hr_reviewed_at else '-'
            )
        return '-'
    hr_info.short_description = 'HR Review'
    
    def get_queryset(self, request):
        """
        Optimize queries and filter based on user role
        
        Rules:
            - Superuser: See all requests
            - HR_ADMIN: See all requests
            - Supervisor: See only requests from their unit (PENDING status)
            - Regular user: See only their own requests
        """
        queryset = super().get_queryset(request)
        queryset = queryset.select_related(
            'employee',
            'attendance',
            'supervisor_reviewed_by',
            'hr_reviewed_by'
        )
        
        # If superuser or HR, show all
        if request.user.is_superuser or request.user.approval_level == 'HR_ADMIN':
            return queryset
        
        # If supervisor, show pending requests from their unit
        if request.user.approval_level == 'SUPERVISOR':
            if hasattr(request.user, 'unit_supervised'):
                # Show requests from employees in supervised unit
                return queryset.filter(
                    employee__unit=request.user.unit_supervised,
                    status='PENDING'
                )
        
        # Regular users see only their own requests
        return queryset.filter(employee=request.user)
    
    def has_change_permission(self, request, obj=None):
        """
        Control who can edit/review requests
        
        Rules:
            - Superuser: Can edit anything
            - HR_ADMIN: Can edit anything
            - Supervisor: Can only approve/reject PENDING requests from their unit
            - Regular user: Cannot edit (read-only)
        """
        if request.user.is_superuser:
            return True
        
        if request.user.approval_level == 'HR_ADMIN':
            return True
        
        if request.user.approval_level == 'SUPERVISOR' and obj:
            # Check if this request is from their unit and pending
            if hasattr(request.user, 'unit_supervised'):
                return (
                    obj.employee.unit == request.user.unit_supervised and
                    obj.status == 'PENDING'
                )
        
        return False
    
    # Quick filters for common views
    def changelist_view(self, request, extra_context=None):
        """Add custom filters to change list view"""
        extra_context = extra_context or {}
        
        # Add counts for each status
        from django.db.models import Count
        status_counts = AttendanceApprovalRequest.objects.values('status').annotate(count=Count('id'))
        extra_context['status_counts'] = {item['status']: item['count'] for item in status_counts}
        
        return super().changelist_view(request, extra_context)


# ============================================================================
# CUSTOMIZE ADMIN SITE HEADER
# ============================================================================
admin.site.site_header = "Office-Flow HR Management"
admin.site.site_title = "Office-Flow Admin"
admin.site.index_title = "Welcome to Office-Flow HR System"
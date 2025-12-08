from django.contrib import admin
from django.utils.html import format_html
from .models import Holiday, AttendanceSettings, Attendance, AttendanceApprovalRequest


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ['name', 'date', 'is_active', 'created_at']
    list_filter = ['is_active', 'date']
    search_fields = ['name', 'description']
    ordering = ['-date']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Holiday Information', {
            'fields': ('name', 'date', 'description')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at')
        }),
    )
    
    actions = ['activate_holidays', 'deactivate_holidays']
    
    def activate_holidays(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} holiday(s) activated.')
    activate_holidays.short_description = "Activate selected holidays"
    
    def deactivate_holidays(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} holiday(s) deactivated.')
    deactivate_holidays.short_description = "Deactivate selected holidays"


@admin.register(AttendanceSettings)
class AttendanceSettingsAdmin(admin.ModelAdmin):
    list_display = ['work_start_time', 'work_end_time', 'clock_out_deadline', 'standard_work_hours', 'is_active', 'updated_at']
    list_filter = ['is_active']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Work Time Configuration', {
            'fields': ('work_start_time', 'work_end_time', 'clock_out_deadline', 'standard_work_hours')
        }),
        ('Enforcement Rules', {
            'fields': ('auto_mark_absent_after_deadline', 'require_clock_out')
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )
    
    def has_add_permission(self, request):
        if AttendanceSettings.objects.filter(is_active=True).exists():
            return False
        return super().has_add_permission(request)


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'clock_in_time', 'clock_out_time', 'hours_worked', 'colored_status', 'has_pending_approval_request']
    list_filter = ['employeeDayStatus', 'date', 'employee__department', 'employee__unit', 'has_pending_approval_request']
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__email', 'employee__employee_id']
    ordering = ['-date', 'employee']
    readonly_fields = ['created_at', 'updated_at', 'hours_worked']
    
    fieldsets = (
        ('Employee & Date', {
            'fields': ('employee', 'date')
        }),
        ('Clock Times', {
            'fields': ('clock_in_time', 'clock_out_time')
        }),
        ('Status & Hours', {
            'fields': ('employeeDayStatus', 'hours_worked', 'has_pending_approval_request')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def colored_status(self, obj):
        colors = {
            'PRESENT': '#28a745',
            'ABSENT': '#dc3545',
            'ON_LEAVE': '#007bff',
            'WEEKEND': '#6c757d',
            'HOLIDAY': '#6f42c1',
            'SUSPENDED': '#fd7e14'
        }
        color = colors.get(obj.employeeDayStatus, '#000000')
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.get_employeeDayStatus_display())
    colored_status.short_description = 'Status'
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.select_related('employee', 'employee__department', 'employee__unit')
        return queryset
    
    actions = ['mark_as_present']
    
    def mark_as_present(self, request, queryset):
        if not request.user.is_superuser and request.user.approval_level != 'HR_ADMIN':
            self.message_user(request, 'Only HR Admin can bulk mark as present.', level='error')
            return
        updated = queryset.update(employeeDayStatus='PRESENT')
        self.message_user(request, f'{updated} record(s) marked as PRESENT.')
    mark_as_present.short_description = "Mark selected as PRESENT (HR only)"


@admin.register(AttendanceApprovalRequest)
class AttendanceApprovalRequestAdmin(admin.ModelAdmin):
    list_display = ['employee', 'attendance_date', 'colored_status', 'supervisor_info', 'hr_info', 'created_at']
    list_filter = ['status', 'attendance__date', 'created_at']
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__email', 'reason']
    ordering = ['-created_at']
    readonly_fields = ['employee', 'attendance', 'reason', 'supporting_documents', 'supervisor_reviewed_by', 'supervisor_review_notes', 'supervisor_reviewed_at', 'hr_reviewed_by', 'hr_review_notes', 'hr_reviewed_at', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Request Details', {
            'fields': ('employee', 'attendance', 'reason', 'supporting_documents', 'status')
        }),
        ('Supervisor Review', {
            'fields': ('supervisor_reviewed_by', 'supervisor_review_notes', 'supervisor_reviewed_at')
        }),
        ('HR Review', {
            'fields': ('hr_reviewed_by', 'hr_review_notes', 'hr_reviewed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def attendance_date(self, obj):
        return obj.attendance.date
    attendance_date.short_description = 'Attendance Date'
    attendance_date.admin_order_field = 'attendance__date'
    
    def colored_status(self, obj):
        colors = {
            'PENDING': '#fd7e14',
            'SUPERVISOR_APPROVED': '#007bff',
            'HR_APPROVED': '#28a745',
            'REJECTED': '#dc3545'
        }
        color = colors.get(obj.status, '#000000')
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.get_status_display())
    colored_status.short_description = 'Status'
    
    def supervisor_info(self, obj):
        if obj.supervisor_reviewed_by:
            return format_html('{}<br><small style="color: gray;">{}</small>', obj.supervisor_reviewed_by.get_short_name(), obj.supervisor_reviewed_at.strftime('%Y-%m-%d %H:%M') if obj.supervisor_reviewed_at else '-')
        return '-'
    supervisor_info.short_description = 'Supervisor Review'
    
    def hr_info(self, obj):
        if obj.hr_reviewed_by:
            return format_html('{}<br><small style="color: gray;">{}</small>', obj.hr_reviewed_by.get_short_name(), obj.hr_reviewed_at.strftime('%Y-%m-%d %H:%M') if obj.hr_reviewed_at else '-')
        return '-'
    hr_info.short_description = 'HR Review'
    
    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.select_related('employee', 'attendance', 'supervisor_reviewed_by', 'hr_reviewed_by')
        if request.user.is_superuser or request.user.approval_level == 'HR_ADMIN':
            return queryset
        if request.user.approval_level == 'SUPERVISOR':
            if hasattr(request.user, 'unit_supervised'):
                return queryset.filter(employee__unit=request.user.unit_supervised, status='PENDING')
        return queryset.filter(employee=request.user)
    
    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if request.user.approval_level == 'HR_ADMIN':
            return True
        if request.user.approval_level == 'SUPERVISOR' and obj:
            if hasattr(request.user, 'unit_supervised'):
                return obj.employee.unit == request.user.unit_supervised and obj.status == 'PENDING'
        return False


admin.site.site_header = "Office-Flow HR Management"
admin.site.site_title = "Office-Flow Admin"
admin.site.index_title = "Welcome to Office-Flow HR System"
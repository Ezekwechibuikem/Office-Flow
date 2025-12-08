from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Department, Unit, EmployeeSuspension


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'head', 'get_unit_count', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    readonly_fields = ['created_at', 'updated_at']
    
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


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'department', 'supervisor', 'is_active']
    list_filter = ['is_active', 'department']
    search_fields = ['name', 'code', 'department__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Unit Info', {
            'fields': ('name', 'code', 'department', 'description')
        }),
        ('Leadership', {
            'fields': ('supervisor',)
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )


@admin.register(EmployeeSuspension)
class EmployeeSuspensionAdmin(admin.ModelAdmin):
    list_display = ['employee', 'start_date', 'end_date', 'suspended_by', 'is_active', 'is_currently_active']
    list_filter = ['is_active', 'start_date', 'end_date']
    search_fields = ['employee__first_name', 'employee__last_name', 'employee__email']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Employee', {
            'fields': ('employee',)
        }),
        ('Suspension Period', {
            'fields': ('start_date', 'end_date', 'reason')
        }),
        ('Administrative', {
            'fields': ('suspended_by', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            if not obj.suspended_by:
                obj.suspended_by = request.user
        super().save_model(request, obj, form, change)


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['email', 'get_full_name', 'employee_id', 'department', 'unit', 'position', 'approval_level', 'employee_status', 'is_active']
    list_filter = ['is_staff', 'is_active', 'department', 'unit', 'approval_level', 'employee_status', 'contract_type']
    search_fields = ['email', 'first_name', 'last_name', 'employee_id', 'phone_number']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Authentication', {
            'fields': ('email', 'work_email', 'password')
        }),
        ('Personal Information', {
            'fields': (
                'first_name', 'middle_name', 'last_name', 
                'gender', 'date_of_birth', 'marital_status',
                'phone_number', 'alternate_phone',
                'address', 'city', 'state', 'country',
                'nationality', 'state_of_origin', 'religion'
            )
        }),
        ('Professional Information', {
            'fields': (
                'employee_id', 'position',
                'bio', 'skills', 'languages'
            )
        }),
        ('Employment Details', {
            'fields': (
                'department', 'unit', 'contract_type',
                'date_joined', 'employee_status', 'work_schedule',
                'office_location'
            )
        }),
        ('Organizational Structure', {
            'fields': ('reports_to', 'approval_level')
        }),
        ('Financial Information', {
            'fields': ('bank_name', 'account_number', 'account_name', 'tax_id'),
            'classes': ('collapse',)
        }),
        ('Emergency Contact', {
            'fields': (
                'emergency_contact_name', 'emergency_contact_relationship',
                'emergency_contact_phone', 'emergency_contact_address'
            )
        }),
        ('Profile', {
            'fields': ('profile_picture',)
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('last_login', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        ('Required Information', {
            'classes': ('wide',),
            'fields': (
                'email',
                'first_name',
                'last_name',
                'password1',
                'password2'
            )
        }),
        ('Employee Details', {
            'classes': ('wide',),
            'fields': (
                'employee_id',
                'department',
                'unit',
                'position'
            )
        }),
        ('Permissions', {
            'classes': ('wide',),
            'fields': (
                'is_staff',
                'is_active',
                'approval_level'
            )
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'last_login']


admin.site.register(CustomUser, CustomUserAdmin)
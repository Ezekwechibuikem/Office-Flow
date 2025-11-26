from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['email', 'get_full_name', 'employee_id', 'department', 'position', 'approval_level', 'employee_status', 'is_active']
    list_filter = ['is_staff', 'is_active', 'department', 'approval_level', 'employee_status', 'contract_type']
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
                'nationality', 'state_of_origin', 'religion', 
            )
        }),
        ('Professional Information', {
            'fields': (
                'employee_id', 'position', 'level',
                'bio', 'skills', 'languages'
            )
        }),
        ('Employment Details', {
            'fields': (
                'department', 'unit', 'contract_type',
                'date_joined', 'employee_status', 'work_schedule',
                'office_location',
            )
        }),
        ('Organizational Structure', {
            'fields': ('reports_to', 'approval_level')
        }),
        ('Financial Information', {
            'fields': ('bank_name', 'account_number', 'account_name', 'tax_id')
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
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Important Dates', {
            'fields': ('last_login', 'created_at', 'updated_at')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'first_name', 'last_name', 
                'employee_id', 'department', 'position',
                'password1', 'password2', 
                'is_staff', 'is_active', 'approval_level'
            )}
        ),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'last_login']


admin.site.register(CustomUser, CustomUserAdmin)
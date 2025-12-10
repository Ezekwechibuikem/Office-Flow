from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError


class CustomUserManager(BaseUserManager):
    """
    Custom manager for email-based authentication
    """
    def create_user(self, email, password=None, **extra_fields):
        
        if not email:
            raise ValueError('Email address is required')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
       
        extra_fields.setdefault('is_staff', True)       
        extra_fields.setdefault('is_superuser', True)   
        extra_fields.setdefault('is_active', True)      
        extra_fields.setdefault('approval_level', 'DIRECTOR')  
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True')
        
        return self.create_user(email, password, **extra_fields)
    
    
class Department(models.Model):
  
    name = models.CharField(
        max_length=100, 
        unique=True, 
        verbose_name='Department Name',
        help_text='e.g., Information Technology, Human Resources'
    )
    code = models.CharField(
        max_length=20, 
        unique=True, 
        verbose_name='Department Code',
        help_text='Short code: IT, HR, FIN, MKT'
    )
    
    description = models.TextField(
        blank=True, 
        null=True, 
        verbose_name='Description',
        help_text='Brief description of department responsibilities'
    )
   
    head = models.OneToOneField(
        'CustomUser',  
        on_delete=models.SET_NULL,  
        null=True,
        blank=True,
        related_name='department_headed',
        verbose_name='Department Head',
        help_text='The person who leads this department'
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name='Active',
        help_text='Inactive departments are hidden from selection'
    )
    created_at = models.DateTimeField(auto_now_add=True) 
    updated_at = models.DateTimeField(auto_now=True)      
    
    class Meta:
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'
        ordering = ['name']  
    
    def __str__(self):
        """String representation shown in admin and dropdowns"""
        return self.name
    
    def get_all_employees(self):
        """Get all employees assigned to this department"""
        return CustomUser.objects.filter(department=self)
    
    def get_unit_count(self):
        """Count how many units are in this department"""
        return self.units.count()  

class Unit(models.Model):
    
    name = models.CharField(max_length=100, verbose_name='Unit Name', help_text='e.g., Network Team, Backend Development, Quality Assurance')
    code = models.CharField(max_length=20, verbose_name='Unit Code', help_text='Short code: NET, DEV, QA, SUP')
    
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='units', verbose_name='Department')
    description = models.TextField(blank=True, null=True, verbose_name='Description', help_text='Brief description of unit responsibilities')
    supervisor = models.OneToOneField('CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='unit_supervised', verbose_name='Unit Supervisor', help_text='The person who supervises this unit')
    is_active = models.BooleanField(default=True, verbose_name='Active', help_text='Inactive units are hidden from selection')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Unit'
        verbose_name_plural = 'Units'
        ordering = ['department', 'name'] 
        unique_together = ['department', 'name']  
    
    def __str__(self):
        """Show as: IT Department - Network Unit"""
        return f"{self.department.name} - {self.name}"
    
    def get_all_employees(self):
        """Get all employees assigned to this unit"""
        return CustomUser.objects.filter(unit=self)

class EmployeeSuspension(models.Model):
    """
    Records of employee suspensions
    """
    employee = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='suspensions', verbose_name='Employee')
    
    start_date = models.DateField(verbose_name='Suspension Start Date', help_text='First day of suspension')
    end_date = models.DateField(verbose_name='Suspension End Date', help_text='Last day of suspension (inclusive)')
    reason = models.TextField(verbose_name='Suspension Reason', help_text='Detailed explanation of why employee is suspended')
    suspended_by = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True, related_name='suspensions_issued', verbose_name='Suspended By', help_text='HR or manager who issued the suspension')
    is_active = models.BooleanField(default=True, verbose_name='Active', help_text='Set to False to cancel suspension')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Employee Suspension'
        verbose_name_plural = 'Employee Suspensions'
        ordering = ['-start_date']  
    
    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.start_date} to {self.end_date}"
    
    def clean(self):
       
        if self.end_date < self.start_date:
            raise ValidationError("End date must be after start date")
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Update employee status if suspension is currently active
        if self.is_active:
            today = timezone.now().date()
            # Check if today falls within suspension period
            if self.start_date <= today <= self.end_date:
                self.employee.employee_status = 'SUSPENDED'
                self.employee.save()
    
    def is_currently_active(self):
        """
        Check if this suspension is active RIGHT NOW
        Returns True if today is between start_date and end_date
        """
        today = timezone.now().date()
        return self.is_active and self.start_date <= today <= self.end_date


class CustomUser(AbstractBaseUser, PermissionsMixin):
    
    # ========== AUTHENTICATION ==========
    email = models.EmailField(
        unique=True, 
        verbose_name='Email Address',
        help_text='Used for login - must be unique'
    )
    
    work_email = models.EmailField(
        blank=True, 
        null=True, 
        verbose_name='Work Email (if different)',
        help_text='Company email if different from login email'
    )
    
    first_name = models.CharField(max_length=50, verbose_name='First Name')
    last_name = models.CharField(max_length=50, verbose_name='Last Name')
    middle_name = models.CharField(max_length=50, blank=True, null=True, verbose_name='Middle Name')
    
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]
    gender = models.CharField(
        max_length=1, 
        choices=GENDER_CHOICES, 
        blank=True, 
        null=True, 
        verbose_name='Gender'
    )
    
    date_of_birth = models.DateField(blank=True, null=True, verbose_name='Date of Birth')
    
    MARITAL_STATUS_CHOICES = [
        ('SINGLE', 'Single'),
        ('MARRIED', 'Married'),
        ('DIVORCED', 'Divorced'),
        ('WIDOWED', 'Widowed'),
    ]
    marital_status = models.CharField(
        max_length=10, 
        choices=MARITAL_STATUS_CHOICES, 
        blank=True, 
        null=True, 
        verbose_name='Marital Status'
    )
    
    # Contact Information
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name='Phone Number')
    alternate_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='Alternate Phone')
    
    # Address Information
    address = models.TextField(blank=True, null=True, verbose_name='Residential Address')
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name='City')
    state = models.CharField(max_length=100, blank=True, null=True, verbose_name='State')
    country = models.CharField(max_length=100, default='Nigeria', verbose_name='Country')
    
    # Origin Information
    nationality = models.CharField(max_length=100, blank=True, null=True, verbose_name='Nationality')
    state_of_origin = models.CharField(max_length=100, blank=True, null=True, verbose_name='State of Origin')
    religion = models.CharField(max_length=50, blank=True, null=True, verbose_name='Religion')
    
    # ========== PROFESSIONAL INFORMATION ==========
    employee_id = models.CharField(
        max_length=20, 
        unique=True, 
        blank=True, 
        null=True, 
        verbose_name='Employee ID',
        help_text='Unique employee identification number'
    )
    
    position = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        verbose_name='Job Title/Position',
        help_text='e.g., Senior Software Engineer, HR Manager'
    )
    
    LEVEL_CHOICES = [
        ('JUNIOR', 'Junior'),
        ('MID', 'Mid-Level'),
        ('SENIOR', 'Senior'),
        ('LEAD', 'Lead'),
        ('PRINCIPAL', 'Principal'),
    ]
    level = models.CharField(
        max_length=20, 
        choices=LEVEL_CHOICES, 
        blank=True, 
        null=True, 
        verbose_name='Professional Level'
    )
    
    # Additional Professional Info
    bio = models.TextField(
        blank=True, 
        null=True, 
        verbose_name='Bio/About', 
        help_text='Brief professional description'
    )
    
    skills = models.TextField(
        blank=True, 
        null=True, 
        verbose_name='Skills', 
        help_text='Comma-separated list of skills (e.g., Python, Django, PostgreSQL)'
    )
    
    languages = models.CharField(
        max_length=200, 
        blank=True, 
        null=True, 
        verbose_name='Languages Spoken', 
        help_text='e.g., English, Hausa, Yoruba, Igbo'
    )
    
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,  
        null=True,
        blank=True,
        related_name='employees',  
        verbose_name='Department'
    )
    
    unit = models.ForeignKey(
        Unit,
        on_delete=models.SET_NULL,  
        null=True,
        blank=True,
        related_name='employees',  
        verbose_name='Unit/Team'
    )
    
    CONTRACT_TYPE_CHOICES = [
        ('PERMANENT', 'Permanent'),
        ('CONTRACT', 'Contract'),
        ('INTERN', 'Intern'),
        ('PART_TIME', 'Part-Time'),
        ('TEMPORARY', 'Temporary'),
    ]
    contract_type = models.CharField(
        max_length=20, 
        choices=CONTRACT_TYPE_CHOICES, 
        default='PERMANENT', 
        verbose_name='Contract Type'
    )
    
    date_joined = models.DateField(
        default=timezone.now, 
        verbose_name='Date Joined Company',
        help_text='Employee hire date'
    )
    
    EMPLOYEE_STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('ON_LEAVE', 'On Leave'),
        ('SUSPENDED', 'Suspended'),
        ('TERMINATED', 'Terminated'),
        ('RESIGNED', 'Resigned'),
    ]
    employee_status = models.CharField(
        max_length=20, 
        choices=EMPLOYEE_STATUS_CHOICES, 
        default='ACTIVE', 
        verbose_name='Employee Status',
        help_text='Current employment status - affects attendance'
    )
    
    WORK_SCHEDULE_CHOICES = [
        ('SHIFTS', 'Shift-based'),
        ('REMOTE', 'Remote'),
        ('HYBRID', 'Hybrid'),
        ('FLEXIBLE', 'Flexible'),
    ]
    work_schedule = models.CharField(
        max_length=20, 
        choices=WORK_SCHEDULE_CHOICES, 
        default='HYBRID', 
        verbose_name='Work Schedule'
    )
    
    office_location = models.CharField(
        max_length=200, 
        blank=True, 
        null=True, 
        verbose_name='Office Location',
        help_text='Physical office location if applicable'
    )
    
    # ========== ORGANIZATIONAL STRUCTURE ==========
    # CRITICAL: Defines who reports to whom
    # Used for approval workflows and org chart
    reports_to = models.ForeignKey(
        'self',  # References another CustomUser (manager/supervisor)
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subordinates',  # Allows: manager.subordinates.all()
        verbose_name='Reports To (Manager/Supervisor)',
        help_text='Direct manager/supervisor'
    )
    
    # CRITICAL: Defines approval authority level
    # Used in attendance approval workflow
    APPROVAL_LEVEL_CHOICES = [
        ('STAFF', 'Staff (No Approval Power)'),
        ('SUPERVISOR', 'Supervisor'),
        ('DEPT_HEAD', 'Department Head'),
        ('DEPUTY_DIR', 'Deputy Director'),
        ('DIRECTOR', 'Director'),
        ('HR_ADMIN', 'HR Admin'),
        ('IT_ADMIN', 'IT Admin'),
    ]
    approval_level = models.CharField(
        max_length=20, 
        choices=APPROVAL_LEVEL_CHOICES, 
        default='STAFF',
        verbose_name='Approval Level',
        help_text='Determines what the user can approve'
    )
    
    # ========== FINANCIAL INFORMATION ==========
    # For payroll module (future implementation)
    bank_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='Bank Name')
    account_number = models.CharField(max_length=20, blank=True, null=True, verbose_name='Account Number')
    account_name = models.CharField(max_length=200, blank=True, null=True, verbose_name='Account Name')
    tax_id = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        verbose_name='Tax ID / NIN',
        help_text='National Identification Number or Tax ID'
    )
    
    # ========== EMERGENCY CONTACT ==========
    emergency_contact_name = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        verbose_name='Emergency Contact Name'
    )
    emergency_contact_relationship = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        verbose_name='Relationship',
        help_text='e.g., Spouse, Parent, Sibling'
    )
    emergency_contact_phone = models.CharField(
        max_length=20, 
        blank=True, 
        null=True, 
        verbose_name='Emergency Contact Phone'
    )
    emergency_contact_address = models.TextField(
        blank=True, 
        null=True, 
        verbose_name='Emergency Contact Address'
    )
    
    # ========== PROFILE & DOCUMENTS ==========
    profile_picture = models.ImageField(
        upload_to='profile_pics/', 
        blank=True, 
        null=True, 
        verbose_name='Profile Picture'
    )
    
    # ========== SYSTEM PERMISSIONS ==========
    is_active = models.BooleanField(
        default=True, 
        verbose_name='Active',
        help_text='Can this user log in?'
    )
    
    is_staff = models.BooleanField(
        default=False, 
        verbose_name='Staff Status (Can access admin)',
        help_text='Allow access to Django admin panel'
    )
    
    is_superuser = models.BooleanField(
        default=False, 
        verbose_name='Superuser Status',
        help_text='Has all permissions without explicitly assigning them'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    last_login = models.DateTimeField(blank=True, null=True, verbose_name='Last Login')
    
    # ========== MANAGER & AUTHENTICATION CONFIG ==========
    objects = CustomUserManager()  
    
    USERNAME_FIELD = 'email'  
    REQUIRED_FIELDS = ['first_name', 'last_name']  
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']  
        indexes = [
            # Database indexes for faster queries
            models.Index(fields=['email']),
            models.Index(fields=['employee_id']),
            models.Index(fields=['department']),
            models.Index(fields=['approval_level']),
        ]
    
    def __str__(self):
        """String representation: John Doe (john@example.com)"""
        return f"{self.get_full_name()} ({self.email})"
    
    def get_full_name(self):
        """
        Returns full name with middle name if available
        Example: John Michael Doe or John Doe
        """
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"
    
    def get_short_name(self):
        """Returns first name only"""
        return self.first_name
    
    def can_approve(self):
        """
        Check if user has approval authority
        Returns True if user is Supervisor, Dept Head, Director, or HR Admin
        Used in attendance approval workflow
        """
        return self.approval_level in [
            'SUPERVISOR', 
            'DEPT_HEAD', 
            'DEPUTY_DIR', 
            'DIRECTOR', 
            'HR_ADMIN'
        ]
    
    def get_subordinates(self):
        """
        Get all employees reporting to this user
        Returns QuerySet of CustomUser objects
        """
        return CustomUser.objects.filter(reports_to=self)
    
    def age(self):
        """
        Calculate age from date of birth
        Returns integer or None if DOB not set
        """
        if self.date_of_birth:
            today = timezone.now().date()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None
    
    # ========== HELPER METHODS FOR ORGANIZATIONAL STRUCTURE ==========
    def get_supervisor(self):
        """
        Get this employee's direct supervisor from their unit
        Returns CustomUser object or None
        
        CRITICAL FOR ATTENDANCE APPROVAL:
        This is used to determine who reviews attendance approval requests
        """
        if self.unit and self.unit.supervisor:
            return self.unit.supervisor
        return None
    
    def get_department_head(self):
        """
        Get this employee's department head
        Returns CustomUser object or None
        """
        if self.department and self.department.head:
            return self.department.head
        return None
    
    def is_department_head(self):
        """
        Check if this user is a department head
        Returns True if user.department_headed exists
        """
        return hasattr(self, 'department_headed')
    
    def is_unit_supervisor(self):
        """
        Check if this user is a unit supervisor
        Returns True if user.unit_supervised exists
        """
        return hasattr(self, 'unit_supervised')
    
    def is_currently_suspended(self):
        """
        Check if employee is currently suspended
        Simply checks employee_status field
        Returns True/False
        
        CRITICAL FOR ATTENDANCE:
        Suspended employees cannot clock in/out
        """
        return self.employee_status == 'SUSPENDED'
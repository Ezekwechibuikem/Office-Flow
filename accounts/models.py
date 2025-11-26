from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    """Custom manager for email-based authentication"""
    
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


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model with comprehensive employee information
    Uses email for authentication instead of username
    """
    
    # ========== AUTHENTICATION ==========
    email = models.EmailField(unique=True, verbose_name='Email Address')
    work_email = models.EmailField(blank=True, null=True, verbose_name='Work Email (if different)')
    
    # ========== PERSONAL INFORMATION ==========
    first_name = models.CharField(max_length=50, verbose_name='First Name')
    last_name = models.CharField(max_length=50, verbose_name='Last Name')
    middle_name = models.CharField(max_length=50, blank=True, null=True, verbose_name='Middle Name')
    
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True, verbose_name='Gender')
    
    date_of_birth = models.DateField(blank=True, null=True, verbose_name='Date of Birth')
    
    MARITAL_STATUS_CHOICES = [
        ('SINGLE', 'Single'),
        ('MARRIED', 'Married'),
        ('DIVORCED', 'Divorced'),
        ('WIDOWED', 'Widowed'),
    ]
    marital_status = models.CharField(max_length=10, choices=MARITAL_STATUS_CHOICES, blank=True, null=True, verbose_name='Marital Status')
    
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name='Phone Number')
    alternate_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='Alternate Phone')
    address = models.TextField(blank=True, null=True, verbose_name='Residential Address')
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name='City')
    state = models.CharField(max_length=100, blank=True, null=True, verbose_name='State')
    country = models.CharField(max_length=100, default='Nigeria', verbose_name='Country')
    
    nationality = models.CharField(max_length=100, blank=True, null=True, verbose_name='Nationality')
    state_of_origin = models.CharField(max_length=100, blank=True, null=True, verbose_name='State of Origin')
    religion = models.CharField(max_length=50, blank=True, null=True, verbose_name='Religion')
    
    # ========== PROFESSIONAL INFORMATION ==========
    employee_id = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name='Employee ID')
    position = models.CharField(max_length=100, blank=True, null=True, verbose_name='Job Title/Position')
    
    LEVEL_CHOICES = [
        ('JUNIOR', 'Junior'),
        ('MID', 'Mid-Level'),
        ('SENIOR', 'Senior'),
        ('LEAD', 'Lead'),
        ('PRINCIPAL', 'Principal'),
    ]
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, blank=True, null=True, verbose_name='Professional Level')
    
    bio = models.TextField(blank=True, null=True, verbose_name='Bio/About', help_text='Brief professional description')
    skills = models.TextField(blank=True, null=True, verbose_name='Skills', help_text='Comma-separated list of skills')
    languages = models.CharField(max_length=200, blank=True, null=True, verbose_name='Languages Spoken', help_text='e.g., English, Hausa, Yoruba')
    
    # ========== EMPLOYMENT DETAILS ==========
    department = models.CharField(max_length=100, blank=True, null=True, verbose_name='Department')
    unit = models.CharField(max_length=100, blank=True, null=True, verbose_name='Unit/Team')
    
    CONTRACT_TYPE_CHOICES = [
        ('PERMANENT', 'Permanent'),
        ('CONTRACT', 'Contract'),
        ('INTERN', 'Intern'),
        ('PART_TIME', 'Part-Time'),
        ('TEMPORARY', 'Temporary'),
    ]
    contract_type = models.CharField(max_length=20, choices=CONTRACT_TYPE_CHOICES, default='PERMANENT', verbose_name='Contract Type')
    
    date_joined = models.DateField(default=timezone.now, verbose_name='Date Joined Company')
    
    EMPLOYEE_STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('ON_LEAVE', 'On Leave'),
        ('SUSPENDED', 'Suspended'),
        ('TERMINATED', 'Terminated'),
        ('RESIGNED', 'Resigned'),
    ]
    employee_status = models.CharField(max_length=20, choices=EMPLOYEE_STATUS_CHOICES, default='ACTIVE', verbose_name='Employee Status')
    
    WORK_SCHEDULE_CHOICES = [
        ('SHIFTS', 'Shift-based'),
        ('REMOTE', 'Remote'),
        ('HYBRID', 'Hybrid'),
        ('FLEXIBLE', 'Flexible'),
    ]
    work_schedule = models.CharField(max_length=20, choices=WORK_SCHEDULE_CHOICES, default='9_TO_5', verbose_name='Work Schedule')
    
    office_location = models.CharField(max_length=200, blank=True, null=True, verbose_name='Office Location')
    
    # ========== ORGANIZATIONAL STRUCTURE ==========
    reports_to = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='subordinates',
        verbose_name='Reports To (Manager/Supervisor)'
    )
    
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
        verbose_name='Approval Level'
    )
    
    # ========== FINANCIAL INFORMATION ==========
    bank_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='Bank Name')
    account_number = models.CharField(max_length=20, blank=True, null=True, verbose_name='Account Number')
    account_name = models.CharField(max_length=200, blank=True, null=True, verbose_name='Account Name')
    tax_id = models.CharField(max_length=50, blank=True, null=True, verbose_name='Tax ID / NIN')
    
    # ========== EMERGENCY CONTACT ==========
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='Emergency Contact Name')
    emergency_contact_relationship = models.CharField(max_length=50, blank=True, null=True, verbose_name='Relationship')
    emergency_contact_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='Emergency Contact Phone')
    emergency_contact_address = models.TextField(blank=True, null=True, verbose_name='Emergency Contact Address')
    
    # ========== PROFILE & DOCUMENTS ==========
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True, verbose_name='Profile Picture')
    
    # ========== SYSTEM PERMISSIONS ==========
    is_active = models.BooleanField(default=True, verbose_name='Active')
    is_staff = models.BooleanField(default=False, verbose_name='Staff Status (Can access admin)')
    is_superuser = models.BooleanField(default=False, verbose_name='Superuser Status')
    
    # ========== TIMESTAMPS ==========
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    last_login = models.DateTimeField(blank=True, null=True, verbose_name='Last Login')
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['employee_id']),
            models.Index(fields=['department']),
            models.Index(fields=['approval_level']),
        ]
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"
    
    def get_full_name(self):
        """Returns full name with middle name if available"""
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"
    
    def get_short_name(self):
        return self.first_name
    
    def can_approve(self):
        """Check if user has approval authority"""
        return self.approval_level in ['SUPERVISOR', 'DEPT_HEAD', 'DEPUTY_DIR', 'DIRECTOR', 'HR_ADMIN']
    
    def get_subordinates(self):
        """Get all employees reporting to this user"""
        return CustomUser.objects.filter(reports_to=self)
    
    def age(self):
        """Calculate age from date of birth"""
        if self.date_of_birth:
            today = timezone.now().date()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None
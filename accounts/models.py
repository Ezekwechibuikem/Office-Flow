from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError


class CustomUserManager(BaseUserManager):
    "This is the custom user manager for CustomUser model"
    
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
    name = models.CharField(max_length=100, unique=True, verbose_name='Department Name')
    code = models.CharField(max_length=20, unique=True, verbose_name='Department Code')
    description = models.TextField(blank=True, null=True, verbose_name='Description')
    head = models.OneToOneField(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='department_headed',
        verbose_name='Department Head'
    )
    is_active = models.BooleanField(default=True, verbose_name='Active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_all_employees(self):
        return CustomUser.objects.filter(department=self)
    
    def get_unit_count(self):
        return self.units.count()


class Unit(models.Model):
    name = models.CharField(max_length=100, verbose_name='Unit Name')
    code = models.CharField(max_length=20, verbose_name='Unit Code')
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='units',
        verbose_name='Department'
    )
    description = models.TextField(blank=True, null=True, verbose_name='Description')
    supervisor = models.OneToOneField(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='unit_supervised',
        verbose_name='Unit Supervisor'
    )
    is_active = models.BooleanField(default=True, verbose_name='Active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Unit'
        verbose_name_plural = 'Units'
        ordering = ['department', 'name']
        unique_together = ['department', 'name']
    
    def __str__(self):
        return f"{self.department.name} - {self.name}"
    
    def get_all_employees(self):
        return CustomUser.objects.filter(unit=self)


class EmployeeSuspension(models.Model):
    employee = models.ForeignKey(
        'CustomUser',
        on_delete=models.CASCADE,
        related_name='suspensions',
        verbose_name='Employee'
    )
    start_date = models.DateField(verbose_name='Suspension Start Date')
    end_date = models.DateField(verbose_name='Suspension End Date')
    reason = models.TextField(verbose_name='Suspension Reason')
    suspended_by = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='suspensions_issued',
        verbose_name='Suspended By'
    )
    is_active = models.BooleanField(default=True, verbose_name='Active')
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
        if self.is_active:
            today = timezone.now().date()
            if self.start_date <= today <= self.end_date:
                self.employee.employee_status = 'SUSPENDED'
                self.employee.save()
    
    def is_currently_active(self):
        today = timezone.now().date()
        return self.is_active and self.start_date <= today <= self.end_date


class CustomUser(AbstractBaseUser, PermissionsMixin):
    
    email = models.EmailField(unique=True, verbose_name='Email Address')
    work_email = models.EmailField(blank=True, null=True, verbose_name='Work Email (if different)')
    
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
    
    employee_id = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name='Employee ID')
    position = models.CharField(max_length=100, blank=True, null=True, verbose_name='Job Title/Position')
    
    bio = models.TextField(blank=True, null=True, verbose_name='Bio/About')
    skills = models.TextField(blank=True, null=True, verbose_name='Skills')
    languages = models.CharField(max_length=200, blank=True, null=True, verbose_name='Languages Spoken')
    
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
    work_schedule = models.CharField(max_length=20, choices=WORK_SCHEDULE_CHOICES, default='HYBRID', verbose_name='Work Schedule')
    
    office_location = models.CharField(max_length=200, blank=True, null=True, verbose_name='Office Location')
    
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
    approval_level = models.CharField(max_length=20, choices=APPROVAL_LEVEL_CHOICES, default='STAFF', verbose_name='Approval Level')
    
    bank_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='Bank Name')
    account_number = models.CharField(max_length=20, blank=True, null=True, verbose_name='Account Number')
    account_name = models.CharField(max_length=200, blank=True, null=True, verbose_name='Account Name')
    tax_id = models.CharField(max_length=50, blank=True, null=True, verbose_name='Tax ID / NIN')
    
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='Emergency Contact Name')
    emergency_contact_relationship = models.CharField(max_length=50, blank=True, null=True, verbose_name='Relationship')
    emergency_contact_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='Emergency Contact Phone')
    emergency_contact_address = models.TextField(blank=True, null=True, verbose_name='Emergency Contact Address')
    
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True, verbose_name='Profile Picture')
    
    is_active = models.BooleanField(default=True, verbose_name='Active')
    is_staff = models.BooleanField(default=False, verbose_name='Staff Status (Can access admin)')
    is_superuser = models.BooleanField(default=False, verbose_name='Superuser Status')
    
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
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"
    
    def get_short_name(self):
        return self.first_name
    
    def can_approve(self):
        return self.approval_level in ['SUPERVISOR', 'DEPT_HEAD', 'DEPUTY_DIR', 'DIRECTOR', 'HR_ADMIN']
    
    def get_subordinates(self):
        return CustomUser.objects.filter(reports_to=self)
    
    def age(self):
        if self.date_of_birth:
            today = timezone.now().date()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None
    
    def get_supervisor(self):
        if self.unit and self.unit.supervisor:
            return self.unit.supervisor
        return None
    
    def get_department_head(self):
        if self.department and self.department.head:
            return self.department.head
        return None
    
    def is_department_head(self):
        return hasattr(self, 'department_headed')
    
    def is_unit_supervisor(self):
        return hasattr(self, 'unit_supervised')
    
    def is_currently_suspended(self):
        return self.employee_status == 'SUSPENDED'
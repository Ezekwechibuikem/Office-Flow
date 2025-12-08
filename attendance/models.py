from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from accounts.models import CustomUser  # Import our custom user model
import datetime


# ============================================================================
# HOLIDAY MODEL
# ============================================================================
class Holiday(models.Model):
    """
    Public holidays - days when no work is expected
    
    Examples:
        - New Year's Day (January 1)
        - Independence Day (October 1)
        - Democracy Day (June 12)
        - Christmas Day (December 25)
    
    When a day is marked as holiday:
        - Employees cannot clock in/out
        - Attendance status automatically becomes 'HOLIDAY'
        - No work day counted (won't affect pay)
    """
    
    # Holiday Information
    name = models.CharField(
        max_length=200, 
        verbose_name='Holiday Name',
        help_text='e.g., Independence Day, Christmas'
    )
    
    date = models.DateField(
        unique=True, 
        verbose_name='Date',
        help_text='The specific date of the holiday'
    )
    
    description = models.TextField(
        blank=True, 
        null=True, 
        verbose_name='Description',
        help_text='Additional information about the holiday'
    )
    
    # Status
    is_active = models.BooleanField(
        default=True, 
        verbose_name='Active',
        help_text='Set to False to disable this holiday'
    )
    
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Public Holiday'
        verbose_name_plural = 'Public Holidays'
        ordering = ['-date']  # Most recent first
    
    def __str__(self):
        """Display as: Independence Day - 2024-10-01"""
        return f"{self.name} - {self.date}"


# ============================================================================
# ATTENDANCE SETTINGS MODEL
# ============================================================================
class AttendanceSettings(models.Model):
    """
    Global attendance rules and time settings
    
    Purpose:
        - Define work hours (9am - 5pm)
        - Set clock-in deadline (9:00 AM)
        - Set clock-out deadline (6:01 PM)
        - Configure enforcement rules
    
    Usage:
        - Only ONE active settings record should exist
        - Admin can update settings without changing code
        - All attendance records follow these rules
    """
    
    # ========== TIME RULES ==========
    work_start_time = models.TimeField(
        default=datetime.time(9, 0),
        verbose_name='Work Start Time (Clock-in deadline)',
        help_text='Employees must clock in by this time (e.g., 09:00 AM)'
    )
    
    work_end_time = models.TimeField(
        default=datetime.time(17, 0),
        verbose_name='Work End Time',
        help_text='Standard work end time (e.g., 05:00 PM)'
    )
    
    clock_out_deadline = models.TimeField(
        default=datetime.time(18, 1),
        verbose_name='Clock-out Deadline',
        help_text='Employees must clock out by this time or marked absent (e.g., 06:01 PM)'
    )
    
    # ========== WORK HOURS ==========
    standard_work_hours = models.DecimalField(
        max_digits=4, 
        decimal_places=2, 
        default=8.00,
        verbose_name='Standard Work Hours Per Day',
        help_text='Expected hours per work day (e.g., 8.00)'
    )
    
    # ========== ENFORCEMENT RULES ==========
    auto_mark_absent_after_deadline = models.BooleanField(
        default=True,
        verbose_name='Auto-mark absent if no clock-in by deadline',
        help_text='If True, employees not clocked in by 9am are marked ABSENT'
    )
    
    require_clock_out = models.BooleanField(
        default=True,
        verbose_name='Require clock-out',
        help_text='If True, employees must clock out or be marked ABSENT'
    )
    
    # ========== STATUS ==========
    is_active = models.BooleanField(
        default=True, 
        verbose_name='Active',
        help_text='Only one settings record should be active at a time'
    )
    
    # ========== TIMESTAMPS ==========
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Attendance Settings'
        verbose_name_plural = 'Attendance Settings'
    
    def __str__(self):
        return f"Attendance Settings (Active: {self.is_active})"
    
    @classmethod
    def get_active_settings(cls):
        """
        Get the currently active settings record
        Returns the first active settings or None
        
        Usage in code:
            settings = AttendanceSettings.get_active_settings()
            work_start = settings.work_start_time
        """
        return cls.objects.filter(is_active=True).first()


# ============================================================================
# ATTENDANCE MODEL
# ============================================================================
class Attendance(models.Model):
    """
    Daily attendance records - simplified and strict
    
    Core Rules:
        1. ONE record per employee per day (unique_together)
        2. Must clock in BEFORE 9:00 AM or marked ABSENT
        3. Must clock out BEFORE 6:01 PM or marked ABSENT
        4. Status auto-calculated based on hierarchy:
           - SUSPENDED (highest priority - from user.employee_status)
           - ON_LEAVE (from user.employee_status)
           - WEEKEND (Saturday/Sunday)
           - HOLIDAY (public holiday)
           - PRESENT (clocked in before 9am)
           - ABSENT (failed to clock in or out on time)
    
    Approval Workflow:
        If marked ABSENT, employee can request approval:
        1. Employee submits request with reason
        2. Unit Supervisor reviews → Approve/Reject
        3. If approved by supervisor → HR reviews → Approve/Reject
        4. If HR approves → Status changes to PRESENT
    """
    
    # ========== STATUS CHOICES ==========
    STATUS_CHOICES = [
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
        ('ON_LEAVE', 'On Leave'),
        ('WEEKEND', 'Weekend'),
        ('HOLIDAY', 'Public Holiday'),
        ('SUSPENDED', 'Suspended'),
    ]
    
    # ========== CORE FIELDS ==========
    employee = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE,  # If employee deleted, delete attendance records
        related_name='attendance_records',  # Allows: user.attendance_records.all()
        verbose_name='Employee'
    )
    
    date = models.DateField(
        default=timezone.now, 
        verbose_name='Date',
        help_text='The date of this attendance record'
    )
    
    # ========== CLOCK IN/OUT ==========
    clock_in_time = models.TimeField(
        null=True, 
        blank=True, 
        verbose_name='Clock In Time',
        help_text='Time when employee clocked in (e.g., 08:45 AM)'
    )
    
    clock_out_time = models.TimeField(
        null=True, 
        blank=True, 
        verbose_name='Clock Out Time',
        help_text='Time when employee clocked out (e.g., 05:30 PM)'
    )
    
    # ========== STATUS ==========
    # CRITICAL: This is the main field that determines attendance
    # Auto-calculated on save() based on multiple factors
    employeeDayStatus = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES,
        verbose_name='Day Status',
        db_index=True,  # Database index for faster queries
        help_text='Auto-calculated based on clock-in time, employee status, holidays, etc.'
    )
    
    # ========== WORK HOURS ==========
    hours_worked = models.DecimalField(
        max_digits=4, 
        decimal_places=2, 
        null=True, 
        blank=True,
        verbose_name='Hours Worked',
        help_text='Auto-calculated: clock_out_time - clock_in_time'
    )
    
    # ========== APPROVAL SYSTEM ==========
    # Used when employee is ABSENT and requests to be marked PRESENT
    has_pending_approval_request = models.BooleanField(
        default=False,
        verbose_name='Has Pending Approval Request',
        help_text='True if employee has submitted request to change ABSENT to PRESENT'
    )
    
    # ========== TIMESTAMPS ==========
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='Created At',
        help_text='When this record was first created'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name='Updated At',
        help_text='Last time this record was modified'
    )
    
    class Meta:
        verbose_name = 'Attendance Record'
        verbose_name_plural = 'Attendance Records'
        ordering = ['-date', '-clock_in_time']  # Most recent first
        unique_together = ['employee', 'date']  # Only ONE record per employee per day
        indexes = [
            # Database indexes for faster queries
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['date']),
            models.Index(fields=['employeeDayStatus']),
        ]
    
    def __str__(self):
        """Display as: John Doe - 2024-12-09 - PRESENT"""
        return f"{self.employee.get_full_name()} - {self.date} - {self.employeeDayStatus}"
    
    def clean(self):
        """
        Validation rules before saving
        Called when form is submitted or model.full_clean() is called
        """
        # Validate that clock-out is after clock-in
        if self.clock_in_time and self.clock_out_time:
            if self.clock_out_time <= self.clock_in_time:
                raise ValidationError("Clock-out time must be after clock-in time")
    
    def save(self, *args, **kwargs):
        """
        Override save method to auto-calculate status and hours worked
        
        STATUS CALCULATION HIERARCHY (checked in order):
        1. Check employee.employee_status for SUSPENDED/ON_LEAVE
        2. Check if weekend (Saturday/Sunday)
        3. Check if public holiday
        4. Check clock-in time (before 9am = PRESENT, after = ABSENT)
        5. If no clock-in = ABSENT
        
        This method runs EVERY TIME an attendance record is saved
        """
        
        # Get active attendance settings
        settings = AttendanceSettings.get_active_settings()
        if not settings:
            # If no settings exist, use defaults
            work_start = datetime.time(9, 0)  # 9:00 AM
            clock_out_deadline = datetime.time(18, 1)  # 6:01 PM
        else:
            work_start = settings.work_start_time
            clock_out_deadline = settings.clock_out_deadline
        
        # ========== PRIORITY 1: CHECK EMPLOYEE STATUS ==========
        # If employee is SUSPENDED or ON_LEAVE in accounts app,
        # that overrides everything else
        if self.employee.employee_status == 'SUSPENDED':
            self.employeeDayStatus = 'SUSPENDED'
        
        elif self.employee.employee_status == 'ON_LEAVE':
            self.employeeDayStatus = 'ON_LEAVE'
        
        # ========== PRIORITY 2: CHECK IF WEEKEND ==========
        # weekday() returns: Monday=0, Tuesday=1, ... Saturday=5, Sunday=6
        elif self.date.weekday() in [5, 6]:
            self.employeeDayStatus = 'WEEKEND'
        
        # ========== PRIORITY 3: CHECK IF PUBLIC HOLIDAY ==========
        elif Holiday.objects.filter(date=self.date, is_active=True).exists():
            self.employeeDayStatus = 'HOLIDAY'
        
        # ========== PRIORITY 4: CALCULATE BASED ON CLOCK-IN/OUT ==========
        else:
            # Check if employee clocked in
            if self.clock_in_time:
                # Did they clock in on time (before 9:00 AM)?
                if self.clock_in_time <= work_start:
                    # Clocked in on time
                    if self.clock_out_time:
                        # Both clock-in and clock-out done = PRESENT
                        self.employeeDayStatus = 'PRESENT'
                    else:
                        # Clocked in but not out yet
                        # Mark as PRESENT for now
                        # Scheduled job at 6:01 PM will change to ABSENT if not clocked out
                        self.employeeDayStatus = 'PRESENT'
                else:
                    # Clocked in AFTER 9:00 AM = ABSENT
                    self.employeeDayStatus = 'ABSENT'
            else:
                # No clock-in at all = ABSENT
                self.employeeDayStatus = 'ABSENT'
        
        # ========== CALCULATE HOURS WORKED ==========
        # Only calculate if both clock-in and clock-out exist
        if self.clock_in_time and self.clock_out_time:
            # Combine date with time to create full datetime objects
            clock_in_datetime = datetime.datetime.combine(self.date, self.clock_in_time)
            clock_out_datetime = datetime.datetime.combine(self.date, self.clock_out_time)
            
            # Calculate time difference
            time_diff = clock_out_datetime - clock_in_datetime
            
            # Convert seconds to hours and round to 2 decimal places
            # Example: 28800 seconds = 8.00 hours
            self.hours_worked = round(time_diff.total_seconds() / 3600, 2)
        
        # Save to database
        super().save(*args, **kwargs)
    
    # ========== HELPER METHODS ==========
    
    def is_full_day(self):
        """
        Check if employee worked full day (8 hours or more)
        Returns True/False
        
        Usage:
            if attendance.is_full_day():
                print("Full day worked!")
        """
        return self.hours_worked and self.hours_worked >= 8
    
    def can_request_approval(self):
        """
        Check if employee can request to change ABSENT to PRESENT
        
        Conditions:
            1. Status must be ABSENT
            2. No pending request already exists
        
        Returns True/False
        """
        return (
            self.employeeDayStatus == 'ABSENT' and 
            not self.has_pending_approval_request
        )
    
    @staticmethod
    def is_employee_suspended(employee, date):
        """
        Static method to check if an employee is suspended on a given date
        
        Args:
            employee: CustomUser object
            date: Date to check
        
        Returns: True if suspended, False otherwise
        
        Usage:
            is_suspended = Attendance.is_employee_suspended(user, today)
        """
        return employee.employee_status == 'SUSPENDED'


# ============================================================================
# ATTENDANCE APPROVAL REQUEST MODEL
# ============================================================================
class AttendanceApprovalRequest(models.Model):
    """
    Three-tier approval workflow for changing ABSENT to PRESENT
    
    WORKFLOW:
    1. Employee (marked ABSENT) submits request with reason
       Status: PENDING
       
    2. Unit Supervisor reviews:
       - If APPROVE → Status: SUPERVISOR_APPROVED (goes to HR)
       - If REJECT → Status: REJECTED (request denied)
       
    3. HR Admin reviews (only if supervisor approved):
       - If APPROVE → Status: HR_APPROVED + Attendance marked PRESENT
       - If REJECT → Status: REJECTED (request denied)
    
    PERMISSIONS:
    - Employee: Can submit request, view own requests
    - Supervisor: Can approve/reject PENDING requests from their unit
    - HR Admin: Can approve/reject SUPERVISOR_APPROVED requests
    
    IMPORTANT:
    - Only HR can actually change attendance status to PRESENT
    - Supervisor approval is just first-level approval
    - Employee cannot directly mark themselves present
    """
    
    # ========== STATUS CHOICES ==========
    STATUS_CHOICES = [
        ('PENDING', 'Pending Supervisor Review'),
        ('SUPERVISOR_APPROVED', 'Supervisor Approved - Awaiting HR'),
        ('HR_APPROVED', 'HR Approved - Marked Present'),
        ('REJECTED', 'Rejected'),
    ]
    
    # ========== CORE FIELDS ==========
    attendance = models.ForeignKey(
        Attendance,
        on_delete=models.CASCADE,  # If attendance deleted, delete requests
        related_name='approval_requests',  # Allows: attendance.approval_requests.all()
        verbose_name='Attendance Record'
    )
    
    employee = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='attendance_requests',  # Allows: user.attendance_requests.all()
        verbose_name='Employee'
    )
    
    # ========== REQUEST DETAILS ==========
    reason = models.TextField(
        verbose_name='Reason for Absence',
        help_text='Employee must explain why they were absent (e.g., traffic, medical emergency)'
    )
    
    supporting_documents = models.FileField(
        upload_to='attendance_approvals/',  # Files saved to media/attendance_approvals/
        null=True,
        blank=True,
        verbose_name='Supporting Documents (Optional)',
        help_text='Upload proof: medical certificate, police report, etc.'
    )
    
    # ========== STATUS ==========
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name='Request Status'
    )
    
    # ========== SUPERVISOR REVIEW ==========
    supervisor_reviewed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supervisor_reviewed_requests',
        verbose_name='Supervisor Reviewed By',
        help_text='Which supervisor approved/rejected this'
    )
    
    supervisor_review_notes = models.TextField(
        null=True, 
        blank=True, 
        verbose_name='Supervisor Notes',
        help_text='Supervisor comments on the request'
    )
    
    supervisor_reviewed_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name='Supervisor Reviewed At'
    )
    
    # ========== HR REVIEW ==========
    hr_reviewed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hr_reviewed_requests',
        verbose_name='HR Reviewed By',
        help_text='Which HR admin approved/rejected this'
    )
    
    hr_review_notes = models.TextField(
        null=True, 
        blank=True, 
        verbose_name='HR Notes',
        help_text='HR admin comments on the request'
    )
    
    hr_reviewed_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name='HR Reviewed At'
    )
    
    # ========== TIMESTAMPS ==========
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='Requested At',
        help_text='When employee submitted this request'
    )
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Attendance Approval Request'
        verbose_name_plural = 'Attendance Approval Requests'
        ordering = ['-created_at']  # Most recent first
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['employee', 'status']),
        ]
    
    def __str__(self):
        """Display as: John Doe - 2024-12-09 - PENDING"""
        return f"{self.employee.get_full_name()} - {self.attendance.date} - {self.status}"
    
    # ========== SUPERVISOR ACTIONS ==========
    
    def supervisor_approve(self, supervisor, notes=None):
        """
        Supervisor approves the request
        
        Action:
            - Changes status to SUPERVISOR_APPROVED
            - Records who approved and when
            - Sends to HR for final review
        
        Args:
            supervisor: CustomUser who is approving
            notes: Optional comments from supervisor
        
        Raises:
            ValidationError if request is not PENDING
        """
        # Can only approve requests that are PENDING
        if self.status != 'PENDING':
            raise ValidationError("Can only approve pending requests")
        
        # Update status and record details
        self.status = 'SUPERVISOR_APPROVED'
        self.supervisor_reviewed_by = supervisor
        self.supervisor_review_notes = notes
        self.supervisor_reviewed_at = timezone.now()
        self.save()
        
        # TODO: Send email notification to HR
        # Example: send_mail("New attendance approval awaiting HR review...")
    
    def supervisor_reject(self, supervisor, notes):
        """
        Supervisor rejects the request
        
        Action:
            - Changes status to REJECTED
            - Request is denied completely (doesn't go to HR)
            - Attendance remains ABSENT
        
        Args:
            supervisor: CustomUser who is rejecting
            notes: REQUIRED reason for rejection
        
        Raises:
            ValidationError if request is not PENDING
        """
        if self.status != 'PENDING':
            raise ValidationError("Can only reject pending requests")
        
        # Update status and record details
        self.status = 'REJECTED'
        self.supervisor_reviewed_by = supervisor
        self.supervisor_review_notes = notes
        self.supervisor_reviewed_at = timezone.now()
        self.save()
        
        # Clear pending flag on attendance record
        self.attendance.has_pending_approval_request = False
        self.attendance.save()
        
        # TODO: Send email notification to employee
        # Example: send_mail("Your attendance request was rejected...")
    
    # ========== HR ACTIONS ==========
    
    def hr_approve(self, hr_user, notes=None):
        """
        HR approves the request
        
        Action:
            - Changes status to HR_APPROVED
            - **MARKS ATTENDANCE AS PRESENT** (this is the key action)
            - Records who approved and when
        
        Args:
            hr_user: CustomUser with HR_ADMIN approval level
            notes: Optional comments from HR
        
        Raises:
            ValidationError if request is not SUPERVISOR_APPROVED
        
        CRITICAL: This is the ONLY method that can change ABSENT to PRESENT
        """
        # Can only approve requests that supervisor already approved
        if self.status != 'SUPERVISOR_APPROVED':
            raise ValidationError("Can only approve supervisor-approved requests")
        
        # Update request status
        self.status = 'HR_APPROVED'
        self.hr_reviewed_by = hr_user
        self.hr_review_notes = notes
        self.hr_reviewed_at = timezone.now()
        self.save()
        
        # **THIS IS WHERE ATTENDANCE GETS MARKED PRESENT**
        self.attendance.employeeDayStatus = 'PRESENT'
        self.attendance.has_pending_approval_request = False
        self.attendance.save()
        
        # TODO: Send email notification to employee
        # Example: send_mail("Your attendance has been marked PRESENT...")
    
    def hr_reject(self, hr_user, notes):
        """
        HR rejects the request
        
        Action:
            - Changes status to REJECTED
            - Attendance remains ABSENT
        
        Args:
            hr_user: CustomUser with HR_ADMIN approval level
            notes: REQUIRED reason for rejection
        
        Raises:
            ValidationError if request is not SUPERVISOR_APPROVED
        """
        if self.status != 'SUPERVISOR_APPROVED':
            raise ValidationError("Can only reject supervisor-approved requests")
        
        # Update request status
        self.status = 'REJECTED'
        self.hr_reviewed_by = hr_user
        self.hr_review_notes = notes
        self.hr_reviewed_at = timezone.now()
        self.save()
        
        # Clear pending flag on attendance record
        self.attendance.has_pending_approval_request = False
        self.attendance.save()
        
        # TODO: Send email notification to employee
        # Example: send_mail("Your attendance request was rejected by HR...")
    
    # ========== PERMISSION CHECKS ==========
    
    def get_supervisor(self):
        """
        Get the supervisor who should review this request
        Returns the employee's unit supervisor
        
        Returns: CustomUser or None
        """
        if self.employee.unit and self.employee.unit.supervisor:
            return self.employee.unit.supervisor
        return None
    
    def can_user_review_as_supervisor(self, user):
        """
        Check if given user is the supervisor for this request
        
        Args:
            user: CustomUser to check
        
        Returns: True if user is the supervisor, False otherwise
        
        Usage:
            if request.can_user_review_as_supervisor(request.user):
                # Show approve/reject buttons
        """
        supervisor = self.get_supervisor()
        return supervisor and supervisor == user
    
    def can_user_review_as_hr(self, user):
        """
        Check if given user is HR admin
        
        Args:
            user: CustomUser to check
        
        Returns: True if user is HR_ADMIN, False otherwise
        
        Usage:
            if request.can_user_review_as_hr(request.user):
                # Show HR approve/reject buttons
        """
        return user.approval_level == 'HR_ADMIN'
    
    def can_supervisor_review(self):
        """Check if this request is ready for supervisor review"""
        return self.status == 'PENDING'
    
    def can_hr_review(self):
        """Check if this request is ready for HR review"""
        return self.status == 'SUPERVISOR_APPROVED'
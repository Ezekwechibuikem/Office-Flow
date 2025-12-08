from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from accounts.models import CustomUser
import datetime


class Holiday(models.Model):
    name = models.CharField(max_length=200, verbose_name='Holiday Name')
    date = models.DateField(unique=True, verbose_name='Date')
    description = models.TextField(blank=True, null=True, verbose_name='Description')
    is_active = models.BooleanField(default=True, verbose_name='Active')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Public Holiday'
        verbose_name_plural = 'Public Holidays'
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.name} - {self.date}"


class AttendanceSettings(models.Model):
    work_start_time = models.TimeField(default=datetime.time(9, 0), verbose_name='Work Start Time (Clock-in deadline)')
    work_end_time = models.TimeField(default=datetime.time(17, 0), verbose_name='Work End Time')
    clock_out_deadline = models.TimeField(default=datetime.time(18, 1), verbose_name='Clock-out Deadline (6:01 PM)')
    standard_work_hours = models.DecimalField(max_digits=4, decimal_places=2, default=8.00, verbose_name='Standard Work Hours Per Day')
    auto_mark_absent_after_deadline = models.BooleanField(default=True, verbose_name='Auto-mark absent if no clock-in by deadline')
    require_clock_out = models.BooleanField(default=True, verbose_name='Require clock-out (mark absent if not clocked out)')
    is_active = models.BooleanField(default=True, verbose_name='Active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Attendance Settings'
        verbose_name_plural = 'Attendance Settings'
    
    def __str__(self):
        return f"Attendance Settings (Active: {self.is_active})"
    
    @classmethod
    def get_active_settings(cls):
        return cls.objects.filter(is_active=True).first()


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
        ('ON_LEAVE', 'On Leave'),
        ('WEEKEND', 'Weekend'),
        ('HOLIDAY', 'Public Holiday'),
        ('SUSPENDED', 'Suspended'),
    ]
    
    employee = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='attendance_records', verbose_name='Employee')
    date = models.DateField(default=timezone.now, verbose_name='Date')
    clock_in_time = models.TimeField(null=True, blank=True, verbose_name='Clock In Time')
    clock_out_time = models.TimeField(null=True, blank=True, verbose_name='Clock Out Time')
    employeeDayStatus = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name='Day Status', db_index=True)
    hours_worked = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, verbose_name='Hours Worked')
    has_pending_approval_request = models.BooleanField(default=False, verbose_name='Has Pending Approval Request')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated At')
    
    class Meta:
        verbose_name = 'Attendance Record'
        verbose_name_plural = 'Attendance Records'
        ordering = ['-date', '-clock_in_time']
        unique_together = ['employee', 'date']
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['date']),
            models.Index(fields=['employeeDayStatus']),
        ]
    
    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.date} - {self.employeeDayStatus}"
    
    def clean(self):
        if self.clock_in_time and self.clock_out_time:
            if self.clock_out_time <= self.clock_in_time:
                raise ValidationError("Clock-out time must be after clock-in time")
    
    def save(self, *args, **kwargs):
        settings = AttendanceSettings.get_active_settings()
        if not settings:
            work_start = datetime.time(9, 0)
            clock_out_deadline = datetime.time(18, 1)
        else:
            work_start = settings.work_start_time
            clock_out_deadline = settings.clock_out_deadline
        
        if self.employee.employee_status == 'SUSPENDED':
            self.employeeDayStatus = 'SUSPENDED'
        elif self.employee.employee_status == 'ON_LEAVE':
            self.employeeDayStatus = 'ON_LEAVE'
        elif self.date.weekday() in [5, 6]:
            self.employeeDayStatus = 'WEEKEND'
        elif Holiday.objects.filter(date=self.date, is_active=True).exists():
            self.employeeDayStatus = 'HOLIDAY'
        else:
            if self.clock_in_time:
                if self.clock_in_time <= work_start:
                    if self.clock_out_time:
                        self.employeeDayStatus = 'PRESENT'
                    else:
                        self.employeeDayStatus = 'PRESENT'
                else:
                    self.employeeDayStatus = 'ABSENT'
            else:
                self.employeeDayStatus = 'ABSENT'
        
        if self.clock_in_time and self.clock_out_time:
            clock_in_datetime = datetime.datetime.combine(self.date, self.clock_in_time)
            clock_out_datetime = datetime.datetime.combine(self.date, self.clock_out_time)
            time_diff = clock_out_datetime - clock_in_datetime
            self.hours_worked = round(time_diff.total_seconds() / 3600, 2)
        
        super().save(*args, **kwargs)
    
    def is_full_day(self):
        return self.hours_worked and self.hours_worked >= 8
    
    def can_request_approval(self):
        return self.employeeDayStatus == 'ABSENT' and not self.has_pending_approval_request
    
    @staticmethod
    def is_employee_suspended(employee, date):
        return employee.employee_status == 'SUSPENDED'


class AttendanceApprovalRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Supervisor Review'),
        ('SUPERVISOR_APPROVED', 'Supervisor Approved - Awaiting HR'),
        ('HR_APPROVED', 'HR Approved - Marked Present'),
        ('REJECTED', 'Rejected'),
    ]
    
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE, related_name='approval_requests', verbose_name='Attendance Record')
    employee = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='attendance_requests', verbose_name='Employee')
    reason = models.TextField(verbose_name='Reason for Absence')
    supporting_documents = models.FileField(upload_to='attendance_approvals/', null=True, blank=True, verbose_name='Supporting Documents (Optional)')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDING', verbose_name='Request Status')
    
    supervisor_reviewed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='supervisor_reviewed_requests', verbose_name='Supervisor Reviewed By')
    supervisor_review_notes = models.TextField(null=True, blank=True, verbose_name='Supervisor Notes')
    supervisor_reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='Supervisor Reviewed At')
    
    hr_reviewed_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='hr_reviewed_requests', verbose_name='HR Reviewed By')
    hr_review_notes = models.TextField(null=True, blank=True, verbose_name='HR Notes')
    hr_reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='HR Reviewed At')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Requested At')
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Attendance Approval Request'
        verbose_name_plural = 'Attendance Approval Requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['employee', 'status']),
        ]
    
    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.attendance.date} - {self.status}"
    
    def supervisor_approve(self, supervisor, notes=None):
        if self.status != 'PENDING':
            raise ValidationError("Can only approve pending requests")
        self.status = 'SUPERVISOR_APPROVED'
        self.supervisor_reviewed_by = supervisor
        self.supervisor_review_notes = notes
        self.supervisor_reviewed_at = timezone.now()
        self.save()
    
    def supervisor_reject(self, supervisor, notes):
        if self.status != 'PENDING':
            raise ValidationError("Can only reject pending requests")
        self.status = 'REJECTED'
        self.supervisor_reviewed_by = supervisor
        self.supervisor_review_notes = notes
        self.supervisor_reviewed_at = timezone.now()
        self.save()
        self.attendance.has_pending_approval_request = False
        self.attendance.save()
    
    def hr_approve(self, hr_user, notes=None):
        if self.status != 'SUPERVISOR_APPROVED':
            raise ValidationError("Can only approve supervisor-approved requests")
        self.status = 'HR_APPROVED'
        self.hr_reviewed_by = hr_user
        self.hr_review_notes = notes
        self.hr_reviewed_at = timezone.now()
        self.save()
        self.attendance.employeeDayStatus = 'PRESENT'
        self.attendance.has_pending_approval_request = False
        self.attendance.save()
    
    def hr_reject(self, hr_user, notes):
        if self.status != 'SUPERVISOR_APPROVED':
            raise ValidationError("Can only reject supervisor-approved requests")
        self.status = 'REJECTED'
        self.hr_reviewed_by = hr_user
        self.hr_review_notes = notes
        self.hr_reviewed_at = timezone.now()
        self.save()
        self.attendance.has_pending_approval_request = False
        self.attendance.save()
    
    def get_supervisor(self):
        if self.employee.unit and self.employee.unit.supervisor:
            return self.employee.unit.supervisor
        return None
    
    def can_user_review_as_supervisor(self, user):
        supervisor = self.get_supervisor()
        return supervisor and supervisor == user
    
    def can_user_review_as_hr(self, user):
        return user.approval_level == 'HR_ADMIN'
    
    def can_supervisor_review(self):
        return self.status == 'PENDING'
    
    def can_hr_review(self):
        return self.status == 'SUPERVISOR_APPROVED'
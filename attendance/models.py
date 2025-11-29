from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from accounts.models import CustomUser
import datetime


class Holiday(models.Model):
    """Public holidays - no work expected"""
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


class OfficeIPWhitelist(models.Model):
    """Allowed IP addresses for clock-in"""
    ip_address = models.GenericIPAddressField(unique=True, verbose_name='IP Address')
    location_name = models.CharField(max_length=200, verbose_name='Office Location')
    is_active = models.BooleanField(default=True, verbose_name='Active')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='created_ips')
    
    class Meta:
        verbose_name = 'Office IP Address'
        verbose_name_plural = 'Office IP Addresses'
        ordering = ['location_name']
    
    def __str__(self):
        return f"{self.ip_address} - {self.location_name}"


class Attendance(models.Model):
    """Daily attendance records with clock-in/out"""
    
    STATUS_CHOICES = [
        ('PRESENT', 'Present'),
        ('LATE', 'Late'),
        ('ABSENT', 'Absent'),
        ('ON_LEAVE', 'On Leave'),
        ('WEEKEND', 'Weekend'),
        ('HOLIDAY', 'Public Holiday'),
    ]
    
    # Core Fields
    employee = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField(default=timezone.now, verbose_name='Date')
    
    # Clock In/Out
    clock_in_time = models.TimeField(null=True, blank=True, verbose_name='Clock In Time')
    clock_out_time = models.TimeField(null=True, blank=True, verbose_name='Clock Out Time')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name='Status')
    
    # Location Tracking
    clock_in_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name='Clock-in IP Address')
    clock_out_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name='Clock-out IP Address')
    clock_in_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name='Clock-in Latitude')
    clock_in_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name='Clock-in Longitude')
    clock_out_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name='Clock-out Latitude')
    clock_out_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name='Clock-out Longitude')
    
    # Device Info
    clock_in_device = models.CharField(max_length=200, null=True, blank=True, verbose_name='Clock-in Device')
    clock_out_device = models.CharField(max_length=200, null=True, blank=True, verbose_name='Clock-out Device')
    
    # Work Hours
    hours_worked = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, verbose_name='Hours Worked')
    
    # Manual Entry (by supervisor)
    is_manual_entry = models.BooleanField(default=False, verbose_name='Manual Entry')
    marked_by = models.ForeignKey(
        CustomUser, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='attendance_marked',
        verbose_name='Marked By'
    )
    manual_entry_reason = models.TextField(null=True, blank=True, verbose_name='Manual Entry Reason')
    
    # Notes
    remarks = models.TextField(null=True, blank=True, verbose_name='Remarks/Notes')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Attendance Record'
        verbose_name_plural = 'Attendance Records'
        ordering = ['-date', '-clock_in_time']
        unique_together = ['employee', 'date']  # One record per employee per day
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['date']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.employee.get_full_name()} - {self.date} - {self.status}"
    
    def clean(self):
        """Validation rules"""
        # Check if weekend
        if self.date.weekday() in [5, 6]:  # Saturday = 5, Sunday = 6
            if not self.is_manual_entry:
                raise ValidationError("Cannot clock in on weekends. Contact supervisor for manual entry.")
        
        # Check if holiday
        if Holiday.objects.filter(date=self.date, is_active=True).exists():
            if not self.is_manual_entry:
                raise ValidationError("Cannot clock in on public holidays. Contact supervisor for manual entry.")
        
        # Validate clock-out is after clock-in
        if self.clock_in_time and self.clock_out_time:
            if self.clock_out_time <= self.clock_in_time:
                raise ValidationError("Clock-out time must be after clock-in time.")
    
    def save(self, *args, **kwargs):
        # Auto-detect weekend
        if self.date.weekday() in [5, 6]:
            self.status = 'WEEKEND'
        
        # Auto-detect holiday
        elif Holiday.objects.filter(date=self.date, is_active=True).exists():
            self.status = 'HOLIDAY'
        
        # Calculate status based on clock-in time
        elif self.clock_in_time:
            work_start = datetime.time(9, 0)  # 9:00 AM
            
            if self.clock_in_time <= work_start:
                self.status = 'PRESENT'
            else:
                self.status = 'LATE'
        
        # Calculate hours worked
        if self.clock_in_time and self.clock_out_time:
            # Combine date with time to create datetime objects
            clock_in_datetime = datetime.datetime.combine(self.date, self.clock_in_time)
            clock_out_datetime = datetime.datetime.combine(self.date, self.clock_out_time)
            
            # Calculate difference
            time_diff = clock_out_datetime - clock_in_datetime
            self.hours_worked = round(time_diff.total_seconds() / 3600, 2)  # Convert to hours
        
        super().save(*args, **kwargs)
    
    def is_late(self):
        """Check if employee was late"""
        return self.status == 'LATE'
    
    def is_full_day(self):
        """Check if employee worked full 8 hours"""
        return self.hours_worked and self.hours_worked >= 8
    
    def is_early_departure(self):
        """Check if employee left before 5 PM"""
        if self.clock_out_time:
            work_end = datetime.time(17, 0)  # 5:00 PM
            return self.clock_out_time < work_end
        return False
    
    @staticmethod
    def is_office_ip(ip_address):
        """Check if IP is in office whitelist"""
        return OfficeIPWhitelist.objects.filter(ip_address=ip_address, is_active=True).exists()
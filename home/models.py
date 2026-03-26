from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('hi', 'Hindi'),
        ('mr', 'Marathi'),
        ('bn', 'Bengali'),
        ('ta', 'Tamil'),
        ('te', 'Telugu'),
        ('gu', 'Gujarati'),
        ('kn', 'Kannada'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    preferred_language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default='en')
    phone = models.CharField(max_length=15, blank=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"{self.user.username}'s profile"


class DomicileApplication(models.Model):
    STATUS_CHOICES = [
        ('pending',    'Pending Review'),
        ('processing', 'Under Processing'),
        ('approved',   'Approved'),
        ('rejected',   'Rejected'),
    ]

    # Applicant details
    user           = models.ForeignKey(User, on_delete=models.CASCADE, related_name='domicile_applications')
    full_name      = models.CharField(max_length=100, verbose_name='Full Name')
    father_name    = models.CharField(max_length=100, blank=True, verbose_name="Father's / Spouse's Name")
    gender         = models.CharField(max_length=10, default='', verbose_name='Gender')
    dob            = models.DateField(verbose_name='Date of Birth')
    mobile         = models.CharField(max_length=15, verbose_name='Mobile Number')

    # Identity documents
    aadhaar        = models.CharField(max_length=20, blank=True, verbose_name='Aadhaar Number')
    pan_number     = models.CharField(max_length=15, blank=True, verbose_name='PAN Number')
    voter_id       = models.CharField(max_length=20, blank=True, verbose_name='Voter ID')

    # Address
    address        = models.TextField(verbose_name='Permanent Address')
    district       = models.CharField(max_length=50, verbose_name='District')
    state          = models.CharField(max_length=50, verbose_name='State')
    residence_years = models.IntegerField(default=0, verbose_name='Years of Residence')
    purpose        = models.CharField(max_length=50, verbose_name='Purpose')

    # Workflow
    status         = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending', verbose_name='Application Status')
    certificate_no = models.CharField(max_length=50, blank=True, null=True, verbose_name='Certificate Number')
    review_notes   = models.TextField(blank=True, null=True, verbose_name='Review Notes / Rejection Reason')
    submitted_at   = models.DateTimeField(auto_now_add=True, verbose_name='Submitted At')
    reviewed_at    = models.DateTimeField(blank=True, null=True, verbose_name='Reviewed At')

    class Meta:
        verbose_name = 'Domicile Application'
        verbose_name_plural = 'Domicile Applications'
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.full_name} — Domicile [{self.get_status_display()}]"


class IncomeCertificateApplication(models.Model):
    STATUS_CHOICES = [
        ('pending',    'Pending Review'),
        ('processing', 'Under Processing'),
        ('approved',   'Approved'),
        ('rejected',   'Rejected'),
    ]

    INCOME_SOURCE_CHOICES = [
        ('agriculture', 'Agriculture / Farming'),
        ('business',    'Business / Self-Employed'),
        ('salary',      'Salary / Service'),
        ('pension',     'Pension'),
        ('other',       'Other'),
    ]

    # Applicant details
    user          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='income_applications')
    full_name     = models.CharField(max_length=100, verbose_name='Full Name')
    father_name   = models.CharField(max_length=100, blank=True, verbose_name="Father's / Spouse's Name")
    gender        = models.CharField(max_length=10, default='', verbose_name='Gender')
    dob           = models.DateField(verbose_name='Date of Birth')
    mobile        = models.CharField(max_length=15, verbose_name='Mobile Number')

    # Identity documents
    aadhaar       = models.CharField(max_length=20, blank=True, verbose_name='Aadhaar Number')
    pan_number    = models.CharField(max_length=15, blank=True, verbose_name='PAN Number')

    # Address
    address       = models.TextField(verbose_name='Permanent Address')
    district      = models.CharField(max_length=50, verbose_name='District')
    state         = models.CharField(max_length=50, verbose_name='State')

    # Income details
    annual_income = models.CharField(max_length=20, verbose_name='Annual Income (INR)')
    income_source = models.CharField(max_length=30, choices=INCOME_SOURCE_CHOICES, default='other', verbose_name='Source of Income')
    purpose       = models.CharField(max_length=100, verbose_name='Purpose of Certificate')

    # Workflow
    status         = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending', verbose_name='Application Status')
    certificate_no = models.CharField(max_length=50, blank=True, null=True, verbose_name='Certificate Number')
    review_notes   = models.TextField(blank=True, null=True, verbose_name='Review Notes / Rejection Reason')
    submitted_at   = models.DateTimeField(auto_now_add=True, verbose_name='Submitted At')
    reviewed_at    = models.DateTimeField(blank=True, null=True, verbose_name='Reviewed At')

    class Meta:
        verbose_name = 'Income Certificate Application'
        verbose_name_plural = 'Income Certificate Applications'
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.full_name} — Income [{self.get_status_display()}]"

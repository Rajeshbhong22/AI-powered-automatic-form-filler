from django.db import models
from django.contrib.auth.models import User

class DomicileApplication(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10)
    dob = models.DateField()
    mobile = models.CharField(max_length=15)
    aadhaar = models.CharField(max_length=20)
    address = models.TextField()
    district = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    residence_years = models.IntegerField()
    purpose = models.CharField(max_length=50)

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    certificate_no = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    

    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.status})"

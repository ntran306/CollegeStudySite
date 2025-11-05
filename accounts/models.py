from django.db import models
from django.contrib.auth.models import User

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    major = models.CharField(max_length=100, blank=True)
    year = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.user.username} (Student)"

class TutorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    subjects = models.TextField(blank=True)
    rate = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    bio = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.username} (Tutor)"

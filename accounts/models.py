from django.db import models
from django.contrib.auth.models import User


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    major = models.CharField(max_length=100, blank=True, null=True)
    year = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - Student"


class TutorProfile(models.Model):
    SUBJECT_CHOICES = [
        ('math', 'Mathematics'),
        ('science', 'Science'),
        ('english', 'English'),
        ('history', 'History'),
        ('computer_science', 'Computer Science'),
        ('engineering', 'Engineering'),
        ('economics', 'Economics'),
        ('psychology', 'Psychology'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    subjects = models.TextField(blank=True, null=True)
    rate = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)

    def get_subjects_list(self):
            """Return subjects as a Python list."""
            if self.subjects:
                return [s.strip() for s in self.subjects.split(',')]
            return []
    def __str__(self):
        return f"{self.user.username} - Tutor"

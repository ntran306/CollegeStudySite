from django.db import models
from django.contrib.auth.models import User

class TutoringSession(models.Model):
    tutor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tutor_sessions')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='student_sessions')
    subject = models.CharField(max_length=100)
    date = models.DateField()
    time = models.TimeField()
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.subject} - {self.date} ({self.tutor.username} tutoring {self.student.username})"

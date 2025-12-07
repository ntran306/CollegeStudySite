from django.db import models
from django.contrib.auth.models import User
from .utils import geocode_address
from classes.models import Class  # ✅ Add this import

class TutoringSession(models.Model):
    # Main fields
    tutor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tutor_sessions')
    
    # ✅ Change subject from CharField to ForeignKey
    subject = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='sessions')

    # Time fields
    date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    # Additional fields
    is_remote = models.BooleanField(default=False)
    capacity = models.PositiveIntegerField(default=1)
    description = models.TextField(blank=True)

    # Location fields
    location = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)    

    class Meta:
        ordering = ['-date', 'start_time']
    
    def __str__(self):
        return f"{self.subject.name} - {self.date} ({self.tutor.username})"
    
    def seats_taken(self):
        return self.requests.filter(status="approved").count()

    def is_full(self):
        return self.seats_taken() >= self.capacity
    
    def save(self, *args, **kwargs):
        """
        Override save to automatically geocode the location when:
        1. It's a new session (no pk yet)
        2. The location has changed
        3. The session is not remote
        """
        # Check if this is an update and if location changed
        location_changed = False
        if self.pk:  # Existing session
            try:
                old_instance = TutoringSession.objects.get(pk=self.pk)
                location_changed = (old_instance.location != self.location or 
                                  old_instance.is_remote != self.is_remote)
            except TutoringSession.DoesNotExist:
                pass
        else:  # New session
            location_changed = True
        
        # Geocode if location changed and session is not remote
        if location_changed and not self.is_remote and self.location and self.location.strip():
            # Don't geocode if location is explicitly "Remote" or similar
            if self.location.strip().lower() not in ['remote', 'online', 'virtual']:
                lat, lng = geocode_address(self.location)
                if lat and lng:
                    self.latitude = lat
                    self.longitude = lng
                    print(f"✅ Geocoded '{self.location}' to ({lat}, {lng})")
                else:
                    print(f"⚠️ Could not geocode location: '{self.location}'")
                    # Optionally clear coordinates if geocoding fails
                    self.latitude = None
                    self.longitude = None
        
        # Clear coordinates if marked as remote
        if self.is_remote:
            self.latitude = None
            self.longitude = None
        
        super().save(*args, **kwargs)


class SessionRequest(models.Model):
    STATUS = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("declined", "Declined"),
        ("canceled", "Canceled"),
    ]
    session = models.ForeignKey(TutoringSession, on_delete=models.CASCADE, related_name="requests")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="session_requests")
    note = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=STATUS, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("session", "student")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student.username} -> {self.session} [{self.status}]"
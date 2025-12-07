from django.db import models
from django.contrib.auth.models import User
from django.templatetags.static import static
from tutoringsession.utils import geocode_address
from classes.models import Class  # ✅ Add this import


def avatar_upload_path(instance, filename):
    return f"avatars/user_{instance.user_id}/{filename}"


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    major = models.CharField(max_length=100, blank=True, null=True)
    year = models.CharField(max_length=20, blank=True, null=True)
    school = models.CharField(max_length=120, blank=True, null=True)
    avatar = models.ImageField(upload_to=avatar_upload_path, blank=True, null=True)

    # Favorite study spot - help students connect (Can also technically be set to their home)
    location = models.CharField(max_length=255, blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)

    # ✅ Add classes field
    classes = models.ManyToManyField(Class, blank=True, related_name='students')

    def save(self, *args, **kwargs):
        """
        Override save to automatically geocode the location when:
        1. It's a new profile (no pk yet)
        2. The location has changed
        3. Coordinates are missing but location exists
        """
        if self.location and self.location.strip():
            should_geocode = False
            
            if self.pk:  # Existing record
                try:
                    old_instance = StudentProfile.objects.get(pk=self.pk)
                    location_changed = old_instance.location != self.location
                    coords_missing = not self.latitude or not self.longitude
                    
                    if location_changed or coords_missing:
                        should_geocode = True
                except StudentProfile.DoesNotExist:
                    should_geocode = True
            else:  # New record
                should_geocode = True
            
            if should_geocode:
                lat, lng = geocode_address(self.location)
                if lat and lng:
                    self.latitude = lat
                    self.longitude = lng
                    print(f"✅ Student geocoded '{self.location}' to ({lat}, {lng})")
                else:
                    print(f"⚠️ Could not geocode student location: '{self.location}'")
        
        super().save(*args, **kwargs)

    def avatar_url_or_default(self, request=None):
        if self.avatar:
            return request.build_absolute_uri(self.avatar.url) if request else self.avatar.url
        d = static("img/avatar-default.png")
        return request.build_absolute_uri(d) if request else d

    def __str__(self):
        return f"{self.user.username} - Student"


class TutorProfile(models.Model):
    
    classes = models.ManyToManyField(Class, blank=True, related_name='tutors')
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    subjects = models.TextField(blank=True, null=True) #mark for future
    rate = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    school = models.CharField(max_length=120, blank=True, null=True)
    avatar = models.ImageField(upload_to=avatar_upload_path, blank=True, null=True)

    # Optional for tutors to also have it since they can just set a general location
    location = models.CharField(max_length=255, blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)


    def save(self, *args, **kwargs):
        """
        Override save to automatically geocode the location when:
        1. It's a new profile (no pk yet)
        2. The location has changed
        3. Coordinates are missing but location exists
        """
        if self.location and self.location.strip():
            should_geocode = False
            
            if self.pk:  # Existing record
                try:
                    old_instance = TutorProfile.objects.get(pk=self.pk)
                    location_changed = old_instance.location != self.location
                    coords_missing = not self.latitude or not self.longitude
                    
                    if location_changed or coords_missing:
                        should_geocode = True
                except TutorProfile.DoesNotExist:
                    should_geocode = True
            else:  # New record
                should_geocode = True
            
            if should_geocode:
                lat, lng = geocode_address(self.location)
                if lat and lng:
                    self.latitude = lat
                    self.longitude = lng
                    print(f"✅ Tutor geocoded '{self.location}' to ({lat}, {lng})")
                else:
                    print(f"⚠️ Could not geocode tutor location: '{self.location}'")
        
        super().save(*args, **kwargs)

    def get_subjects_list(self):
        return [s.strip() for s in self.subjects.split(',')] if self.subjects else []

    def avatar_url_or_default(self, request=None):
        if self.avatar:
            return request.build_absolute_uri(self.avatar.url) if request else self.avatar.url
        d = static("img/avatar-default.png")
        return request.build_absolute_uri(d) if request else d

    def __str__(self):
        return f"{self.user.username} - Tutor"


class Friendship(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="friendships_from")
    friend = models.ForeignKey(User, on_delete=models.CASCADE, related_name="friendships_to")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "friend"], name="unique_friend_pair"),
        ]

    def save(self, *args, **kwargs):
        if self.user_id == self.friend_id:
            raise ValueError("Cannot friend yourself.")
        if self.user_id and self.friend_id and self.user_id > self.friend_id:
            self.user, self.friend = self.friend, self.user
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user} ↔ {self.friend}"


class FriendRequest(models.Model):
    PENDING  = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    CANCELED = "canceled"

    STATUS_CHOICES = [
        (PENDING,  "Pending"),
        (ACCEPTED, "Accepted"),
        (DECLINED, "Declined"),
        (CANCELED, "Canceled"),
    ]

    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_requests")
    to_user   = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_requests")
    status    = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["from_user", "to_user"], name="unique_friend_request"),
        ]

    def __str__(self):
        return f"{self.from_user} → {self.to_user} [{self.status}]"
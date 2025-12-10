from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import StudentProfile, TutorProfile, StudentClassSkill
from classes.models import Class
import json


class StudentSignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    major = forms.CharField(max_length=100, required=False)
    year = forms.CharField(max_length=20, required=False)
    location = forms.CharField(max_length=255, required=False)
    latitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    longitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    classes = forms.CharField(required=False, widget=forms.HiddenInput())
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            
            # Create student profile
            profile = StudentProfile.objects.create(
                user=user,
                major=self.cleaned_data.get('major', ''),
                year=self.cleaned_data.get('year', ''),
                location=self.cleaned_data.get('location', ''),
                latitude=self.cleaned_data.get('latitude'),
                longitude=self.cleaned_data.get('longitude'),
            )
            
            classes_data = self.cleaned_data.get('classes', '')
            if classes_data:
                try:
                    # Parse JSON: [{"id": 1, "skill_level": 3}, ...]
                    classes_list = json.loads(classes_data)
                    
                    for item in classes_list:
                        class_id = item.get('id')
                        skill_level = item.get('skill_level', 3)
                        if class_id:
                            StudentClassSkill.objects.create(
                                student=profile,
                                class_taken_id=class_id,
                                skill_level=skill_level
                            )
                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    print(f"Error parsing classes data: {e}")
        
        return user



class TutorSignUpForm(UserCreationForm):
    classes = forms.CharField(required=False, widget=forms.HiddenInput())
    
    rate = forms.DecimalField(
        max_digits=6,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter hourly rate',
            'min': '0',
            'step': '1',
        }),
        label="Hourly Rate ($)",
    )
    bio = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False
    )
    location = forms.CharField(
            max_length=255,
            required=False,
            widget=forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your city or campus'
            })
        )
    latitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    longitude = forms.FloatField(required=False, widget=forms.HiddenInput())

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            profile = TutorProfile.objects.create(
                user=user,
                rate=self.cleaned_data.get('rate'),
                bio=self.cleaned_data.get('bio', ''),
                location=self.cleaned_data.get('location', ''),
                latitude=self.cleaned_data.get('latitude') or None,
                longitude=self.cleaned_data.get('longitude') or None,
            )
            
            class_ids = self.cleaned_data.get('classes', '').split(',')
            valid_classes = Class.objects.filter(id__in=[c for c in class_ids if c.isdigit()])
            profile.classes.set(valid_classes)
            
        return user


class TutorProfileForm(forms.ModelForm):
    classes = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = TutorProfile
        fields = [
            'rate', 'bio', 'school',
            'location', 'latitude', 'longitude',
            'avatar',
        ]
        widgets = {
            'rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter hourly rate',
                'min': '0',
                'step': '1',
            }),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'school': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your school (optional)'}),
            'location': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Favorite study spot (optional)'}),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
        }

    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            profile.save()
            
            class_ids = self.cleaned_data.get('classes', '').split(',')
            valid_classes = Class.objects.filter(id__in=[c for c in class_ids if c.isdigit()])
            profile.classes.set(valid_classes)
            
        return profile


class StudentProfileForm(forms.ModelForm):
    classes = forms.CharField(required=False, widget=forms.HiddenInput())
    
    class Meta:
        model = StudentProfile
        fields = ['major', 'year', 'school', 'location', 'latitude', 'longitude', 'avatar']
        widgets = {
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
        }
    
    def save(self, commit=True):
        instance = super().save(commit=commit)
        
        if commit:
            
            classes_data = self.cleaned_data.get('classes', '')
            if classes_data:
                try:
                    # Parse JSON: [{"id": 1, "skill_level": 3}, ...]
                    classes_list = json.loads(classes_data)
                    
                    # Clear existing skills
                    StudentClassSkill.objects.filter(student=instance).delete()
                    
                    # Create new skills
                    for item in classes_list:
                        class_id = item.get('id')
                        skill_level = item.get('skill_level', 3)
                        if class_id:
                            StudentClassSkill.objects.create(
                                student=instance,
                                class_taken_id=class_id,
                                skill_level=skill_level
                            )
                except (json.JSONDecodeError, ValueError, KeyError) as e:
                    print(f"Error parsing classes data: {e}")
        
        return instance
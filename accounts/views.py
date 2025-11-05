from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from .forms import StudentSignUpForm, TutorSignUpForm
from .models import StudentProfile, TutorProfile

# ------------------------------------
# Sign-up Choice Page
# ------------------------------------
def signup_choice(request):
    return render(request, 'accounts/signup_choice.html')

# ------------------------------------
# Student Sign-Up
# ------------------------------------
def signup_student(request):
    if request.method == 'POST':
        form = StudentSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Student account created successfully!")
            return redirect('accounts:profile')
    else:
        form = StudentSignUpForm()
    return render(request, 'accounts/signup_student.html', {'form': form})

# ------------------------------------
# Tutor Sign-Up
# ------------------------------------
def signup_tutor(request):
    if request.method == 'POST':
        form = TutorSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Tutor account created successfully!")
            return redirect('accounts:profile')
    else:
        form = TutorSignUpForm()
    return render(request, 'accounts/signup_tutor.html', {'form': form})

# ------------------------------------
# Login & Logout
# ------------------------------------
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('accounts:profile')
        messages.error(request, "Invalid credentials.")
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('home:index')

# ------------------------------------
# Profile Page
# ------------------------------------
def profile_view(request):
    user = request.user
    student_profile = getattr(user, 'studentprofile', None)
    tutor_profile = getattr(user, 'tutorprofile', None)
    return render(request, 'accounts/profile.html', {
        'student_profile': student_profile,
        'tutor_profile': tutor_profile
    })

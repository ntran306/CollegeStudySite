from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from .forms import StudentSignUpForm, TutorSignUpForm
from .models import StudentProfile, TutorProfile
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .forms import TutorProfileForm
from .forms import TutorProfileForm, StudentProfileForm


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

# ------------------------------------
# Edit Profile
# ------------------------------------
@login_required
def edit_profile_view(request):
    # Determine if the user is a tutor or student
    tutor_profile = getattr(request.user, 'tutorprofile', None)
    student_profile = getattr(request.user, 'studentprofile', None)

    if tutor_profile:
        profile = tutor_profile
        form_class = TutorProfileForm
        profile_type = "Tutor"
    elif student_profile:
        profile = student_profile
        form_class = StudentProfileForm
        profile_type = "Student"
    else:
        # User has no profile yet (edge case)
        return redirect('accounts:signup_choice')

    if request.method == 'POST':
        form = form_class(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('accounts:profile')
    else:
        form = form_class(instance=profile)

    return render(request, 'accounts/edit_profile.html', {
        'form': form,
        'profile_type': profile_type,
    })
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from .forms import StudentSignUpForm, TutorSignUpForm
from .models import StudentProfile, TutorProfile, Friendship
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
# ------------------------------------
# Connections Page & View
# ------------------------------------
@login_required
def connect_list(request):
    tab = (request.GET.get('tab') or 'find').lower()
    q = (request.GET.get('q') or '').strip()

    pairs = Friendship.objects.filter(Q(user=request.user) | Q(friend=request.user))
    connected_ids = set()
    for f in pairs:
        connected_ids.add(f.user_id if f.user_id != request.user.id else f.friend_id)

    users = (
        User.objects
            .exclude(id=request.user.id)
            .exclude(id__in=connected_ids)
    )
    if q:
        users = users.filter(
            Q(username__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q)
        )
    users = users.order_by('username')

    friends = User.objects.filter(id__in=list(connected_ids)).order_by('username')

    ctx = {
        "users": users,
        "friends": friends,
        "query": q,
        "tab": "friends" if tab == "friends" else "find",
        "counts": {
            "find": users.count(),
            "friends": friends.count(),
        }
    }
    return render(request, "accounts/connect.html", ctx)

@login_required
def connect(request, user_id):
    target = get_object_or_404(User, id=user_id)
    if target == request.user:
        messages.error(request, "You cannot connect with yourself.")
        return redirect('accounts:connect')

    exists = Friendship.objects.filter(
        Q(user=request.user, friend=target) | Q(user=target, friend=request.user)
    ).exists()

    if exists:
        messages.info(request, f"You’re already connected with {target.username}.")
    else:
        Friendship.objects.create(user=request.user, friend=target)
        messages.success(request, f"You’re now connected with {target.username}!")
    return redirect('accounts:connect')
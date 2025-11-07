from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from .models import StudentProfile, TutorProfile, Friendship, FriendRequest
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .forms import TutorProfileForm, StudentProfileForm, TutorSignUpForm, StudentSignUpForm


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
        return redirect('accounts:signup_choice')

    if request.method == 'POST':
        form = form_class(request.POST, request.FILES, instance=profile)
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

    # Existing friendships (undirected)
    pairs = Friendship.objects.filter(Q(user=request.user) | Q(friend=request.user))
    connected_ids = set()
    for f in pairs:
        connected_ids.add(f.user_id if f.user_id != request.user.id else f.friend_id)

    # Users with any pending relation (either direction)
    pending_qs = FriendRequest.objects.filter(
        Q(from_user=request.user) | Q(to_user=request.user),
        status=FriendRequest.PENDING,
    )

    # Correct way to gather both columns into one set of IDs
    pending_with_ids = set()
    for fu, tu in pending_qs.values_list("from_user_id", "to_user_id"):
        pending_with_ids.add(fu)
        pending_with_ids.add(tu)

    # Base "Find" queryset: exclude self, existing friends, anyone with pending state
    users = (
        User.objects
        .exclude(id=request.user.id)
        .exclude(id__in=connected_ids)
        .exclude(id__in=pending_with_ids)
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

    # For the Pending tab + counts
    incoming = FriendRequest.objects.filter(
        to_user=request.user, status=FriendRequest.PENDING
    ).select_related("from_user").order_by("-created_at")

    outgoing = FriendRequest.objects.filter(
        from_user=request.user, status=FriendRequest.PENDING
    ).select_related("to_user").order_by("-created_at")

    ctx = {
        "users": users,
        "friends": friends,
        "query": q,
        "tab": "find" if tab not in ("find", "friends", "pending") else tab,
        "counts": {
            "find": users.count(),
            "friends": friends.count(),
            "pending_in": incoming.count(),
            "pending_out": outgoing.count(),
        },
    }

    # Only attach these when the template needs them
    if tab == "pending":
        ctx.update({"incoming": incoming, "outgoing": outgoing})

    return render(request, "accounts/connect.html", ctx)


@login_required
def connect_request(request, user_id):
    """Send a friend request (or auto-accept if the other person already requested you)."""
    target = get_object_or_404(User, id=user_id)
    if target == request.user:
        messages.error(request, "You cannot connect with yourself.")
        return redirect('accounts:connect')

    # already friends?
    exists = Friendship.objects.filter(
        Q(user=request.user, friend=target) | Q(user=target, friend=request.user)
    ).exists()
    if exists:
        messages.info(request, f"You’re already connected with {target.username}.")
        return redirect('accounts:connect')

    # if they already sent you a pending request, auto-accept
    incoming = FriendRequest.objects.filter(from_user=target, to_user=request.user, status=FriendRequest.PENDING).first()
    if incoming:
        # create the friendship (canonical order)
        u, v = (request.user, target)
        if u.id > v.id:
            u, v = v, u
        Friendship.objects.get_or_create(user=u, friend=v)
        incoming.status = FriendRequest.ACCEPTED
        incoming.save(update_fields=["status"])
        messages.success(request, f"You are now connected with {target.username}!")
        return redirect('accounts:connect')

    # otherwise, if you already sent them a pending request
    already_sent = FriendRequest.objects.filter(from_user=request.user, to_user=target, status=FriendRequest.PENDING).exists()
    if already_sent:
        messages.info(request, f"Request already sent to {target.username}.")
        return redirect('accounts:connect')

    # create a new friend request
    FriendRequest.objects.create(from_user=request.user, to_user=target)
    messages.success(request, f"Request sent to {target.username}.")
    return redirect('accounts:connect')


@login_required
def connect_requests(request):
    """Pending tab: show incoming & outgoing."""
    incoming = FriendRequest.objects.filter(to_user=request.user, status=FriendRequest.PENDING).select_related("from_user").order_by("-created_at")
    outgoing = FriendRequest.objects.filter(from_user=request.user, status=FriendRequest.PENDING).select_related("to_user").order_by("-created_at")

    return render(request, "accounts/connect_requests.html", {
        "incoming": incoming,
        "outgoing": outgoing,
    })


@login_required
def connect_accept(request, pk):
    if request.method != "POST":
        return redirect('accounts:connect_requests')
    fr = get_object_or_404(FriendRequest, pk=pk, to_user=request.user, status=FriendRequest.PENDING)
    # create friendship (canonical order)
    u, v = (fr.from_user, fr.to_user)
    if u.id > v.id:
        u, v = v, u
    Friendship.objects.get_or_create(user=u, friend=v)
    fr.status = FriendRequest.ACCEPTED
    fr.save(update_fields=["status"])
    messages.success(request, f"You are now connected with {fr.from_user.username}.")
    return redirect('accounts:connect_requests')


@login_required
def connect_decline(request, pk):
    if request.method != "POST":
        return redirect('accounts:connect_requests')
    fr = get_object_or_404(FriendRequest, pk=pk, to_user=request.user, status=FriendRequest.PENDING)
    fr.status = FriendRequest.DECLINED
    fr.save(update_fields=["status"])
    messages.info(request, f"Declined request from {fr.from_user.username}.")
    return redirect('accounts:connect_requests')


@login_required
def connect_cancel(request, pk):
    if request.method != "POST":
        return redirect('accounts:connect_requests')
    fr = get_object_or_404(FriendRequest, pk=pk, from_user=request.user, status=FriendRequest.PENDING)
    fr.status = FriendRequest.CANCELED
    fr.save(update_fields=["status"])
    messages.info(request, f"Canceled request to {fr.to_user.username}.")
    return redirect('accounts:connect_requests')
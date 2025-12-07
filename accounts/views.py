import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.conf import settings
from django.templatetags.static import static
from django.db.models import Q
from .models import StudentProfile, TutorProfile, Friendship, FriendRequest
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .forms import TutorProfileForm, StudentProfileForm, TutorSignUpForm, StudentSignUpForm
from tutoringsession.utils import haversine, batch_road_distance_and_time
from classes.models import Class


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
            messages.success(request, 'Student account created successfully!')
            return redirect('home:index')
    else:
        form = StudentSignUpForm()
    
    # ✅ Pass classes to template
    classes = list(Class.objects.values('id', 'name'))
    return render(request, 'accounts/signup_student.html', {
        'form': form,
        'classes': classes,
    })

# ------------------------------------
# Tutor Sign-Up
# ------------------------------------
def signup_tutor(request):
    if request.method == 'POST':
        form = TutorSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Tutor account created successfully!')
            return redirect('home:index')
    else:
        form = TutorSignUpForm()
    
    classes = list(Class.objects.values('id', 'name'))
    return render(request, 'accounts/signup_tutor.html', {
        'form': form,
        'classes': classes,
    })

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
def profile_view(request, username=None):
    # If username is provided, show that user's profile
    # Otherwise, show the logged-in user's profile
    if username:
        profile_user = get_object_or_404(User, username=username)
        is_own_profile = request.user.is_authenticated and request.user == profile_user
    else:
        # No username provided - must be logged in to view own profile
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        profile_user = request.user
        is_own_profile = True
    
    student_profile = getattr(profile_user, 'studentprofile', None)
    tutor_profile = getattr(profile_user, 'tutorprofile', None)
    
    return render(request, 'accounts/profile.html', {
        'profile_user': profile_user,
        'student_profile': student_profile,
        'tutor_profile': tutor_profile,
        'is_own_profile': is_own_profile,
    })

def _get_user_profile(u):
    sp = getattr(u, "studentprofile", None)
    if sp is not None:
        return sp, "student"
    tp = getattr(u, "tutorprofile", None)
    if tp is not None:
        return tp, "tutor"
    return None, None

# ------------------------------------
# Edit Profile
# ------------------------------------
@login_required
def edit_profile_view(request):
    # Determine profile type
    if hasattr(request.user, 'studentprofile'):
        profile = request.user.studentprofile
        form_class = StudentProfileForm
        profile_type = 'Student'
    elif hasattr(request.user, 'tutorprofile'):
        profile = request.user.tutorprofile
        form_class = TutorProfileForm
        profile_type = 'Tutor'
    else:
        messages.error(request, 'No profile found.')
        return redirect('accounts:profile')
    
    if request.method == 'POST':
        form = form_class(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
    else:
        form = form_class(instance=profile)
    
    context = {
        'form': form,
        'profile_type': profile_type,
    }
    
    # ✅ Add classes data for both student AND tutor profiles
    classes = list(Class.objects.values('id', 'name'))
    
    if profile_type == 'Student':
        current_classes = list(profile.classes.values('id', 'name'))
        context['classes'] = classes
        context['current_classes'] = current_classes
    elif profile_type == 'Tutor':
        current_classes = list(profile.classes.values('id', 'name'))
        context['classes'] = classes
        context['current_classes'] = current_classes
    
    return render(request, 'accounts/edit_profile.html', context)

# ------------------------------------
# Connections Page & View
# ------------------------------------
@login_required
def connect_list(request):
    tab = (request.GET.get('tab') or 'find').lower()
    q = (request.GET.get('q') or '').strip()
    users = []  # defensive init

    # Location/radius params
    location = (request.GET.get('location') or '').strip()
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    radius_raw = request.GET.get('radius') or ''
    try:
        radius_miles = max(1, int(radius_raw)) if radius_raw else 15
    except ValueError:
        radius_miles = 15

    # Existing friendships (undirected)
    pairs = Friendship.objects.filter(Q(user=request.user) | Q(friend=request.user))
    connected_ids = {f.user_id if f.user_id != request.user.id else f.friend_id for f in pairs}

    # Pending (either direction)
    pending_qs = FriendRequest.objects.filter(
        Q(from_user=request.user) | Q(to_user=request.user),
        status=FriendRequest.PENDING,
    )
    pending_with_ids = set()
    for fu, tu in pending_qs.values_list("from_user_id", "to_user_id"):
        pending_with_ids.add(fu)
        pending_with_ids.add(tu)

    # Base queryset
    users_qs = (
        User.objects
        .exclude(id=request.user.id)
        .exclude(id__in=connected_ids)
        .exclude(id__in=pending_with_ids)
        .select_related("studentprofile", "tutorprofile")
        .order_by("username")
    )

    # ✅ APPLY FILTERS BEFORE MATERIALIZING
    if q:
        users_qs = users_qs.filter(
            Q(username__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q)
        )

    if location and not (lat and lng):
        users_qs = users_qs.filter(
            Q(studentprofile__location__icontains=location) |
            Q(tutorprofile__location__icontains=location)
        )

    # Now materialize and attach a unified .profile
    users = list(users_qs)
    for u in users:
        sp = getattr(u, "studentprofile", None)
        tp = getattr(u, "tutorprofile", None)
        u.profile = sp if sp is not None else tp
        u.profile_role = "student" if sp is not None else ("tutor" if tp is not None else None)

    # Radius/road-distance filter (optional)
    if location and lat and lng:
        try:
            o_lat = float(lat); o_lng = float(lng)

            dests = []
            for u in users:
                p = getattr(u, "profile", None)
                if p and getattr(p, "latitude", None) is not None and getattr(p, "longitude", None) is not None:
                    dests.append((float(p.latitude), float(p.longitude), u.id))

            if dests:
                dm_results = batch_road_distance_and_time(
                    o_lat, o_lng, dests, use_traffic=True, traffic_model="best_guess"
                )
                kept = []
                for u in users:
                    res = dm_results.get(u.id)
                    if not res:
                        continue
                    dist = res.get("distance_miles")
                    if dist is None or dist > float(radius_miles):
                        continue
                    u.distance_miles = round(dist, 1)
                    drive_min = res.get("duration_in_traffic_minutes") or res.get("duration_minutes")
                    u.drive_minutes = round(drive_min, 1) if drive_min is not None else None
                    kept.append(u)

                users = sorted(
                    kept,
                    key=lambda x: (
                        x.distance_miles if getattr(x, "distance_miles", None) is not None else 1e9,
                        x.drive_minutes if getattr(x, "drive_minutes", None) is not None else 1e9,
                        x.username.lower(),
                    )
                )
            # else: nobody has coords → leave `users` as-is

        except ValueError:
            # bad coords; fallback to simple substring match in Python
            users = [
                u for u in users
                if getattr(u, "profile", None)
                and getattr(u.profile, "location", None)
                and location.lower() in u.profile.location.lower()
            ]

    # 🔎 Build map markers from ALL users with coordinates (not just filtered by location)
    # Get ALL potential users for the map (not filtered by search query)
    all_mappable_users = (
        User.objects
        .exclude(id=request.user.id)
        .exclude(id__in=connected_ids)
        .exclude(id__in=pending_with_ids)
        .select_related("studentprofile", "tutorprofile")
    )
    
    markers = []
    for u in all_mappable_users:
        sp = getattr(u, "studentprofile", None)
        tp = getattr(u, "tutorprofile", None)
        p = sp if sp is not None else tp
        
        if not p:
            continue
        if not getattr(p, "latitude", None) or not getattr(p, "longitude", None):
            continue
        if str(getattr(p, "location", "") or "").strip().lower() == "remote":
            continue
        
        markers.append({
            "id": u.id,
            "username": u.username,
            "study_location": p.location or "",
            "lat": float(p.latitude),
            "lng": float(p.longitude),
            "avatar": (p.avatar.url if getattr(p, "avatar", None) else static("img/avatar-placeholder.png")),
            "distance_miles": None,  # No distance calculation without origin
            "drive_minutes": None,
        })

    user_markers_json = json.dumps(markers)
    has_map_data = bool(markers)
    map_api_key = settings.GOOGLE_MAPS_API_KEY

    # Friends + pending (unchanged)
    friends = User.objects.filter(id__in=list(connected_ids)).order_by('username')
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
            "find": len(users),
            "friends": friends.count(),
            "pending_in": incoming.count(),
            "pending_out": outgoing.count(),
        },
        "request": request,  # so template can echo form values
        # map props for the template:
        "user_markers_json": user_markers_json,
        "has_map_data": has_map_data,
        "GOOGLE_MAPS_API_KEY": map_api_key,
    }
    if ctx["tab"] == "pending":
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
        messages.info(request, f"You're already connected with {target.username}.")
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
        return redirect('accounts:connect')
    fr = get_object_or_404(FriendRequest, pk=pk, to_user=request.user, status=FriendRequest.PENDING)
    # create friendship (canonical order)
    u, v = (fr.from_user, fr.to_user)
    if u.id > v.id:
        u, v = v, u
    Friendship.objects.get_or_create(user=u, friend=v)
    fr.status = FriendRequest.ACCEPTED
    fr.save(update_fields=["status"])
    messages.success(request, f"You are now connected with {fr.from_user.username}.")
    return redirect('accounts:connect')


@login_required
def connect_decline(request, pk):
    if request.method != "POST":
        return redirect('accounts:connect')
    fr = get_object_or_404(FriendRequest, pk=pk, to_user=request.user, status=FriendRequest.PENDING)
    fr.status = FriendRequest.DECLINED
    fr.save(update_fields=["status"])
    messages.info(request, f"Declined request from {fr.from_user.username}.")
    return redirect('accounts:connect')


@login_required
def connect_cancel(request, pk):
    if request.method != "POST":
        return redirect('accounts:connect')
    fr = get_object_or_404(FriendRequest, pk=pk, from_user=request.user, status=FriendRequest.PENDING)
    fr.status = FriendRequest.CANCELED
    fr.save(update_fields=["status"])
    messages.info(request, f"Canceled request to {fr.to_user.username}.")
    return redirect('accounts:connect')
from datetime import datetime
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from accounts.models import Friendship
from .models import TutoringSession, SessionRequest
from .utils import haversine
import json


REMOTE_TOKENS = {"remote", "online"}

def _parse_time(s: str):
    if not s:
        return None
    s = s.strip().lower()
    for fmt in ("%H:%M", "%I:%M%p", "%I:%M %p"):
        try:
            return datetime.strptime(s, fmt).time()
        except ValueError:
            continue
    return None

def index(request):
    qs = TutoringSession.objects.select_related("tutor").all()

    # --- basic text filters ---
    subject = (request.GET.get("subject") or "").strip()
    if subject:
        qs = qs.filter(subject__icontains=subject)

    tutor_q = (request.GET.get("tutor") or "").strip()
    if tutor_q:
        qs = qs.filter(
            Q(tutor__username__icontains=tutor_q) |
            Q(tutor__first_name__icontains=tutor_q) |
            Q(tutor__last_name__icontains=tutor_q)
        )

    # --- location / remote ---
    location = (request.GET.get("location") or "").strip()
    if location:
        if location.lower() in REMOTE_TOKENS:
            qs = qs.filter(is_remote=True)
        else:
            qs = qs.filter(location__icontains=location)

    # --- date ---
    date_str = (request.GET.get("date") or "").strip()
    if date_str:
        try:
            qs = qs.filter(date=datetime.strptime(date_str, "%Y-%m-%d").date())
        except ValueError:
            pass  # ignore bad date input

    # --- time containment ---
    # include sessions with NULL/Blank start/end as "any time"
    time_str = (request.GET.get("time") or "").strip()
    t = _parse_time(time_str)
    if t is not None:
        qs = qs.filter(
            Q(start_time__isnull=True) | Q(end_time__isnull=True) |
            (Q(start_time__lte=t) & Q(end_time__gte=t))
        )

    # --- capacity type ---
    capacity_type = (request.GET.get("capacity_type") or "").strip()
    if capacity_type == "one_on_one":
        qs = qs.filter(capacity=1)
    elif capacity_type == "group":
        qs = qs.filter(capacity__gt=1)

    include_full = request.GET.get("include_full") == "1"
    if not include_full:
        qs = [s for s in qs]
        qs = [s for s in qs if not s.is_full()]
    else:
        qs = list(qs)

    # --- Get user's location for distance calculations ---
    user_lat = None
    user_lng = None
    if request.user.is_authenticated and hasattr(request.user, 'latitude') and hasattr(request.user, 'longitude'):
        user_lat = request.user.latitude
        user_lng = request.user.longitude

    # --- markers for map ---
    markers = []
    has_map_data = False
    
    for s in qs:
        if s.latitude and s.longitude and not s.is_remote:
            # Calculate distance if user has location
            distance_miles = None
            if user_lat and user_lng:
                distance_miles = haversine(user_lng, user_lat, s.longitude, s.latitude)
            
            # Get tutor avatar (assuming tutor has profile with avatar)
            avatar_url = "/static/img/avatar-default.png"
            if hasattr(s.tutor, 'avatar') and s.tutor.avatar:
                avatar_url = s.tutor.avatar.url
            
            markers.append({
                "id": s.id,
                "lat": float(s.latitude),
                "lng": float(s.longitude),
                "title": s.subject,
                "location": s.location,
                "tutor": s.tutor.username,
                "date": s.date.isoformat() if s.date else "",
                "avatar": avatar_url,
                "distance_miles": round(distance_miles, 1) if distance_miles else None,
            })
            has_map_data = True

    # Convert markers to JSON for template
    markers_json = json.dumps(markers)

    return render(request, "tutoringsession/index.html", {
        "sessions": qs,
        "user_markers_json": markers_json,
        "has_map_data": has_map_data,
        "GOOGLE_MAPS_API_KEY": getattr(settings, "GOOGLE_MAPS_API_KEY", ""),
        "selected": {
            "subject": subject,
            "tutor": tutor_q,
            "location": location,
            "date": date_str,
            "time": time_str,
            "capacity_type": capacity_type,
            "include_full": "1" if include_full else "0",
        }
    })


def _friend_ids(user):
    pairs = Friendship.objects.filter(Q(user=user) | Q(friend=user)).values_list("user_id", "friend_id")
    ids = set()
    for u, f in pairs:
        ids.add(f if u == user.id else u)
    return ids


@login_required
def friends_sessions(request):
    friend_ids = _friend_ids(request.user)
    sessions = (
        TutoringSession.objects
        .filter(requests__student_id__in=friend_ids, requests__status__in=["approved", "pending"])
        .distinct()
    )
    return render(request, "tutoringsession/friends_sessions.html", {"sessions": sessions})

@login_required
def request_session(request, session_id):
    session = get_object_or_404(TutoringSession, id=session_id)

    # prevent joining if full (could technically just not show full, but you can at least view tutor and maybe connect?)
    if session.is_full():
        messages.error(request, "Sorry, this session is already full.")
        return redirect("tutoringsession:index")

    # avoid duplicate requests
    existing = SessionRequest.objects.filter(session=session, student=request.user).first()
    if existing:
        messages.info(request, f"You already have a request ({existing.status}).")
    else:
        SessionRequest.objects.create(session=session, student=request.user, status="pending")
        messages.success(request, "Request sent!")

    return redirect("tutoringsession:index")
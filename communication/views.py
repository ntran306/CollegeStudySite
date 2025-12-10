from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET
from django.http import JsonResponse
from django.db.models import Q
from twilio.base.exceptions import TwilioRestException
from accounts.models import StudentProfile, TutorProfile, Friendship
from . import services as dm
from .services import (
    create_twilio_access_token,
    get_or_create_conversation,
    ensure_participant,
    can_message,
    get_twilio_client,
    get_conversation_messages,
    get_other_user_in_conversation,
)

User = get_user_model()

# ===================================================================
# HELPER FUNCTIONS
# ===================================================================

def _can_message(viewer, target) -> bool:
    try:
        return can_message(viewer, target)
    except Exception:
        return viewer.id != target.id

def _get_profile_for_user_id(user_id: int):
    sp = StudentProfile.objects.select_related("user").filter(user_id=user_id).first()
    if sp:
        return sp
    return get_object_or_404(TutorProfile.objects.select_related("user"), user_id=user_id)

# ===================================================================
# API ENDPOINTS
# ===================================================================

@login_required
@require_GET
def get_twilio_token(request):
    try:
        token = create_twilio_access_token(request.user)
        if isinstance(token, (bytes, bytearray)):
            token = token.decode("utf-8")
        identity = f"user_{request.user.id}"
        return JsonResponse({
            "token": token,
            "identity": identity
        })
    except Exception as e:
        print(f"[get_twilio_token] Error: {e}")
        return JsonResponse({
            "error": "Failed to generate token"
        }, status=500)

@login_required
@login_required
def start_conversation(request, user_id: int):
    other = get_object_or_404(User, id=user_id)
    
    # Prevent self-messaging
    if other.id == request.user.id:
        return JsonResponse({
            "error": "Cannot message yourself."
        }, status=400)
    
    # Check friendship status
    if not _can_message(request.user, other):
        return JsonResponse({
            "error": "You must be friends with this user to message them."
        }, status=403)
    
    try:
        # Create or get conversation
        conv_sid = get_or_create_conversation(request.user.id, other.id)
        
        # Ensure both users are participants
        ensure_participant(conv_sid, request.user.id)
        ensure_participant(conv_sid, other.id)
        
        return JsonResponse({
            "ok": True,
            "conversation_sid": conv_sid,  # ← Changed from "sid" to "conversation_sid"
            "sid": conv_sid,  # ← Keep this for backward compatibility
            "other_id": other.id,
            "other_username": other.username,
            "friendly_name": other.username,
            "media_enabled": True
        })
        
    except TwilioRestException as e:
        print(f"[start_conversation] Twilio error: {e}")
        return JsonResponse({
            "ok": False,
            "error": f"Twilio API Error: {str(e)}"
        }, status=500)
        
    except Exception as e:
        print(f"[start_conversation] Error: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            "ok": False,
            "error": str(e)
        }, status=500)

@login_required
@require_GET
def list_conversations(request):
    """
    Returns all conversations where the current user is a participant.
    """
    client = get_twilio_client()
    identity = f"user_{request.user.id}"
    data = []

    try:
        # Get all conversations in the service
        svc = client.conversations.v1.services(dm.CONV_SERVICE_SID)
        all_conversations = svc.conversations.list(limit=100)
        
        print(f"[list_conversations] Found {len(all_conversations)} total conversations")
        
        # Filter for conversations where this user is a participant
        for conv in all_conversations:
            try:
                # Check if user is a participant in this conversation
                participants = conv.participants.list()
                participant_identities = [p.identity for p in participants]
                
                if identity not in participant_identities:
                    continue  # Skip this conversation
                
                print(f"[list_conversations] User is participant in {conv.sid}")
                
                # Get "other" user in this conversation (for 1-1 DMs)
                other_user = get_other_user_in_conversation(conv.sid, request.user.id)
                friendly_name = other_user["username"] if other_user else conv.sid

                # Fetch last message in this conversation
                last_list = conv.messages.list(limit=1, order='desc')
                last_msg = last_list[0] if last_list else None

                if last_msg:
                    last_body = last_msg.body or ""
                    last_author = last_msg.author
                    last_date = last_msg.date_created.isoformat() if last_msg.date_created else None
                else:
                    last_body = ""
                    last_author = None
                    last_date = None

                data.append({
                    "sid": conv.sid,
                    "friendly_name": friendly_name,
                    "other_user_id": other_user["user_id"] if other_user else None,
                    "other_username": other_user["username"] if other_user else None,

                    # Preview fields
                    "last_message_body": last_body,
                    "last_message_author": last_author,
                    "last_message_date_created": last_date,
                })

            except Exception as e:
                print(f"[list_conversations] Error processing conversation {conv.sid}: {e}")
                import traceback
                traceback.print_exc()
                continue

        print(f"[list_conversations] Returning {len(data)} conversations for user {request.user.id}")
        return JsonResponse({"conversations": data})

    except TwilioRestException as e:
        print(f"[list_conversations] Twilio error: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"conversations": []})

    except Exception as e:
        print(f"[list_conversations] Error: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"conversations": []})

@login_required
@require_GET
def conversation_view(request, conversation_sid: str):
    client = get_twilio_client()
    identity = f"user_{request.user.id}"
    
    try:
        # Fetch conversation
        conv = client.conversations.v1.services(dm.CONV_SERVICE_SID)\
            .conversations(conversation_sid).fetch()
        
        # Verify user is a participant
        participants = conv.participants.list()
        participant_identities = [p.identity for p in participants]
        
        if identity not in participant_identities:
            print(f"[conversation_view] Unauthorized access attempt by {identity}")
            return JsonResponse({"error": "Unauthorized"}, status=403)
        
        # Get other user info
        other_user = get_other_user_in_conversation(conversation_sid, request.user.id)
        friendly_name = other_user['username'] if other_user else conv.sid
        
        return JsonResponse({
            "sid": conv.sid,
            "friendly_name": friendly_name,
            "other_user_id": other_user['user_id'] if other_user else None,
            "other_username": other_user['username'] if other_user else None,
            "media_enabled": True,
        })
        
    except TwilioRestException as e:
        return JsonResponse({"error": str(e)}, status=404)
        
    except Exception as e:
        print(f"[conversation_view] Error: {e}")
        return JsonResponse({"error": "Internal error"}, status=500)

@login_required
@require_GET
def get_messages(request, conversation_sid: str):
    client = get_twilio_client()
    identity = f"user_{request.user.id}"
    
    try:
        # Verify user is a participant
        conv = client.conversations.v1.services(dm.CONV_SERVICE_SID)\
            .conversations(conversation_sid).fetch()
        
        participants = conv.participants.list()
        participant_identities = [p.identity for p in participants]
        
        if identity not in participant_identities:
            return JsonResponse({"error": "Unauthorized"}, status=403)
        
        # Get message limit from query params
        limit = int(request.GET.get('limit', 50))
        limit = min(limit, 100)  # Cap at 100
        
        # Fetch messages with media
        messages = get_conversation_messages(conversation_sid, limit=limit)
        
        return JsonResponse({
            "messages": messages,
            "count": len(messages)
        })
        
    except TwilioRestException as e:
        return JsonResponse({"error": str(e)}, status=404)
        
    except Exception as e:
        print(f"[get_messages] Error: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": "Internal error"}, status=500)

@login_required
@require_GET
def get_other_user(request, conversation_sid: str):
    client = get_twilio_client()
    identity = f"user_{request.user.id}"
    
    try:
        # Verify user is a participant
        conv = client.conversations.v1.services(dm.CONV_SERVICE_SID)\
            .conversations(conversation_sid).fetch()
        
        participants = conv.participants.list()
        participant_identities = [p.identity for p in participants]
        
        if identity not in participant_identities:
            return JsonResponse({"error": "Unauthorized"}, status=403)
        
        # Get other user from conversation attributes
        other_user = get_other_user_in_conversation(conversation_sid, request.user.id)
        
        if not other_user:
            return JsonResponse({
                "error": "Could not find other user"
            }, status=404)
        
        # Fetch full user details from database
        try:
            user = User.objects.get(id=other_user['user_id'])
            
            # Get profile - try both student and tutor
            student_profile = getattr(user, 'studentprofile', None)
            tutor_profile = getattr(user, 'tutorprofile', None)
            profile = student_profile or tutor_profile
            
            avatar_url = None
            if profile and hasattr(profile, 'avatar') and profile.avatar:
                avatar_url = request.build_absolute_uri(profile.avatar.url)
            
            return JsonResponse({
                "user_id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "avatar_url": avatar_url,
                "profile_type": "student" if student_profile else ("tutor" if tutor_profile else "none")
            })
            
        except User.DoesNotExist:
            # Fallback to just username if user not found
            return JsonResponse({
                "user_id": other_user['user_id'],
                "username": other_user['username'],
                "avatar_url": None,
            })
        
    except TwilioRestException as e:
        print(f"[get_other_user] Twilio error: {e}")
        return JsonResponse({"error": str(e)}, status=404)
        
    except Exception as e:
        print(f"[get_other_user] Error: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": "Internal error"}, status=500)
    
@login_required
def get_friends_list(request):
    """
    Returns a list of all friends with their basic info.
    """
    try:
        # Get all friendships where the user is involved
        friendships = Friendship.objects.filter(
            Q(user=request.user) | Q(friend=request.user)
        ).select_related('user', 'friend')
        
        friends = []
        for friendship in friendships:
            # Determine which user is the friend
            friend_user = friendship.friend if friendship.user == request.user else friendship.user
            
            # Get profile for avatar
            student_profile = getattr(friend_user, 'studentprofile', None)
            tutor_profile = getattr(friend_user, 'tutorprofile', None)
            profile = student_profile or tutor_profile
            
            avatar_url = None
            if profile and hasattr(profile, 'avatar') and profile.avatar:
                avatar_url = request.build_absolute_uri(profile.avatar.url)
            
            friends.append({
                'id': friend_user.id,
                'username': friend_user.username,
                'first_name': friend_user.first_name,
                'last_name': friend_user.last_name,
                'avatar_url': avatar_url,
            })
        
        # Sort by username
        friends.sort(key=lambda x: x['username'].lower())
        
        return JsonResponse({'friends': friends})
    
    except Exception as e:
        print(f"Error getting friends list: {e}")
        return JsonResponse({'error': str(e), 'friends': []}, status=500)
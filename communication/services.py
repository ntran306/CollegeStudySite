import os
import json
from django.contrib.auth import get_user_model
from twilio.rest import Client
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import ChatGrant
from twilio.base.exceptions import TwilioRestException
from accounts.models import Friendship

# basically just env variables but easier declaration
ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
API_KEY_SID = os.environ.get("TWILIO_API_KEY_SID")
API_KEY_SECRET = os.environ.get("TWILIO_API_KEY_SECRET")
CONV_SERVICE_SID = os.environ.get("TWILIO_CONVERSATIONS_SERVICE_SID")

User = get_user_model()

def get_twilio_client():
    if not all([ACCOUNT_SID, AUTH_TOKEN]):
        raise RuntimeError("Twilio ACCOUNT_SID/AUTH_TOKEN missing")
    return Client(ACCOUNT_SID, AUTH_TOKEN)

def _unique_name_for_pair(a_id: int, b_id: int) -> str:
    lo, hi = sorted([int(a_id), int(b_id)])
    return f"userpair_{lo}_{hi}"

def create_twilio_access_token(django_user) -> str:
    if not all([ACCOUNT_SID, API_KEY_SID, API_KEY_SECRET, CONV_SERVICE_SID]):
        raise RuntimeError("Twilio API key or service SID missing")

    identity = f"user_{django_user.id}"
    token = AccessToken(ACCOUNT_SID, API_KEY_SID, API_KEY_SECRET, identity=identity)
    token.ttl = 3600
    grant = ChatGrant(service_sid=CONV_SERVICE_SID)
    token.add_grant(grant)
    jwt = token.to_jwt()
    return jwt.decode("utf-8") if isinstance(jwt, (bytes, bytearray)) else jwt

def get_or_create_conversation(a_id: int, b_id: int) -> str:
    client = get_twilio_client()
    unique = _unique_name_for_pair(a_id, b_id)
    
    try:
        user_a = User.objects.get(id=a_id)
        user_b = User.objects.get(id=b_id)
        username_a = user_a.username
        username_b = user_b.username
    except User.DoesNotExist:
        username_a = f"User{a_id}"
        username_b = f"User{b_id}"
    
    attributes = {
        f"user_{a_id}": username_a,
        f"user_{b_id}": username_b,
        "type": "direct_message"
    }
    attributes_json = json.dumps(attributes)
    
    try:
        svc = client.conversations.v1.services(CONV_SERVICE_SID)
        for conv in svc.conversations.list(limit=1000):
            if getattr(conv, "unique_name", None) == unique:
                try:
                    client.conversations.v1.services(CONV_SERVICE_SID)\
                        .conversations(conv.sid).update(attributes=attributes_json)
                except Exception:
                    pass
                return conv.sid
    except Exception:
        pass
    
    try:
        svc = client.conversations.v1.services(CONV_SERVICE_SID)
        conv = svc.conversations.create(
            unique_name=unique,
            attributes=attributes_json,
            friendly_name=f"{username_a} & {username_b}"
        )
        return conv.sid
    except TwilioRestException as e:
        if getattr(e, "status", None) == 409:
            svc = client.conversations.v1.services(CONV_SERVICE_SID)
            for conv in svc.conversations.list(limit=1000):
                if getattr(conv, "unique_name", None) == unique:
                    return conv.sid
        raise

def ensure_participant(conversation_sid: str, user_id: int):
    identity = f"user_{user_id}"
    client = get_twilio_client()
    
    try:
        svc = client.conversations.v1.services(CONV_SERVICE_SID)
        svc.conversations(conversation_sid).participants.create(identity=identity)
    except TwilioRestException as e:
        error_msg = str(e).lower()
        if getattr(e, "status", None) == 409 or "already" in error_msg or "exists" in error_msg:
            return
        raise

def get_conversation_messages(conversation_sid: str, limit: int = 50):
    client = get_twilio_client()
    
    try:
        svc = client.conversations.v1.services(CONV_SERVICE_SID)
        messages = svc.conversations(conversation_sid).messages.list(limit=limit)
        
        result = []
        for msg in messages:
            message_data = {
                "sid": msg.sid,
                "author": msg.author,
                "body": msg.body,
                "date_created": msg.date_created.isoformat() if msg.date_created else None,
                "media": []
            }
            
            if hasattr(msg, 'media') and msg.media:
                try:
                    media_list = svc.conversations(conversation_sid)\
                        .messages(msg.sid).media.list()
                    
                    for media in media_list:
                        message_data["media"].append({
                            "sid": media.sid,
                            "content_type": media.content_type,
                            "size": media.size,
                            "filename": media.filename,
                        })
                except Exception:
                    pass
            
            result.append(message_data)
        
        return result
    except Exception as e:
        raise

def can_message(viewer_user, target_user) -> bool:
    if viewer_user.id == target_user.id:
        return False
    return is_friends(viewer_user.id, target_user.id)

def is_friends(a_id: int, b_id: int) -> bool:
    lo, hi = sorted([a_id, b_id])
    return Friendship.objects.filter(user_id=lo, friend_id=hi).exists()

def get_other_user_in_conversation(conversation_sid: str, current_user_id: int):
    """
    Try to find the 'other' user in a 1–1 conversation.

    Priority:
      1. Use conversation.attributes (our preferred schema).
      2. Fallback to Twilio participants: identity = 'user_<id>'.
    """
    client = get_twilio_client()

    try:
        svc = client.conversations.v1.services(CONV_SERVICE_SID)
        conv = svc.conversations(conversation_sid).fetch()

        # ----- 1) Try attributes (preferred) -----
        if getattr(conv, "attributes", None):
            try:
                attrs = json.loads(conv.attributes)
                for key, username in attrs.items():
                    if key.startswith("user_") and key != f"user_{current_user_id}":
                        other_user_id = int(key.replace("user_", ""))
                        return {"user_id": other_user_id, "username": username}
            except Exception as e:
                print(f"[get_other_user_in_conversation] attribute parse failed: {e}")

        # ----- 2) Fallback: inspect participants -----
        try:
            participants = svc.conversations(conversation_sid).participants.list()
            for p in participants:
                identity = getattr(p, "identity", None)
                if not identity:
                    continue
                if not identity.startswith("user_"):
                    continue

                try:
                    uid = int(identity.replace("user_", ""))
                except ValueError:
                    continue

                if uid == current_user_id:
                    continue

                # Try to resolve username from Django user
                try:
                    user = User.objects.get(id=uid)
                    username = user.username
                except User.DoesNotExist:
                    username = identity  # fallback to identity string

                return {"user_id": uid, "username": username}
        except Exception as e:
            print(f"[get_other_user_in_conversation] participant fallback failed: {e}")

        return None

    except Exception as e:
        print(f"[get_other_user_in_conversation] Error: {e}")
        return None
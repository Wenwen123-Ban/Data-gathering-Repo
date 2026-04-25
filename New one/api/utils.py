import json
import threading
from datetime import datetime
from django.forms.models import model_to_dict
from django.http import JsonResponse

# Thread-safe in-memory session store { school_id: { token, expires } }
# Uses a lock so concurrent requests don't corrupt state
_SESSION_LOCK = threading.Lock()
ACTIVE_SESSIONS = {}
SESSION_HOURS = 2


def parse_json_body(request):
    try:
        return json.loads(request.body.decode('utf-8') or '{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def list_response(queryset):
    return JsonResponse([model_to_dict(obj) for obj in queryset], safe=False)


def get_token(request):
    # Accept token from Authorization header OR from X-Token header (fallback)
    token = request.headers.get('Authorization', '').strip()
    if not token:
        token = request.headers.get('X-Token', '').strip()
    return token


def _lookup_session(token):
    """Find uid for a valid token. Returns uid or None. Thread-safe."""
    if not token:
        return None
    now = datetime.now()
    with _SESSION_LOCK:
        expired = [uid for uid, sess in ACTIVE_SESSIONS.items()
                   if isinstance(sess, dict) and now >= sess.get('expires', datetime.min)]
        for uid in expired:
            del ACTIVE_SESSIONS[uid]
        for uid, sess in ACTIVE_SESSIONS.items():
            if isinstance(sess, dict) and sess.get('token') == token:
                return uid
    return None


def store_session(school_id, token, expires, is_staff=False):
    """Store a session. Thread-safe. Caches is_staff to avoid DB hit per request."""
    with _SESSION_LOCK:
        ACTIVE_SESSIONS[school_id] = {'token': token, 'expires': expires, 'is_staff': bool(is_staff)}


def remove_session(token):
    """Remove a session by token. Thread-safe."""
    with _SESSION_LOCK:
        for uid, sess in list(ACTIVE_SESSIONS.items()):
            if isinstance(sess, dict) and sess.get('token') == token:
                del ACTIVE_SESSIONS[uid]
                break


def require_auth(request):
    token = get_token(request)
    uid = _lookup_session(token)
    if uid:
        return uid
    # Session cookie fallback
    session_id = request.session.get('admin_school_id', '')
    if session_id:
        return session_id
    return None


def require_admin(request):
    token = get_token(request)
    uid = _lookup_session(token)
    if uid:
        # Check cached is_staff first — no MySQL hit needed
        with _SESSION_LOCK:
            sess = ACTIVE_SESSIONS.get(uid, {})
        if sess.get('is_staff'):
            return uid
        # Fallback: verify from DB (handles sessions created before this fix)
        try:
            from core.models import UserProfile
            user = UserProfile.objects.get(school_id=uid)
            if user.is_staff:
                # Update cache for next time
                with _SESSION_LOCK:
                    if uid in ACTIVE_SESSIONS:
                        ACTIVE_SESSIONS[uid]['is_staff'] = True
                return uid
        except Exception:
            pass

    # Session cookie fallback (no DB hit needed if is_admin flag set)
    admin_id = request.session.get('admin_school_id', '')
    if admin_id and request.session.get('is_admin'):
        return admin_id
    return None


def unauth():
    return JsonResponse({'success': False, 'message': 'Unauthorized — please log in as admin'}, status=401)

import os as _os
from django.conf import settings as _settings

_AVATARS_SET = {
    'avatar_fox.svg','avatar_bear.svg','avatar_rabbit.svg','avatar_cat.svg',
    'avatar_dog.svg','avatar_panda.svg','avatar_owl.svg','avatar_penguin.svg',
    'default.png',
}

def resolve_photo(photo):
    """Return photo filename if it exists on disk, else 'default.png'."""
    if not photo or photo in (None, 'None', 'null', ''):
        return 'default.png'
    # Known avatars always resolve without disk check
    if photo in _AVATARS_SET:
        return photo
    # For uploaded files (reg_*.jpg, etc.) verify the file actually exists
    full_path = _os.path.join(_settings.MEDIA_ROOT, photo)
    if _os.path.isfile(full_path):
        return photo
    return 'default.png'


import uuid
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from core.models import UserProfile
from .utils import parse_json_body, require_admin, store_session, remove_session, SESSION_HOURS, resolve_photo


@csrf_exempt
def api_login(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    data = parse_json_body(request)
    s_id = str(data.get('school_id', '')).strip().lower()
    pwd = str(data.get('password', '')).strip()
    id_only = bool(data.get('id_only', False))

    # Try JSON store first (always available), fall back to MySQL
    from .store import find_user as _find_user
    user = _find_user(s_id)
    if not user:
        # Try MySQL fallback
        try:
            db_user = UserProfile.objects.get(school_id=s_id)
            user = {
                'school_id': db_user.school_id, 'name': db_user.name,
                'password': db_user.password, 'is_staff': db_user.is_staff,
                'status': db_user.status, 'photo': db_user.photo,
                'category': db_user.category, 'year_level': db_user.year_level,
                'school_level': db_user.school_level, 'course': db_user.course,
                'phone_number': db_user.phone_number, 'email': getattr(db_user, 'email', ''),
            }
        except Exception:
            pass
    if not user:
        return JsonResponse({'success': False, 'ok': False, 'message': 'ID not found'}, status=404)

    if str(user.get('status', 'approved')).lower() == 'pending':
        return JsonResponse({'success': False, 'ok': False, 'message': 'Account Pending Approval'}, status=401)

    if not id_only and user.get('password') != pwd:
        return JsonResponse({'success': False, 'ok': False, 'message': 'Invalid Password'}, status=401)

    token = str(uuid.uuid4())
    expires = datetime.now() + timedelta(hours=SESSION_HOURS)
    store_session(s_id, token, expires, is_staff=bool(user.get('is_staff')))

    if user.get('is_staff'):
        request.session['is_admin'] = True
        request.session['admin_school_id'] = s_id

    profile = {
        'name': user.get('name', ''),
        'school_id': user.get('school_id', s_id),
        'photo': resolve_photo(user.get('photo', 'default.png')),
        'is_staff': bool(user.get('is_staff')),
        'category': user.get('category', 'Student'),
        'status': user.get('status', 'approved'),
        'year_level': user.get('year_level', ''),
        'school_level': user.get('school_level', ''),
        'course': user.get('course', ''),
        'phone_number': user.get('phone_number', ''),
        'email': user.get('email', ''),
    }
    return JsonResponse({'success': True, 'ok': True, 'token': token, 'profile': profile})


@csrf_exempt
def api_logout(request):
    request.session.flush()
    token = request.headers.get('Authorization', '').strip()
    remove_session(token)   # thread-safe remove
    return JsonResponse({'success': True})

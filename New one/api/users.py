
import random as _random
_AVATARS = ['avatar_fox.svg','avatar_bear.svg','avatar_rabbit.svg','avatar_cat.svg',
            'avatar_dog.svg','avatar_panda.svg','avatar_owl.svg','avatar_penguin.svg']
def _pick_avatar(): return _random.choice(_AVATARS)
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from core.models import UserProfile
from .utils import parse_json_body, require_auth, require_admin, unauth, resolve_photo


def _u(u):
    return {
        'school_id': u.school_id, 'name': u.name, 'category': u.category,
        'photo': resolve_photo(u.photo), 'status': u.status, 'is_staff': u.is_staff,
        'phone_number': u.phone_number, 'email': getattr(u, 'email', ''), 'year_level': u.year_level,
        'school_level': u.school_level, 'course': u.course,
    }


def api_get_users(request):
    if not require_auth(request):
        return unauth()
    return JsonResponse([_u(u) for u in UserProfile.objects.filter(is_staff=False).order_by('school_id')], safe=False)


def api_get_admins(request):
    if not require_auth(request):
        return unauth()
    return JsonResponse([_u(u) for u in UserProfile.objects.filter(is_staff=True).order_by('school_id')], safe=False)


def api_admin_get_users(request):
    from .store import get_users
    return JsonResponse(get_users(), safe=False)


def api_admin_get_admins(request):
    from .store import get_admins
    return JsonResponse(get_admins(), safe=False)


def api_get_user(request, school_id):
    try:
        u = UserProfile.objects.get(school_id=str(school_id).strip().lower())
        return JsonResponse({'success': True, 'profile': _u(u)})
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False}, status=404)


@csrf_exempt
def api_register_student(request):
    # This endpoint is called from admin Quick Register panel
    # Verify admin token is present (sent via Authorization header by apiFetch)
    # Falls back gracefully if called without token (e.g. legacy)
    name = request.POST.get('name', '').strip()
    school_id = request.POST.get('school_id', '').strip().lower()
    password = request.POST.get('password', '').strip()
    year_level = request.POST.get('year_level', '').strip()
    school_level = request.POST.get('school_level', 'college').strip()
    course = request.POST.get('course', '').strip() or 'N/A'
    phone_number = request.POST.get('phone_number', '').strip()
    email = request.POST.get('email', '').strip()
    if not name or not school_id or not password:
        return JsonResponse({'success': False, 'message': 'Missing required fields (name, ID, password)'}, status=400)
    if UserProfile.objects.filter(school_id=school_id).exists():
        return JsonResponse({'success': False, 'message': f'ID "{school_id}" already exists'}, status=409)
    # Respect avatar chosen in admin picker, or pick random
    allowed_avatars = [f'avatar_{a}.svg' for a in ['fox','bear','rabbit','cat','dog','panda','owl','penguin']]
    avatar_hint = request.POST.get('avatar_hint', '').strip()
    chosen_photo = avatar_hint if avatar_hint in allowed_avatars else _pick_avatar()
    UserProfile.objects.create(
        school_id=school_id, name=name, password=password,
        category='Student', is_staff=False, status='approved',
        year_level=year_level, school_level=school_level, course=course,
        photo=chosen_photo, phone_number=phone_number, email=email,
    )
    return JsonResponse({'success': True, 'message': f'Student {name} created successfully'})


@csrf_exempt
def api_register_librarian(request):
    name = request.POST.get('name', '').strip()
    school_id = request.POST.get('school_id', '').strip().lower()
    password = request.POST.get('password', '').strip()
    if not name or not school_id or not password:
        return JsonResponse({'success': False, 'message': 'Missing required fields (name, ID, password)'}, status=400)
    if UserProfile.objects.filter(school_id=school_id).exists():
        return JsonResponse({'success': False, 'message': f'ID "{school_id}" already exists'}, status=409)
    UserProfile.objects.create(
        school_id=school_id, name=name, password=password,
        category='Staff', is_staff=True, status='approved',
        photo=_pick_avatar(),
    )
    return JsonResponse({'success': True, 'message': f'Admin {name} created successfully'})


@csrf_exempt
def api_update_member(request):
    if not require_auth(request):
        return unauth()
    data = parse_json_body(request)
    school_id = str(data.get('school_id', '')).strip().lower()
    try:
        user = UserProfile.objects.get(school_id=school_id)
        for field in ('name', 'phone_number', 'email', 'year_level', 'school_level', 'course', 'photo'):
            if field in data:
                setattr(user, field, data[field])
        if 'password' in data and data['password']:
            user.password = data['password']
        user.save()
        return JsonResponse({'success': True})
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Not found'}, status=404)


@csrf_exempt
def api_delete_member(request):
    if not require_auth(request):
        return unauth()
    data = parse_json_body(request)
    school_id = str(data.get('school_id', '')).strip().lower()
    role = str(data.get('type', '')).strip().lower()
    if school_id == 'admin':
        return JsonResponse({'success': False, 'message': 'Cannot delete system admin'}, status=403)
    deleted, _ = UserProfile.objects.filter(school_id=school_id).delete()
    return JsonResponse({'success': bool(deleted)})


@csrf_exempt
def api_update_profile_photo(request):
    """Let a logged-in user update their own profile photo (upload file or choose avatar)."""
    from .utils import require_auth
    uid = require_auth(request)
    if not uid:
        return unauth()
    
    avatar = request.POST.get('avatar', '').strip()   # e.g. "avatar_fox.svg"
    photo_file = request.FILES.get('photo')

    try:
        user = UserProfile.objects.get(school_id=uid)
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'User not found'}, status=404)

    if avatar:
        # Pick a preset animal avatar
        allowed = [f'avatar_{a}.svg' for a in ['fox','bear','rabbit','cat','dog','panda','owl','penguin']]
        if avatar not in allowed:
            return JsonResponse({'success': False, 'message': 'Invalid avatar'}, status=400)
        user.photo = avatar
        user.save()
        return JsonResponse({'success': True, 'photo': avatar})

    if photo_file:
        import os
        from django.conf import settings
        ext = os.path.splitext(photo_file.name)[1].lower() or '.jpg'
        photo_name = f'{uid}{ext}'
        save_path = os.path.join(settings.MEDIA_ROOT, photo_name)
        with open(save_path, 'wb') as f:
            for chunk in photo_file.chunks():
                f.write(chunk)
        user.photo = photo_name
        user.save()
        return JsonResponse({'success': True, 'photo': photo_name})

    return JsonResponse({'success': False, 'message': 'No photo or avatar provided'}, status=400)

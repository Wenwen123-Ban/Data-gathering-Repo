import random as _random
_AVATARS = ['avatar_fox.svg','avatar_bear.svg','avatar_rabbit.svg','avatar_cat.svg',
            'avatar_dog.svg','avatar_panda.svg','avatar_owl.svg','avatar_penguin.svg']
def _pick_avatar(): return _random.choice(_AVATARS)

import uuid
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from core.models import RegistrationRequest, UserProfile
from .utils import parse_json_body, require_auth, require_admin, unauth, resolve_photo


def _r(r):
    return {
        'request_id': r.request_id, 'request_number': r.request_number,
        'name': r.name, 'school_id': r.school_id, 'year_level': r.year_level,
        'school_level': r.school_level, 'course': r.course,
        'photo': resolve_photo(r.photo), 'status': r.status, 'reviewed_by': r.reviewed_by,
        'phone_number': r.phone_number, 'email': r.email,
        'created_at': str(r.created_at)[:16],
    }


@csrf_exempt
def api_register_request(request):
    name = request.POST.get('name', '').strip()
    school_id = request.POST.get('school_id', '').strip().lower()
    year_level = request.POST.get('year_level', '').strip()
    school_level = request.POST.get('school_level', '').strip()
    course = request.POST.get('course', '').strip() or 'N/A'
    phone_number = request.POST.get('phone_number', '').strip()
    email = request.POST.get('email', '').strip()
    password = request.POST.get('password', '').strip()
    if not all([name, school_id, year_level, school_level, password]):
        return JsonResponse({'success': False, 'message': 'All fields required'}, status=400)
    if not phone_number and not email:
        return JsonResponse({'success': False, 'message': 'At least one contact (phone or email) is required'}, status=400)
    if UserProfile.objects.filter(school_id=school_id).exists():
        return JsonResponse({'success': False, 'message': 'ID already registered'}, status=409)
    if RegistrationRequest.objects.filter(school_id=school_id, status='pending').exists():
        return JsonResponse({'success': False, 'message': 'Pending request already exists'}, status=409)
    # Photo: respect avatar_hint from picker, else assign random avatar
    # File uploads are no longer used in signup (avatar system replaced them)
    import os
    from django.conf import settings as _cfg
    _ALLOWED_AVATARS = [f'avatar_{a}.svg' for a in ['fox','bear','rabbit','cat','dog','panda','owl','penguin']]
    avatar_hint = request.POST.get('avatar_hint', '').strip()
    if avatar_hint in _ALLOWED_AVATARS:
        photo_name = avatar_hint
    else:
        photo_name = _pick_avatar()
    # Legacy: still accept file upload if provided, verify it saves successfully
    photo_file = request.FILES.get('photo')
    if photo_file:
        ext = os.path.splitext(photo_file.name)[1].lower() or '.jpg'
        candidate = f'reg_{school_id}{ext}'
        try:
            os.makedirs(_cfg.MEDIA_ROOT, exist_ok=True)
            save_path = os.path.join(_cfg.MEDIA_ROOT, candidate)
            with open(save_path, 'wb') as fh:
                for chunk in photo_file.chunks():
                    fh.write(chunk)
            if os.path.isfile(save_path) and os.path.getsize(save_path) > 0:
                photo_name = candidate  # only use if file actually saved
        except Exception:
            pass  # fall back to avatar
    num = RegistrationRequest.objects.count() + 1
    req_id = f"REG-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
    # Write to JSON store first (always works)
    from .store import jread, jwrite
    reqs_json = jread('registration_requests')
    new_req = {
        'request_id': req_id, 'request_number': f'{num:04d}', 'name': name,
        'school_id': school_id, 'year_level': year_level, 'school_level': school_level,
        'course': course, 'password': password, 'status': 'pending', 'photo': photo_name,
        'phone_number': phone_number, 'email': email,
        'reviewed_by': '', 'created_at': str(datetime.now())[:16],
    }
    reqs_json.append(new_req)
    jwrite('registration_requests', reqs_json)

    # Try MySQL too (best effort)
    try:
        RegistrationRequest.objects.create(
            request_id=req_id, request_number=f'{num:04d}', name=name,
            school_id=school_id, year_level=year_level, school_level=school_level,
            course=course, password=password, status='pending', photo=photo_name,
            phone_number=phone_number, email=email,
        )
    except Exception as e:
        import logging; logging.getLogger('LBAS').warning(f'MySQL reg write failed: {e}')

    return JsonResponse({'success': True, 'request_number': f'{num:04d}'})


def api_admin_list(request):
    from .store import get_registration_requests
    return JsonResponse(get_registration_requests(), safe=False)


@csrf_exempt
def api_admin_decision(request, request_id):
    # Open for demo - admin verified by isStaff in JS
    data = parse_json_body(request)
    decision = str(data.get('decision', '')).strip().lower()
    try:
        req = RegistrationRequest.objects.get(request_id=request_id)
    except RegistrationRequest.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Not found'}, status=404)
    if req.status != 'pending':
        return JsonResponse({'success': False, 'message': 'Already resolved'}, status=400)
    if decision == 'approve':
        if not UserProfile.objects.filter(school_id=req.school_id).exists():
            UserProfile.objects.create(
                school_id=req.school_id, name=req.name, password=req.password,
                photo=req.photo, year_level=req.year_level, school_level=req.school_level,
                course=req.course, category='Student', is_staff=False, status='approved',
                phone_number=getattr(req, 'phone_number', ''),
                email=getattr(req, 'email', ''),
            )
        req.status = 'approved'
    elif decision == 'reject':
        req.status = 'rejected'
    else:
        return JsonResponse({'success': False, 'message': 'Invalid decision'}, status=400)
    req.reviewed_by = require_auth(request) or 'admin'
    req.reviewed_at = datetime.now()
    req.save()

    # Mirror to JSON store
    from .store import jread, jwrite
    reqs_json = jread('registration_requests')
    for r in reqs_json:
        if str(r.get('request_id')) == str(request_id):
            r['status'] = decision if decision in ('approve','reject') else req.status
            r['reviewed_by'] = str(req.reviewed_by)
            break
    jwrite('registration_requests', reqs_json)

    # If approved, also add to JSON users
    if decision == 'approve':
        users_json = jread('users')
        if not any(str(u.get('school_id','')).lower() == req.school_id for u in users_json):
            users_json.append({
                'school_id': req.school_id, 'name': req.name,
                'password': req.password, 'photo': req.photo,
                'category': 'Student', 'status': 'approved',
                'year_level': req.year_level, 'school_level': req.school_level,
                'course': req.course, 'phone_number': req.phone_number,
                'email': req.email, 'is_staff': False,
            })
            jwrite('users', users_json)

    return JsonResponse({'success': True, 'decision': decision})

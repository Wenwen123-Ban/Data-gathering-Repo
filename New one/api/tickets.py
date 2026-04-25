import random
import string
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from core.models import UserProfile
from .utils import parse_json_body, require_auth, require_admin, unauth

# In-memory PIN store — no file, no crash
_PINS = {}  # { school_id: { pin, status, created_at } }
TTL = 10  # minutes


def _cleanup():
    now = datetime.now()
    stale = [s for s, d in _PINS.items()
             if (now - d['created_at']).total_seconds() > TTL * 60]
    for s in stale:
        del _PINS[s]


@csrf_exempt
def api_request_reset(request):
    data = parse_json_body(request)
    s_id = str(data.get('school_id', '')).strip().lower()
    if not UserProfile.objects.filter(school_id=s_id).exists():
        return JsonResponse({'success': False, 'message': 'ID not found'}, status=404)
    _cleanup()
    _PINS[s_id] = {'pin': None, 'status': 'pending', 'created_at': datetime.now()}
    return JsonResponse({'success': True, 'message': 'Reset request submitted'})


@csrf_exempt
def api_check_ticket_status(request):
    data = parse_json_body(request)
    s_id = str(data.get('school_id', '')).strip().lower()
    _cleanup()
    entry = _PINS.get(s_id)
    if not entry:
        return JsonResponse({'status': 'not_found'})
    if entry['status'] == 'approved' and entry['pin']:
        return JsonResponse({'status': 'approved', 'code': entry['pin']})
    return JsonResponse({'status': 'pending'})


def api_admin_tickets(request):
    _cleanup()
    items = [
        {
            'school_id': sid,
            'status': d['status'],
            'expiry': (d['created_at'] + timedelta(minutes=TTL)).strftime('%Y-%m-%d %H:%M:%S'),
        }
        for sid, d in _PINS.items()
    ]
    return JsonResponse(items, safe=False)


@csrf_exempt
def api_approve_ticket(request):
    if not require_auth(request):
        return unauth()
    data = parse_json_body(request)
    s_id = str(data.get('school_id', '')).strip().lower()
    _cleanup()
    if s_id not in _PINS:
        return JsonResponse({'success': False, 'message': 'Request not found'}, status=404)
    pin = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    _PINS[s_id].update({'pin': pin, 'status': 'approved'})
    return JsonResponse({'success': True, 'code': pin})


@csrf_exempt
def api_finalize_reset(request):
    data = parse_json_body(request)
    s_id = str(data.get('school_id', '')).strip().lower()
    code = str(data.get('code', '')).strip().upper()
    new_pwd = str(data.get('new_password', '')).strip()
    _cleanup()
    entry = _PINS.get(s_id)
    if not entry or entry.get('pin') != code or entry.get('status') != 'approved':
        return JsonResponse({'success': False, 'message': 'Invalid or expired code'}, status=401)
    if not new_pwd:
        return JsonResponse({'success': False, 'message': 'Password required'}, status=400)
    UserProfile.objects.filter(school_id=s_id).update(password=new_pwd)
    del _PINS[s_id]
    return JsonResponse({'success': True})

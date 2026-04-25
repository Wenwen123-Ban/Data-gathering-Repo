from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from core.models import DateRestriction
from .utils import parse_json_body, require_auth, unauth

PH_HOLIDAYS = {
    '01-01': "New Year's Day",
    '04-09': 'Araw ng Kagitingan',
    '05-01': 'Labor Day',
    '06-12': 'Independence Day',
    '08-21': 'Ninoy Aquino Day',
    '11-01': "All Saints' Day",
    '11-30': 'Bonifacio Day',
    '12-25': 'Christmas Day',
    '12-30': 'Rizal Day',
}


def _status(date_str):
    try:
        day = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return {'date': date_str, 'restricted': False, 'reason': '', 'source': 'invalid'}

    auto = day.weekday() >= 5
    reason = 'Weekend' if auto else ''
    md = day.strftime('%m-%d')
    if md in PH_HOLIDAYS:
        auto, reason = True, f"Holiday: {PH_HOLIDAYS[md]}"

    try:
        manual = DateRestriction.objects.get(date=date_str)
        if manual.action == 'lift':
            return {'date': date_str, 'restricted': False, 'reason': manual.reason or 'Manually opened', 'source': 'manual_lift'}
        if manual.action == 'ban':
            return {'date': date_str, 'restricted': True, 'reason': manual.reason or 'Manually restricted', 'source': 'manual_ban'}
    except DateRestriction.DoesNotExist:
        pass

    return {'date': date_str, 'restricted': auto, 'reason': reason, 'source': 'auto' if auto else 'open'}


def api_list(request):
    year = int(request.GET.get('year', datetime.now().year))
    month = request.GET.get('month')
    start = datetime(year, int(month), 1) if month else datetime(year, 1, 1)
    end = (start.replace(day=28) + timedelta(days=4)).replace(day=1) if month else datetime(year + 1, 1, 1)
    items, cursor = [], start
    while cursor < end:
        items.append(_status(cursor.strftime('%Y-%m-%d')))
        cursor += timedelta(days=1)
    return JsonResponse({'success': True, 'items': items})


def api_check(request):
    date_str = request.GET.get('date', '')[:10]
    return JsonResponse({'success': True, **_status(date_str)})


@csrf_exempt
def api_set(request):
    if not require_auth(request):
        return unauth()
    data = parse_json_body(request)
    date_str = str(data.get('date', ''))[:10].strip()
    action = str(data.get('action', '')).strip().lower()
    reason = str(data.get('reason', '')).strip()
    if not date_str or action not in {'ban', 'lift', 'reset'}:
        return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)
    if action == 'reset':
        DateRestriction.objects.filter(date=date_str).delete()
    else:
        DateRestriction.objects.update_or_create(
            date=date_str, defaults={'action': action, 'reason': reason}
        )
    return JsonResponse({'success': True, 'item': _status(date_str)})

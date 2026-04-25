from collections import Counter
from datetime import datetime
from django.http import JsonResponse
from core.models import Transaction, UserProfile
from .utils import resolve_photo


def api_monthly_leaderboard(request):
    from .store import get_transactions
    now = datetime.now()
    all_txs = get_transactions()
    # Filter to this month's borrowed/returned
    def _in_month(t):
        try:
            from datetime import datetime as _dt
            d = str(t.get('date', ''))[:10]
            dt = _dt.strptime(d, '%Y-%m-%d')
            return dt.year == now.year and dt.month == now.month and str(t.get('status','')).lower() in ('borrowed','returned')
        except Exception:
            return False
    monthly = [t for t in all_txs if _in_month(t)]
    if not monthly:
        monthly = [t for t in all_txs if str(t.get('status','')).lower() in ('borrowed','returned')]
    counter = Counter(str(t.get('school_id','')) for t in monthly)
    top = []
    for i, (sid, total) in enumerate(counter.most_common(10), 1):
        try:
            user = UserProfile.objects.get(school_id=sid)
            name, photo = user.name, resolve_photo(user.photo)
        except UserProfile.DoesNotExist:
            name, photo = sid, 'default.png'
        top.append({'rank': i, 'school_id': sid, 'name': name,
                    'photo': photo, 'total_borrowed': total})
    return JsonResponse({'top_borrowers': top, 'top_books': []})


def api_leaderboard_profile(request, school_id):
    try:
        user = UserProfile.objects.get(school_id=str(school_id).strip())
        total = Transaction.objects.filter(
            school_id=school_id, status__in=['Borrowed', 'Returned']
        ).count()
        return JsonResponse({
            'success': True,
            'profile': {
                'school_id': user.school_id, 'name': user.name,
                'photo': user.photo, 'total_borrowed': total,
            },
        })
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False}, status=404)


def api_monthly_activity_logs(request):
    return JsonResponse({'month': datetime.now().strftime('%Y-%m'), 'totals': {}, 'days': []})

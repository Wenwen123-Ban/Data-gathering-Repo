from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from core.models import HomeCard
from .utils import parse_json_body, require_admin, unauth


@csrf_exempt
def api_home_cards(request):
    if request.method == 'GET':
        cards = HomeCard.objects.all().order_by('card_id')
        return JsonResponse(
            [{'id': c.card_id, 'title': c.title, 'body': c.body} for c in cards],
            safe=False
        )
    if request.method == 'POST':
        if not require_auth(request):
            return unauth()
        data = parse_json_body(request)
        rows = data if isinstance(data, list) else data.get('cards', [])
        for row in rows:
            cid = int(row.get('id', 0))
            if 1 <= cid <= 4:
                HomeCard.objects.update_or_create(
                    card_id=cid,
                    defaults={'title': row.get('title', ''), 'body': row.get('body', '')}
                )
        cards = HomeCard.objects.all().order_by('card_id')
        return JsonResponse({
            'success': True,
            'cards': [{'id': c.card_id, 'title': c.title, 'body': c.body} for c in cards]
        })
    return JsonResponse({'error': 'Method not allowed'}, status=405)

import uuid
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from core.models import NewsPost
from .utils import require_admin, unauth


def _p(p):
    return {
        'id': p.post_id, 'title': p.title, 'summary': p.summary,
        'body': p.body, 'image_filename': p.image_filename,
        'date': str(p.date)[:10], 'author': p.author,
    }


@csrf_exempt
def api_news_list(request):
    if request.method == 'GET':
        return JsonResponse([_p(p) for p in NewsPost.objects.all().order_by('-date')], safe=False)
    if request.method == 'POST':
        if not require_auth(request):
            return unauth()
        title = request.POST.get('title', '').strip()
        summary = request.POST.get('summary', '').strip()
        body = request.POST.get('body', '').strip()
        if not title or not summary or not body:
            return JsonResponse({'success': False, 'message': 'Missing fields'}, status=400)
        image_filename = None
        image_file = request.FILES.get('image')
        if image_file:
            import os
            from django.conf import settings
            ext = os.path.splitext(image_file.name)[1].lower() or '.jpg'
            image_filename = f'news_{uuid.uuid4().hex[:8]}{ext}'
            save_path = os.path.join(settings.MEDIA_ROOT, image_filename)
            os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
            with open(save_path, 'wb') as f:
                for chunk in image_file.chunks():
                    f.write(chunk)
        post = NewsPost.objects.create(
            post_id=uuid.uuid4().hex, title=title, summary=summary,
            body=body, image_filename=image_filename
        )
        return JsonResponse({'success': True, 'post': _p(post)})
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def api_news_delete(request, post_id):
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    if not require_auth(request):
        return unauth()
    deleted, _ = NewsPost.objects.filter(post_id=post_id).delete()
    return JsonResponse({'success': bool(deleted)})

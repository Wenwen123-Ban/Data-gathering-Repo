from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from core.models import Book, Category
from .utils import parse_json_body, require_auth, require_admin, unauth

_DEFAULTS = ['General', 'Mathematics', 'Science', 'Literature']


def _book_dict(b):
    return {'book_no': b.book_no, 'title': b.title,
            'status': b.status, 'category': b.category}


def _all_categories():
    """Return all categories from lbas_categories table, always including defaults."""
    db_cats = list(Category.objects.values_list('name', flat=True).order_by('name'))
    for d in _DEFAULTS:
        if d not in db_cats:
            db_cats.append(d)
            # Also ensure it exists in DB
            Category.objects.get_or_create(name=d)
    return sorted(set(db_cats))


def api_get_books(request):
    from .store import get_books
    return JsonResponse(get_books(), safe=False)


def api_admin_get_books(request):
    from .store import get_books
    return JsonResponse(get_books(), safe=False)


@csrf_exempt
def api_bulk_register(request):
    if not require_auth(request):
        return unauth()
    data = parse_json_body(request)
    raw_text = str(data.get('text', '')).strip()
    category = str(data.get('category', 'General')).strip() or 'General'
    if data.get('clear_first'):
        Book.objects.all().delete()
    added = 0
    skipped = 0
    for line in raw_text.split('\n'):
        line = line.strip()
        if not line:
            continue
        if '|' in line:
            parts = [p.strip() for p in line.split('|', 1)]
        elif ',' in line:
            parts = [p.strip() for p in line.split(',', 1)]
        else:
            parts = line.split(None, 1)
        if len(parts) >= 2:
            b_no = parts[0].strip().upper()
            title = parts[1].strip()
            _, created = Book.objects.get_or_create(
                book_no=b_no,
                defaults={'title': title, 'status': 'Available', 'category': category}
            )
            if created:
                added += 1
            else:
                skipped += 1
    return JsonResponse({
        'success': True,
        'added': added,
        'items_added': added,
        'skipped': skipped,
        'total_in_db': Book.objects.count()
    })


@csrf_exempt
def api_update_book(request):
    if not require_auth(request):
        return unauth()
    data = parse_json_body(request)
    b_no = str(data.get('book_no', '')).strip()
    try:
        book = Book.objects.get(book_no=b_no)
        if 'title' in data:
            book.title = data['title']
        if 'category' in data:
            book.category = data['category']
        if 'status' in data:
            book.status = data['status']
        book.save()
        return JsonResponse({'success': True})
    except Book.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Not found'}, status=404)


@csrf_exempt
def api_delete_book(request):
    if not require_auth(request):
        return unauth()
    data = parse_json_body(request)
    b_no = str(data.get('book_no', '')).strip()
    deleted, _ = Book.objects.filter(book_no=b_no).delete()
    return JsonResponse({'success': bool(deleted)})


@csrf_exempt
def api_categories(request):
    if request.method == 'POST':
        if not require_auth(request):
            return unauth()
        data = parse_json_body(request)
        cat = str(data.get('category', '')).strip()
        if not cat:
            return JsonResponse({'success': False, 'message': 'Category name required'}, status=400)
        Category.objects.get_or_create(name=cat)
        return JsonResponse({'success': True, 'categories': _all_categories()})
    # GET
    from .store import get_categories
    return JsonResponse(get_categories(), safe=False)


@csrf_exempt
def api_delete_category(request):
    if not require_auth(request):
        return unauth()
    data = parse_json_body(request)
    cat = str(data.get('category', '')).strip()
    if not cat:
        return JsonResponse({'success': False, 'message': 'No category'}, status=400)
    Category.objects.filter(name=cat).delete()
    Book.objects.filter(category=cat).delete()
    return JsonResponse({'success': True})

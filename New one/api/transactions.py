from __future__ import annotations
import uuid
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from core.models import Transaction, Book, UserProfile
from .utils import parse_json_body, require_auth, require_admin, unauth


def _tx(t):
    return {
        'id': t.id,
        'book_no': t.book_no, 'title': t.title,
        'school_id': t.school_id, 'borrower_name': t.borrower_name,
        'status': t.status,
        'date': str(t.date)[:16] if t.date else '',
        'expiry': str(t.expiry) if t.expiry else '',
        'return_date': str(t.return_date)[:16] if t.return_date else '',
        'pickup_schedule': t.pickup_schedule,
        'pickup_location': t.pickup_location,
        'reservation_note': t.reservation_note,
        'phone_number': t.phone_number,
        'contact_type': t.contact_type,
        'request_id': t.request_id,
        'approved_by': t.approved_by,
    }


def api_get_transactions(request):
    if not require_auth(request):
        return unauth()
    return JsonResponse([_tx(t) for t in Transaction.objects.all().order_by('-date')], safe=False)


def api_admin_get_transactions(request):
    from .store import get_transactions
    txs = get_transactions()
    txs.sort(key=lambda t: str(t.get('date', '')), reverse=True)
    return JsonResponse(txs, safe=False)


def api_admin_approval_records(request):
    qs = Transaction.objects.filter(status__in=['Borrowed', 'Returned']).order_by('-date')
    return JsonResponse([_tx(t) for t in qs], safe=False)


@csrf_exempt
def api_reserve(request):
    if not require_auth(request):
        return unauth()
    data = parse_json_body(request)
    b_no = str(data.get('book_no', '')).strip()
    s_id = str(data.get('school_id', '')).strip().lower()
    pickup_schedule = str(data.get('pickup_schedule', '')).strip()
    contact_type = str(data.get('contact_type', '')).strip()
    phone_number = str(data.get('phone_number', '')).strip()
    reservation_note = str(data.get('reservation_note', '')).strip()
    pickup_location = str(data.get('pickup_location', '')).strip()
    request_id = str(data.get('request_id', '') or uuid.uuid4())

    try:
        book = Book.objects.get(book_no=b_no)
    except Book.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Book not found'}, status=404)

    if Transaction.objects.filter(book_no=b_no, school_id=s_id,
                                   status__in=['Reserved', 'Borrowed']).exists():
        return JsonResponse({'success': False, 'message': 'Already have an active reservation for this book'}, status=409)

    if Transaction.objects.filter(school_id=s_id, status='Reserved').count() >= 5:
        return JsonResponse({'success': False, 'message': 'Reservation limit reached (5 max)'}, status=400)

    try:
        user = UserProfile.objects.get(school_id=s_id)
        borrower_name = user.name
    except UserProfile.DoesNotExist:
        borrower_name = s_id

    if book.status == 'Available':
        book.status = 'Reserved'
        book.save()

    # Write to JSON store first
    from .store import jread, jwrite
    import datetime as _dt
    txs_json = jread('transactions')
    txs_json.append({
        'book_no': b_no, 'title': book.title, 'school_id': s_id,
        'borrower_name': borrower_name, 'status': 'Reserved',
        'pickup_schedule': pickup_schedule, 'contact_type': contact_type,
        'phone_number': phone_number, 'request_id': request_id,
        'pickup_location': pickup_location, 'reservation_note': reservation_note,
        'date': _dt.datetime.now().strftime('%Y-%m-%d %H:%M'),
        'expiry': '', 'return_date': '', 'approved_by': '',
    })
    jwrite('transactions', txs_json)
    # Also update book status in JSON
    books_json = jread('books')
    for b in books_json:
        if str(b.get('book_no')) == str(b_no):
            b['status'] = 'Reserved'
            break
    jwrite('books', books_json)

    # Try MySQL (best effort)
    try:
        Transaction.objects.create(
            book_no=b_no, title=book.title, school_id=s_id,
            borrower_name=borrower_name, status='Reserved',
            pickup_schedule=pickup_schedule, contact_type=contact_type,
            phone_number=phone_number, request_id=request_id,
            pickup_location=pickup_location, reservation_note=reservation_note,
        )
    except Exception as e:
        import logging; logging.getLogger('LBAS').warning(f'MySQL tx write failed: {e}')

    return JsonResponse({'success': True, 'request_id': request_id})


@csrf_exempt
def api_process_transaction(request):
    # Auth checked client-side via isStaff; token sent via apiFetch
    data = parse_json_body(request)
    b_no = str(data.get('book_no', '')).strip()
    action = str(data.get('action', '')).strip().lower()
    approved_by = str(data.get('approved_by', '')).strip()

    try:
        book = Book.objects.get(book_no=b_no)
    except Book.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Book not found'}, status=404)

    if action == 'return':
        book.status = 'Available'
        book.save()
        Transaction.objects.filter(book_no=b_no, status='Borrowed').update(
            status='Returned', return_date=datetime.now()
        )
        # Also update JSON store
        from .store import jread, jwrite
        txs_j = jread('transactions')
        for t in txs_j:
            if str(t.get('book_no',''))==b_no and str(t.get('status','')).lower()=='borrowed':
                t['status'] = 'Returned'
                t['return_date'] = datetime.now().strftime('%Y-%m-%d %H:%M')
                break
        books_j = jread('books')
        for bk in books_j:
            if str(bk.get('book_no',''))==b_no:
                bk['status'] = 'Available'; break
        jwrite('transactions', txs_j); jwrite('books', books_j)
        return JsonResponse({'success': True})

    if action == 'borrow':
        tx = Transaction.objects.filter(book_no=b_no, status='Reserved').order_by('date').first()
        if not tx:
            return JsonResponse({'success': False, 'message': 'No reservation found'}, status=400)
        tx.status = 'Borrowed'
        if approved_by:
            tx.approved_by = approved_by
        # Save return due date
        return_due_date = str(data.get('return_due_date', '')).strip()
        if return_due_date:
            try:
                from datetime import date
                tx.expiry = datetime.strptime(return_due_date, '%Y-%m-%d').date()
            except ValueError:
                pass
        tx.save()
        book.status = 'Borrowed'
        book.save()
        # Also update JSON store
        from .store import jread, jwrite
        txs_j = jread('transactions')
        for t in txs_j:
            if str(t.get('book_no',''))==b_no and str(t.get('status','')).lower()=='reserved':
                t['status'] = 'Borrowed'
                t['approved_by'] = approved_by
                t['expiry'] = str(data.get('return_due_date',''))
                break
        books_j = jread('books')
        for bk in books_j:
            if str(bk.get('book_no',''))==b_no:
                bk['status'] = 'Borrowed'; break
        jwrite('transactions', txs_j); jwrite('books', books_j)
        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'message': 'Invalid action'}, status=400)


@csrf_exempt
def api_cancel_reservation(request):
    # Auth checked client-side via isStaff; token sent via apiFetch
    data = parse_json_body(request)
    b_no = str(data.get('book_no', '')).strip()
    s_id = str(data.get('school_id', '')).strip().lower()
    request_id = str(data.get('request_id', '')).strip()

    # ── JSON store cancel (always works) ──
    from .store import jread, jwrite
    txs_json = jread('transactions')
    cancelled_json = False
    for t in txs_json:
        if str(t.get('book_no','')) == b_no and str(t.get('status','')).lower() in ('reserved','borrowed'):
            if (not request_id and not s_id) or                (request_id and str(t.get('request_id','')) == request_id) or                (s_id and str(t.get('school_id','')).lower() == s_id):
                t['status'] = 'Cancelled'
                cancelled_json = True
                break
    if cancelled_json:
        # Update book status in JSON too
        books_json = jread('books')
        still_reserved = any(str(t.get('book_no',''))==b_no and str(t.get('status','')).lower()=='reserved'
                             for t in txs_json)
        for bk in books_json:
            if str(bk.get('book_no','')) == b_no:
                bk['status'] = 'Reserved' if still_reserved else 'Available'
                break
        jwrite('transactions', txs_json)
        jwrite('books', books_json)

    # ── MySQL cancel (best effort) ──
    try:
        qs = Transaction.objects.filter(book_no=b_no, status__in=['Reserved', 'Borrowed'])
        if request_id:
            qs = qs.filter(request_id=request_id)
        elif s_id:
            qs = qs.filter(school_id=s_id)
        tx = qs.first()
        if tx:
            tx.status = 'Cancelled'
            tx.save()
            if not Transaction.objects.filter(book_no=b_no, status='Reserved').exists():
                Book.objects.filter(book_no=b_no).update(status='Available')
    except Exception as e:
        import logging; logging.getLogger('LBAS').warning(f'MySQL cancel failed: {e}')

    if cancelled_json:
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'message': 'No active reservation found'}, status=404)

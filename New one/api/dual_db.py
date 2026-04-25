"""
Dual-DB Layer for LBAS Defense Demo
Tries MySQL first, falls back to JSON if MySQL is unavailable or empty.
Writes go to BOTH so they stay in sync.
"""
import json
import os
import logging
from pathlib import Path

logger = logging.getLogger("LBAS.dual_db")

# Path to JSON files
_JSON_DIR = Path(__file__).resolve().parent.parent / "JSON's"

# JSON key → filename mapping
_JSON_FILES = {
    'books':                  'books.json',
    'users':                  'users.json',
    'admins':                 'admins.json',  # in FormerDB subfolder
    'transactions':           'transactions.json',
    'categories':             'categories.json',
    'registration_requests':  'registration_requests.json',
    'home_cards':             'home_cards.json',
    'news_posts':             'news_posts.json',
    'courses':                'courses.json',
    'admin_approval_record':  'Admin_approval_record.json',
    'date_restricted':        'Date_Restricted.json',
    'reservation_transactions': 'reservation_transaction.json',
}


def _json_path(key):
    if key == 'admins':
        return _JSON_DIR / 'FormerDB' / 'admins.json'
    fname = _JSON_FILES.get(key)
    if not fname:
        return None
    return _JSON_DIR / fname


def read_json(key):
    """Read from JSON fallback file."""
    path = _json_path(key)
    if not path or not path.exists():
        return [] if key != 'date_restricted' else {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Normalize admins to have is_staff=True
        if key == 'admins':
            for a in (data if isinstance(data, list) else []):
                a['is_staff'] = True
                a.setdefault('status', 'approved')
                a.setdefault('photo', 'default.png')
        return data
    except Exception as e:
        logger.warning(f"JSON read failed ({key}): {e}")
        return [] if key != 'date_restricted' else {}


def write_json(key, data):
    """Write to JSON fallback file to keep it in sync."""
    path = _json_path(key)
    if not path:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    except Exception as e:
        logger.warning(f"JSON write failed ({key}): {e}")


def get_books_with_fallback():
    """Get books — MySQL first, JSON if empty/failed."""
    try:
        from core.models import Book
        books = list(Book.objects.values('book_no', 'title', 'status', 'category'))
        if books:
            return books
        logger.info("Books: MySQL empty, using JSON fallback")
    except Exception as e:
        logger.warning(f"Books: MySQL failed ({e}), using JSON fallback")
    return read_json('books')


def get_users_with_fallback():
    """Get users — MySQL first, JSON if empty/failed."""
    try:
        from core.models import UserProfile
        from api.utils import resolve_photo
        users = [
            {'school_id': u.school_id, 'name': u.name, 'category': u.category,
             'photo': resolve_photo(u.photo), 'status': u.status, 'is_staff': u.is_staff,
             'phone_number': u.phone_number, 'email': getattr(u, 'email', ''),
             'year_level': u.year_level, 'school_level': u.school_level, 'course': u.course}
            for u in UserProfile.objects.filter(is_staff=False)
        ]
        if users:
            return users
        logger.info("Users: MySQL empty, using JSON fallback")
    except Exception as e:
        logger.warning(f"Users: MySQL failed ({e}), using JSON fallback")
    # JSON users don't have is_staff field - add it
    users = read_json('users')
    for u in users:
        u.setdefault('is_staff', False)
        u.setdefault('status', 'approved')
    return users


def get_admins_with_fallback():
    """Get admins — MySQL first, JSON if empty/failed."""
    try:
        from core.models import UserProfile
        from api.utils import resolve_photo
        admins = [
            {'school_id': u.school_id, 'name': u.name, 'category': u.category,
             'photo': resolve_photo(u.photo), 'status': u.status, 'is_staff': True,
             'phone_number': u.phone_number, 'email': getattr(u, 'email', '')}
            for u in UserProfile.objects.filter(is_staff=True)
        ]
        if admins:
            return admins
        logger.info("Admins: MySQL empty, using JSON fallback")
    except Exception as e:
        logger.warning(f"Admins: MySQL failed ({e}), using JSON fallback")
    return read_json('admins')


def get_transactions_with_fallback():
    """Get transactions — MySQL first, JSON if failed."""
    try:
        from core.models import Transaction
        txs = list(Transaction.objects.values(
            'id', 'book_no', 'title', 'school_id', 'borrower_name',
            'status', 'date', 'expiry', 'return_date', 'pickup_schedule',
            'pickup_location', 'reservation_note', 'phone_number',
            'contact_type', 'request_id', 'approved_by'
        ))
        return txs  # transactions can legitimately be empty
    except Exception as e:
        logger.warning(f"Transactions: MySQL failed ({e}), using JSON fallback")
    return read_json('transactions')


def get_registration_requests_with_fallback():
    """Get registration requests — MySQL first, JSON if failed."""
    try:
        from core.models import RegistrationRequest
        from api.utils import resolve_photo
        reqs = [
            {'request_id': r.request_id, 'request_number': r.request_number,
             'name': r.name, 'school_id': r.school_id, 'year_level': r.year_level,
             'school_level': r.school_level, 'course': r.course,
             'photo': resolve_photo(r.photo), 'status': r.status,
             'reviewed_by': r.reviewed_by, 'phone_number': r.phone_number,
             'email': r.email, 'created_at': str(r.created_at)[:16]}
            for r in RegistrationRequest.objects.all().order_by('-created_at')
        ]
        return reqs
    except Exception as e:
        logger.warning(f"RegRequests: MySQL failed ({e}), using JSON fallback")
    return read_json('registration_requests')


def get_categories_with_fallback():
    """Get categories — MySQL first, JSON if empty/failed."""
    try:
        from core.models import Category
        cats = list(Category.objects.values_list('name', flat=True))
        if cats:
            return sorted(cats)
        logger.info("Categories: MySQL empty, using JSON fallback")
    except Exception as e:
        logger.warning(f"Categories: MySQL failed ({e}), using JSON fallback")
    return read_json('categories') or ['General', 'Mathematics', 'Science', 'Literature']

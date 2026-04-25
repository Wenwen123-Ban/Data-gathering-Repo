"""
LBAS Data Store — JSON primary, MySQL sync secondary.
All reads from JSON. All writes to JSON first, MySQL when available.
"""
import json
import os
import threading
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("LBAS.store")

_BASE = Path(__file__).resolve().parent.parent
_JSON = _BASE / "JSON's"
_LOCK = threading.Lock()
_PENDING_SYNC = []   # queue of (operation, key, data) waiting for MySQL
_MYSQL_OK = False    # last known MySQL health

_FILES = {
    'books':                   _JSON / 'books.json',
    'users':                   _JSON / 'users.json',
    'admins':                  _JSON / 'FormerDB' / 'admins.json',
    'transactions':            _JSON / 'transactions.json',
    'categories':              _JSON / 'categories.json',
    'registration_requests':   _JSON / 'registration_requests.json',
    'home_cards':              _JSON / 'home_cards.json',
    'news_posts':              _JSON / 'news_posts.json',
    'courses':                 _JSON / 'courses.json',
    'admin_approval_record':   _JSON / 'Admin_approval_record.json',
    'date_restricted':         _JSON / 'Date_Restricted.json',
}


# ── JSON read/write ───────────────────────────────────────────────

def jread(key):
    path = _FILES.get(key)
    if not path or not path.exists():
        return {} if key in ('date_restricted', 'courses') else []
    try:
        with _LOCK:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"jread({key}): {e}")
        return {} if key in ('date_restricted', 'courses') else []


def jwrite(key, data):
    path = _FILES.get(key)
    if not path:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with _LOCK:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    except Exception as e:
        logger.warning(f"jwrite({key}): {e}")


# ── MySQL health check ────────────────────────────────────────────

def check_mysql():
    global _MYSQL_OK
    try:
        from django.db import connection
        connection.ensure_connection()
        _MYSQL_OK = True
        return True
    except Exception:
        _MYSQL_OK = False
        return False


def mysql_ok():
    return _MYSQL_OK


# ── Sync: push JSON → MySQL ───────────────────────────────────────

def sync_to_mysql():
    """Push all JSON data into MySQL. Called when MySQL becomes available."""
    if not check_mysql():
        return False
    try:
        _sync_users()
        _sync_books()
        _sync_transactions()
        _sync_registration_requests()
        _sync_categories()
        logger.info("sync_to_mysql: complete")
        return True
    except Exception as e:
        logger.warning(f"sync_to_mysql failed: {e}")
        return False


def _sync_users():
    from core.models import UserProfile
    users = jread('users')
    admins = jread('admins')
    for u in users:
        sid = str(u.get('school_id', '')).strip().lower()
        if not sid:
            continue
        UserProfile.objects.get_or_create(
            school_id=sid,
            defaults={
                'name': u.get('name', ''),
                'password': u.get('password', ''),
                'category': u.get('category', 'Student'),
                'photo': u.get('photo', 'default.png'),
                'status': u.get('status', 'approved'),
                'is_staff': False,
                'phone_number': u.get('phone_number', ''),
                'email': u.get('email', ''),
                'year_level': str(u.get('year_level', '')),
                'school_level': u.get('school_level', 'college'),
                'course': u.get('course', ''),
            }
        )
    for a in admins:
        sid = str(a.get('school_id', '')).strip().lower()
        if not sid:
            continue
        UserProfile.objects.get_or_create(
            school_id=sid,
            defaults={
                'name': a.get('name', ''),
                'password': a.get('password', ''),
                'category': 'Staff',
                'photo': a.get('photo', 'default.png'),
                'status': 'approved',
                'is_staff': True,
            }
        )


def _sync_books():
    from core.models import Book
    books = jread('books')
    for b in books:
        bno = str(b.get('book_no', '')).strip()
        if not bno:
            continue
        Book.objects.get_or_create(
            book_no=bno,
            defaults={
                'title': b.get('title', ''),
                'status': b.get('status', 'Available'),
                'category': b.get('category', 'General'),
            }
        )


def _sync_transactions():
    from core.models import Transaction
    import uuid as _uuid
    txs = jread('transactions')
    for t in txs:
        bno = str(t.get('book_no', '')).strip()
        sid = str(t.get('school_id', '')).strip().lower()
        if not bno or not sid:
            continue
        req_id = str(t.get('request_id', '') or _uuid.uuid4())
        Transaction.objects.get_or_create(
            request_id=req_id,
            defaults={
                'book_no': bno,
                'title': t.get('title', ''),
                'school_id': sid,
                'borrower_name': t.get('borrower_name', ''),
                'status': t.get('status', 'Reserved'),
                'phone_number': t.get('phone_number', ''),
                'contact_type': t.get('contact_type', ''),
                'pickup_schedule': t.get('pickup_schedule', ''),
                'pickup_location': t.get('pickup_location', ''),
                'reservation_note': t.get('reservation_note', ''),
                'approved_by': t.get('approved_by', ''),
            }
        )


def _sync_registration_requests():
    from core.models import RegistrationRequest
    reqs = jread('registration_requests')
    for r in reqs:
        rid = str(r.get('request_id', '')).strip()
        if not rid:
            continue
        RegistrationRequest.objects.get_or_create(
            request_id=rid,
            defaults={
                'request_number': r.get('request_number', '0001'),
                'name': r.get('name', ''),
                'school_id': str(r.get('school_id', '')).lower(),
                'year_level': str(r.get('year_level', '')),
                'school_level': r.get('school_level', 'college'),
                'course': r.get('course', ''),
                'phone_number': r.get('phone_number', ''),
                'email': r.get('email', ''),
                'password': r.get('password', ''),
                'photo': r.get('photo', 'default.png'),
                'status': r.get('status', 'pending'),
            }
        )


def _sync_categories():
    from core.models import Category
    cats = jread('categories')
    for c in (cats if isinstance(cats, list) else []):
        Category.objects.get_or_create(name=str(c).strip())


# ── Convenience read functions used by API endpoints ─────────────

def get_books():
    books = jread('books')
    # Normalize status capitalization
    for b in books:
        s = str(b.get('status', 'Available'))
        b['status'] = s[0].upper() + s[1:].lower() if s else 'Available'
    return books


def get_users():
    from api.utils import resolve_photo
    users = jread('users')
    for u in users:
        u.setdefault('is_staff', False)
        u.setdefault('status', 'approved')
        u.setdefault('phone_number', '')
        u.setdefault('email', '')
        u.setdefault('year_level', '')
        u.setdefault('school_level', 'college')
        u.setdefault('course', '')
        u['photo'] = resolve_photo(u.get('photo', 'default.png'))
    return users


def get_admins():
    from api.utils import resolve_photo
    admins = jread('admins')
    for a in admins:
        a['is_staff'] = True
        a.setdefault('status', 'approved')
        a.setdefault('phone_number', '')
        a.setdefault('email', '')
        a.setdefault('year_level', '')
        a.setdefault('school_level', '')
        a.setdefault('course', '')
        a['photo'] = resolve_photo(a.get('photo', 'default.png'))
    return admins


def get_transactions():
    txs = jread('transactions')
    for t in txs:
        t.setdefault('request_id', '')
        t.setdefault('borrower_name', t.get('school_id', ''))
        t.setdefault('title', '')
        t.setdefault('expiry', '')
        t.setdefault('return_date', t.get('return_by', ''))
        t.setdefault('pickup_schedule', '')
        t.setdefault('pickup_location', '')
        t.setdefault('reservation_note', '')
        t.setdefault('phone_number', '')
        t.setdefault('contact_type', '')
        t.setdefault('approved_by', '')
    return txs


def get_registration_requests():
    reqs = jread('registration_requests')
    for r in reqs:
        r.setdefault('request_number', '0001')
        r.setdefault('year_level', '')
        r.setdefault('school_level', 'college')
        r.setdefault('course', '')
        r.setdefault('phone_number', '')
        r.setdefault('email', '')
        r.setdefault('photo', 'default.png')
        r.setdefault('reviewed_by', '')
        r.setdefault('created_at', r.get('date_created', ''))
    return reqs


def get_categories():
    cats = jread('categories')
    if not isinstance(cats, list) or not cats:
        return ['General', 'Mathematics', 'Science', 'Literature']
    return cats


def find_user(school_id):
    """Find user in JSON store (admins first, then users)."""
    sid = str(school_id).strip().lower()
    for a in get_admins():
        if str(a.get('school_id', '')).strip().lower() == sid:
            return a
    for u in get_users():
        if str(u.get('school_id', '')).strip().lower() == sid:
            return u
    return None

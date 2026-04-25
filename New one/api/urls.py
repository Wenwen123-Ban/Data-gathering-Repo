from django.urls import path
from . import (
    auth, books, users, registration,
    tickets, leaderboard, news,
    home_cards, date_restrictions, courses, transactions,
)
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def api_ping(request):
    """Health check — also triggers MySQL sync when stable"""
    from api.store import check_mysql, mysql_ok, sync_to_mysql
    import threading
    was_ok = mysql_ok()
    now_ok = check_mysql()
    # If MySQL just became available (recovered from crash), sync in background
    if now_ok and not was_ok:
        threading.Thread(target=sync_to_mysql, daemon=True).start()
    return JsonResponse({
        'ok': True,
        'status': 'running',
        'mysql': now_ok,
        'mode': 'mysql+json' if now_ok else 'json-only'
    })

urlpatterns = [
    # Auth
    path('login', auth.api_login),
    path('logout', auth.api_logout),

    # Books (public + admin)
    path('books', books.api_get_books),
    path('admin/books', books.api_admin_get_books),
    path('bulk_register', books.api_bulk_register),
    path('update_book', books.api_update_book),
    path('delete_book', books.api_delete_book),
    path('categories', books.api_categories),
    path('delete_category', books.api_delete_category),

    # Users
    path('users', users.api_get_users),
    path('admins', users.api_get_admins),
    path('admin/users', users.api_admin_get_users),
    path('admin/admins', users.api_admin_get_admins),
    path('register_student', users.api_register_student),
    path('register_librarian', users.api_register_librarian),
    path('update_member', users.api_update_member),
    path('update_profile_photo', users.api_update_profile_photo),
    path('delete_member', users.api_delete_member),
    path('user/<str:school_id>', users.api_get_user),

    # Transactions
    path('transactions', transactions.api_get_transactions),
    path('admin/transactions', transactions.api_admin_get_transactions),
    path('admin/approval-records', transactions.api_admin_approval_records),
    path('reserve', transactions.api_reserve),
    path('process_transaction', transactions.api_process_transaction),
    path('cancel_reservation', transactions.api_cancel_reservation),

    # Registration requests
    path('register_request', registration.api_register_request),
    path('admin/registration-requests', registration.api_admin_list),
    path('admin/registration-requests/<str:request_id>/decision', registration.api_admin_decision),

    # Password reset tickets (in-memory, no file)
    path('request_reset', tickets.api_request_reset),
    path('check_ticket_status', tickets.api_check_ticket_status),
    path('admin/tickets', tickets.api_admin_tickets),
    path('admin/approve_ticket', tickets.api_approve_ticket),
    path('finalize_reset', tickets.api_finalize_reset),

    # Leaderboard
    path('monthly_leaderboard', leaderboard.api_monthly_leaderboard),
    path('leaderboard_profile/<str:school_id>', leaderboard.api_leaderboard_profile),
    path('monthly_activity_logs', leaderboard.api_monthly_activity_logs),

    # News
    path('news_posts', news.api_news_list),
    path('news_posts/<str:post_id>', news.api_news_delete),

    # Home cards
    path('home_cards', home_cards.api_home_cards),

    # Date restrictions
    path('date_restrictions', date_restrictions.api_list),
    path('date_restrictions/check', date_restrictions.api_check),
    path('date_restrictions/set', date_restrictions.api_set),

    # Health check (no DB)
    path('ping', api_ping),

    # Courses
    path('courses', courses.api_courses),
    path('admin/courses', courses.api_admin_courses),
]

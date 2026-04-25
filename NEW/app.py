import base64
import json
import secrets
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
MEDIA_DIR = BASE_DIR / 'media' / 'book_borrow_transaction_photos'
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

DB_FILES = {
    'users': BASE_DIR / 'users.json',
    'registration_requests': BASE_DIR / 'registration_requests.json',
    'borrow_transactions': BASE_DIR / 'borrow_transactions.json',
    'date_restrictions': BASE_DIR / 'date_restrictions.json',
}

app = Flask(__name__, template_folder='templates', static_folder='.')
QR_TOKENS = {}


def read_json(name):
    path = DB_FILES[name]
    if not path.exists():
        return []
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def write_json(name, data):
    with DB_FILES[name].open('w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def now_str():
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')


def notify_user(student_id, message):
    users = read_json('users')
    for u in users:
        if u.get('student_id') == student_id:
            u.setdefault('notifications', []).insert(0, {
                'message': message,
                'timestamp': now_str(),
                'unread': True,
            })
            break
    write_json('users', users)


def date_is_restricted(date_obj):
    manual = {row['date']: row for row in read_json('date_restrictions')}
    date_key = date_obj.strftime('%Y-%m-%d')
    if date_key in manual:
        item = manual[date_key]
        if item.get('action') == 'lift':
            return False, item.get('reason') or 'Manually opened'
        if item.get('action') == 'ban':
            return True, item.get('reason') or 'Manually restricted'

    if date_obj.weekday() >= 5:
        return True, 'Weekend restriction (Phase 9)'
    holidays = {'01-01': "New Year's Day", '12-25': 'Christmas Day'}
    md = date_obj.strftime('%m-%d')
    if md in holidays:
        return True, f'Holiday restriction: {holidays[md]}'
    return False, ''


@app.route('/')
def home():
    return render_template('student_portal.html')


@app.route('/admin')
def admin():
    return render_template('admin_dashboard.html')


@app.route('/mobile/borrow-proof/<token>')
def mobile_borrow_proof(token):
    tx_id = QR_TOKENS.get(token)
    if not tx_id:
        return jsonify({'success': False, 'message': 'Invalid or expired link'}), 404
    return render_template('mobile_qr_capture.html', token=token, transaction_id=tx_id)


@app.route('/media/book_borrow_transaction_photos/<path:filename>')
def media_file(filename):
    return send_from_directory(str(MEDIA_DIR), filename)


@app.route('/api/registration_requests', methods=['GET', 'POST'])
def registration_requests():
    if request.method == 'GET':
        return jsonify(read_json('registration_requests'))

    payload = request.get_json(force=True)
    rows = read_json('registration_requests')
    row = {
        'request_id': f"RR-{len(rows)+1:04d}",
        'name': payload.get('name', ''),
        'student_id': payload.get('student_id', '').lower(),
        'school_level': payload.get('school_level', ''),
        'year': payload.get('year', ''),
        'course': payload.get('course', ''),
        'contact': payload.get('contact', ''),
        'avatar_path': payload.get('avatar_path', '/media/avatars/default.png'),
        'status': 'pending',
        'created_at': now_str(),
    }
    rows.append(row)
    write_json('registration_requests', rows)
    return jsonify({'success': True, 'request': row})


@app.post('/api/admin/registration_requests/<request_id>/approve')
def approve_registration(request_id):
    requests_db = read_json('registration_requests')
    users = read_json('users')
    for req in requests_db:
        if req['request_id'] == request_id:
            req['status'] = 'approved'
            users.append({
                'student_id': req['student_id'],
                'name': req['name'],
                'avatar_path': req.get('avatar_path', '/media/avatars/default.png'),
                'school_level': req.get('school_level', ''),
                'year': req.get('year', ''),
                'course': req.get('course', ''),
                'contact': req.get('contact', ''),
                'notifications': [{
                    'message': 'Your registration has been approved.',
                    'timestamp': now_str(),
                    'unread': True,
                }],
            })
            write_json('registration_requests', requests_db)
            write_json('users', users)
            return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'request not found'}), 404


@app.get('/api/users/<student_id>/notifications')
def user_notifications(student_id):
    for row in read_json('users'):
        if row.get('student_id') == student_id.lower():
            return jsonify(row.get('notifications', []))
    return jsonify([])


@app.get('/api/transactions')
def list_transactions():
    return jsonify(read_json('borrow_transactions'))


@app.post('/api/reservations/cancel')
def cancel_reservation():
    payload = request.get_json(force=True)
    tx_id = payload.get('transaction_id')
    txs = read_json('borrow_transactions')
    for tx in txs:
        if tx.get('transaction_id') == tx_id:
            tx['status'] = 'canceled'
            tx['updated_at'] = now_str()
            notify_user(tx['student_id'], f"Reservation {tx_id} was canceled.")
            write_json('borrow_transactions', txs)
            return jsonify({'success': True, 'sync_toast': 'Reservation canceled'})
    return jsonify({'success': False}), 404


@app.post('/api/reservations/extend')
def extend_reservation():
    payload = request.get_json(force=True)
    tx_id = payload.get('transaction_id')
    txs = read_json('borrow_transactions')
    for tx in txs:
        if tx.get('transaction_id') != tx_id:
            continue
        base_dt = datetime.strptime(tx['reservation_date'][:10], '%Y-%m-%d')
        extended = base_dt + timedelta(days=3)
        restricted, reason = date_is_restricted(extended)
        if restricted:
            return jsonify({'success': False, 'message': reason}), 400
        tx['reservation_date'] = extended.strftime('%Y-%m-%d')
        tx['updated_at'] = now_str()
        notify_user(tx['student_id'], f"Reservation {tx_id} extended to {tx['reservation_date']}.")
        write_json('borrow_transactions', txs)
        return jsonify({'success': True, 'sync_toast': 'Reservation extended'})
    return jsonify({'success': False}), 404


@app.post('/api/admin/borrow/approve')
def approve_borrow():
    payload = request.get_json(force=True)
    tx_id = payload.get('transaction_id')
    admin_id = payload.get('admin_id', 'admin-root')
    txs = read_json('borrow_transactions')
    for tx in txs:
        if tx.get('transaction_id') == tx_id:
            tx['approval_admin_id'] = admin_id
            tx['approval_date'] = now_str()
            tx['status'] = 'approved'
            token = secrets.token_urlsafe(18)
            QR_TOKENS[token] = tx_id
            notify_user(tx['student_id'], f"Borrow {tx_id} approved by {admin_id}.")
            write_json('borrow_transactions', txs)
            return jsonify({
                'success': True,
                'temporary_link': f"/mobile/borrow-proof/{token}",
                'qr_payload': f"/mobile/borrow-proof/{token}",
                'sync_toast': 'Borrow approved + QR link generated',
            })
    return jsonify({'success': False}), 404


@app.post('/api/mobile/upload-proof/<token>')
def upload_mobile_proof(token):
    tx_id = QR_TOKENS.get(token)
    if not tx_id:
        return jsonify({'success': False, 'message': 'Invalid token'}), 404

    payload = request.get_json(force=True)
    image_data = payload.get('image_data', '')
    if ',' not in image_data:
        return jsonify({'success': False, 'message': 'Missing image payload'}), 400

    _, encoded = image_data.split(',', 1)
    image_bytes = base64.b64decode(encoded)
    filename = f'{tx_id}_{int(datetime.utcnow().timestamp())}.jpg'
    out_path = MEDIA_DIR / filename
    out_path.write_bytes(image_bytes)

    txs = read_json('borrow_transactions')
    for tx in txs:
        if tx.get('transaction_id') == tx_id:
            tx['proof_image_path'] = f'/media/book_borrow_transaction_photos/{filename}'
            tx['updated_at'] = now_str()
            notify_user(tx['student_id'], f'Proof image uploaded for transaction {tx_id}.')
            break
    write_json('borrow_transactions', txs)
    return jsonify({'success': True, 'path': f'/media/book_borrow_transaction_photos/{filename}'})


@app.get('/api/admin/live_log')
def live_log():
    rows = []
    for tx in read_json('borrow_transactions'):
        rows.append({
            'transaction_id': tx.get('transaction_id'),
            'student_id': tx.get('student_id'),
            'book_id': tx.get('book_id'),
            'status': tx.get('status', 'pending'),
            'approval_admin_id': tx.get('approval_admin_id', ''),
            'proof_image_path': tx.get('proof_image_path', ''),
            'reservation_date': tx.get('reservation_date', ''),
            'approval_date': tx.get('approval_date', ''),
        })
    return jsonify(rows)


if __name__ == '__main__':
    app.run(debug=True)

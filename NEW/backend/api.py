from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request


def get_service():
    return current_app.config['LBAS_SERVICE']


def create_api_blueprint() -> Blueprint:
    api = Blueprint('api', __name__, url_prefix='/api')

    @api.get('/health')
    def health():
        service = get_service()
        return jsonify(
            {
                'ok': True,
                'service': 'lbas-new-backend',
                'files': list(service.store.file_map.keys()),
                'active_qr_tokens': len(service.qr_tokens),
            }
        )

    @api.get('/registration_requests')
    def list_registration_requests():
        return jsonify(get_service().store.read('registration_requests'))

    @api.post('/registration_requests')
    def create_registration_request():
        row = get_service().create_registration_request(request.get_json(force=True))
        return jsonify({'success': True, 'request': row})

    @api.post('/admin/registration_requests/<request_id>/approve')
    def approve_registration(request_id: str):
        success = get_service().approve_registration(request_id)
        if not success:
            return jsonify({'success': False, 'message': 'request not found'}), 404
        return jsonify({'success': True})

    @api.get('/users/<student_id>')
    def user(student_id: str):
        target = student_id.lower()
        for row in get_service().store.read('users'):
            if row.get('student_id') == target:
                return jsonify(row)
        return jsonify({'message': 'user not found'}), 404

    @api.get('/users/<student_id>/notifications')
    def user_notifications(student_id: str):
        target = student_id.lower()
        for row in get_service().store.read('users'):
            if row.get('student_id') == target:
                return jsonify(row.get('notifications', []))
        return jsonify([])

    @api.get('/transactions')
    def list_transactions():
        return jsonify(get_service().store.read('borrow_transactions'))

    @api.post('/reservations')
    def create_reservation():
        payload = request.get_json(force=True)
        if not payload.get('student_id') or not payload.get('book_id'):
            return jsonify({'success': False, 'message': 'student_id and book_id are required'}), 400
        row = get_service().create_reservation(payload)
        return jsonify({'success': True, 'transaction': row}), 201

    @api.post('/reservations/cancel')
    def cancel_reservation():
        payload = request.get_json(force=True)
        tx_id = payload.get('transaction_id')
        if not tx_id:
            return jsonify({'success': False, 'message': 'transaction_id is required'}), 400
        success = get_service().cancel_reservation(tx_id)
        if not success:
            return jsonify({'success': False, 'message': 'Transaction not found'}), 404
        return jsonify({'success': True, 'sync_toast': 'Reservation canceled'})

    @api.post('/reservations/extend')
    def extend_reservation():
        payload = request.get_json(force=True)
        tx_id = payload.get('transaction_id')
        if not tx_id:
            return jsonify({'success': False, 'message': 'transaction_id is required'}), 400
        success, msg = get_service().extend_reservation(tx_id)
        if not success:
            status_code = 404 if msg == 'Transaction not found' else 400
            return jsonify({'success': False, 'message': msg}), status_code
        return jsonify({'success': True, 'sync_toast': msg})

    @api.post('/admin/borrow/approve')
    def approve_borrow():
        payload = request.get_json(force=True)
        tx_id = payload.get('transaction_id')
        admin_id = payload.get('admin_id', 'admin-root')
        if not tx_id:
            return jsonify({'success': False, 'message': 'transaction_id is required'}), 400
        result = get_service().approve_borrow(tx_id, admin_id)
        if not result:
            return jsonify({'success': False, 'message': 'Transaction not found'}), 404
        token = result['token']
        minutes = result['minutes']
        return jsonify(
            {
                'success': True,
                'temporary_link': f'/mobile/borrow-proof/{token}',
                'qr_payload': f'/mobile/borrow-proof/{token}',
                'expires_in_minutes': minutes,
                'sync_toast': 'Borrow approved + QR link generated',
            }
        )

    @api.post('/mobile/upload-proof/<token>')
    def upload_mobile_proof(token: str):
        payload = request.get_json(force=True)
        image_data = payload.get('image_data', '')
        success, message, path = get_service().upload_mobile_proof(token, image_data)
        if not success:
            status = 404 if message == 'Invalid token' else 400
            return jsonify({'success': False, 'message': message}), status
        return jsonify({'success': True, 'path': path})

    @api.get('/admin/live_log')
    def live_log():
        rows = []
        for tx in get_service().store.read('borrow_transactions'):
            rows.append(
                {
                    'transaction_id': tx.get('transaction_id'),
                    'student_id': tx.get('student_id'),
                    'book_id': tx.get('book_id'),
                    'status': tx.get('status', 'pending'),
                    'approval_admin_id': tx.get('approval_admin_id', ''),
                    'proof_image_path': tx.get('proof_image_path', ''),
                    'reservation_date': tx.get('reservation_date', ''),
                    'approval_date': tx.get('approval_date', ''),
                }
            )
        return jsonify(rows)

    @api.post('/admin/qr_tokens/cleanup')
    def cleanup_tokens():
        count = get_service().cleanup_expired_tokens()
        return jsonify({'success': True, 'cleaned': count})

    return api

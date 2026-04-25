from __future__ import annotations

import base64
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .datastore import JsonStore


class LbasService:
    def __init__(self, store: JsonStore, media_dir: Path) -> None:
        self.store = store
        self.media_dir = media_dir
        self.qr_tokens: dict[str, dict[str, Any]] = {}

    @staticmethod
    def now_str() -> str:
        return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    def token_is_expired(self, token: str) -> bool:
        token_row = self.qr_tokens.get(token)
        if not token_row:
            return True
        return datetime.utcnow() > token_row['expires_at']

    def get_tx_photo_dir(self, transaction_id: str) -> Path:
        tx_dir = self.media_dir / transaction_id
        tx_dir.mkdir(parents=True, exist_ok=True)
        return tx_dir

    def notify_user(self, student_id: str, message: str) -> None:
        users = self.store.read('users')
        for user in users:
            if user.get('student_id') == student_id:
                user.setdefault('notifications', []).insert(
                    0,
                    {
                        'message': message,
                        'timestamp': self.now_str(),
                        'unread': True,
                    },
                )
                break
        self.store.write('users', users)

    def date_is_restricted(self, date_obj: datetime) -> tuple[bool, str]:
        manual = {row['date']: row for row in self.store.read('date_restrictions') if 'date' in row}
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

    def create_registration_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        rows = self.store.read('registration_requests')
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
            'created_at': self.now_str(),
        }
        rows.append(row)
        self.store.write('registration_requests', rows)
        return row

    def approve_registration(self, request_id: str) -> bool:
        requests_db = self.store.read('registration_requests')
        users = self.store.read('users')
        for req in requests_db:
            if req.get('request_id') != request_id:
                continue
            req['status'] = 'approved'
            users.append(
                {
                    'student_id': req['student_id'],
                    'name': req['name'],
                    'avatar_path': req.get('avatar_path', '/media/avatars/default.png'),
                    'school_level': req.get('school_level', ''),
                    'year': req.get('year', ''),
                    'course': req.get('course', ''),
                    'contact': req.get('contact', ''),
                    'notifications': [
                        {
                            'message': 'Your registration has been approved.',
                            'timestamp': self.now_str(),
                            'unread': True,
                        }
                    ],
                }
            )
            self.store.write('registration_requests', requests_db)
            self.store.write('users', users)
            return True
        return False

    def create_reservation(self, payload: dict[str, Any]) -> dict[str, Any]:
        txs = self.store.read('borrow_transactions')
        row = {
            'transaction_id': f"BTX-{len(txs)+1:04d}",
            'student_id': payload['student_id'].lower(),
            'book_id': payload['book_id'],
            'approval_admin_id': '',
            'proof_image_path': '',
            'reservation_date': payload.get('reservation_date') or datetime.utcnow().strftime('%Y-%m-%d'),
            'approval_date': '',
            'status': 'reserved',
            'extension_count': 0,
            'created_at': self.now_str(),
        }
        txs.append(row)
        self.store.write('borrow_transactions', txs)
        return row

    def cancel_reservation(self, transaction_id: str) -> bool:
        txs = self.store.read('borrow_transactions')
        for tx in txs:
            if tx.get('transaction_id') == transaction_id:
                tx['status'] = 'canceled'
                tx['updated_at'] = self.now_str()
                self.notify_user(tx['student_id'], f'Reservation {transaction_id} was canceled.')
                self.store.write('borrow_transactions', txs)
                return True
        return False

    def extend_reservation(self, transaction_id: str) -> tuple[bool, str]:
        txs = self.store.read('borrow_transactions')
        for tx in txs:
            if tx.get('transaction_id') != transaction_id:
                continue
            base_dt = datetime.strptime(tx['reservation_date'][:10], '%Y-%m-%d')
            extended = base_dt + timedelta(days=3)
            restricted, reason = self.date_is_restricted(extended)
            if restricted:
                return False, reason
            tx['reservation_date'] = extended.strftime('%Y-%m-%d')
            tx['extension_count'] = int(tx.get('extension_count', 0)) + 1
            tx['updated_at'] = self.now_str()
            self.notify_user(tx['student_id'], f"Reservation {transaction_id} extended to {tx['reservation_date']}.")
            self.store.write('borrow_transactions', txs)
            return True, 'Reservation extended'
        return False, 'Transaction not found'

    def approve_borrow(self, transaction_id: str, admin_id: str) -> dict[str, Any] | None:
        txs = self.store.read('borrow_transactions')
        for tx in txs:
            if tx.get('transaction_id') != transaction_id:
                continue
            tx['approval_admin_id'] = admin_id
            tx['approval_date'] = self.now_str()
            tx['status'] = 'approved'
            token = secrets.token_urlsafe(18)
            self.qr_tokens[token] = {
                'tx_id': transaction_id,
                'expires_at': datetime.utcnow() + timedelta(minutes=15),
            }
            self.notify_user(tx['student_id'], f'Borrow {transaction_id} approved by {admin_id}.')
            self.store.write('borrow_transactions', txs)
            return {'token': token, 'minutes': 15}
        return None

    def upload_mobile_proof(self, token: str, image_data: str) -> tuple[bool, str, str | None]:
        token_row = self.qr_tokens.get(token)
        if not token_row or self.token_is_expired(token):
            self.qr_tokens.pop(token, None)
            return False, 'Invalid token', None
        if ',' not in image_data:
            return False, 'Missing image payload', None

        tx_id = token_row['tx_id']
        _, encoded = image_data.split(',', 1)
        image_bytes = base64.b64decode(encoded)
        filename = f'{int(datetime.utcnow().timestamp())}.jpg'
        rel_path = f'/media/book_borrow_transaction_photos/{tx_id}/{filename}'
        out_path = self.get_tx_photo_dir(tx_id) / filename
        out_path.write_bytes(image_bytes)

        txs = self.store.read('borrow_transactions')
        for tx in txs:
            if tx.get('transaction_id') == tx_id:
                tx['proof_image_path'] = rel_path
                tx['updated_at'] = self.now_str()
                self.notify_user(tx['student_id'], f'Proof image uploaded for transaction {tx_id}.')
                break
        self.store.write('borrow_transactions', txs)
        return True, 'Uploaded', rel_path

    def cleanup_expired_tokens(self) -> int:
        now = datetime.utcnow()
        expired = [token for token, row in self.qr_tokens.items() if now > row['expires_at']]
        for token in expired:
            self.qr_tokens.pop(token, None)
        return len(expired)

from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, render_template, send_from_directory

from backend import JsonStore, LbasService, create_api_blueprint

BASE_DIR = Path(__file__).resolve().parent
MEDIA_DIR = Path('/media/book_borrow_transaction_photos')
if not MEDIA_DIR.exists():
    MEDIA_DIR = BASE_DIR / 'media' / 'book_borrow_transaction_photos'
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

FILE_MAP = {
    'users': 'users.json',
    'registration_requests': 'registration_requests.json',
    'borrow_transactions': 'borrow_transactions.json',
    'date_restrictions': 'date_restrictions.json',
}


def create_app(base_dir: Path | None = None, media_dir: Path | None = None) -> Flask:
    app = Flask(__name__, template_folder='templates', static_folder='.')

    data_dir = base_dir or BASE_DIR
    files = {key: str(Path(name)) for key, name in FILE_MAP.items()}
    store = JsonStore(data_dir, files)
    store.ensure_files()

    effective_media_dir = media_dir or MEDIA_DIR
    effective_media_dir.mkdir(parents=True, exist_ok=True)
    service = LbasService(store, effective_media_dir)
    app.config['LBAS_SERVICE'] = service

    app.register_blueprint(create_api_blueprint())

    @app.get('/')
    def home():
        return render_template('student_portal.html')

    @app.get('/admin')
    def admin():
        return render_template('admin_dashboard.html')

    @app.get('/mobile/borrow-proof/<token>')
    def mobile_borrow_proof(token: str):
        token_row = service.qr_tokens.get(token)
        if not token_row or service.token_is_expired(token):
            service.qr_tokens.pop(token, None)
            return jsonify({'success': False, 'message': 'Invalid or expired link'}), 404
        tx_id = token_row['tx_id']
        return render_template('mobile_qr_capture.html', token=token, transaction_id=tx_id)

    @app.get('/media/book_borrow_transaction_photos/<path:filename>')
    def media_file(filename: str):
        return send_from_directory(str(effective_media_dir), filename)

    return app


app = create_app()


if __name__ == '__main__':
    app.run(debug=True)

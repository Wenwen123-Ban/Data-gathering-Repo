# NEW (LBAS Experimental Branch Reconstruction - JSON Phase)

This folder is the transition workspace for LBAS v3.1 flow reconstruction using **JSON-only** storage.

## Run
```bash
cd NEW
python app.py
```

The backend now boots through a startup manager that verifies JSON collections and then launches all API routes.

## Backend architecture
- `backend/datastore.py` → JSON file manager (`JsonStore`) with startup validation.
- `backend/services.py` → LBAS business logic (registration, reservation, approval, QR proof upload).
- `backend/api.py` → Flask Blueprint that exposes all `/api/*` endpoints.
- `app.py` → app factory (`create_app`) that wires pages + API + media serving.

## API endpoints
- `GET /api/health`
- `GET|POST /api/registration_requests`
- `POST /api/admin/registration_requests/<request_id>/approve`
- `GET /api/users/<student_id>`
- `GET /api/users/<student_id>/notifications`
- `GET /api/transactions`
- `POST /api/reservations`
- `POST /api/reservations/cancel`
- `POST /api/reservations/extend`
- `POST /api/admin/borrow/approve`
- `POST /api/mobile/upload-proof/<token>`
- `GET /api/admin/live_log`
- `POST /api/admin/qr_tokens/cleanup`

## Notes
- Existing runtime JSONs (`users.json`, `registration_requests.json`, `borrow_transactions.json`, `date_restrictions.json`) remain compatible.
- Media uploads are stored under `/media/book_borrow_transaction_photos/` when available, else `NEW/media/book_borrow_transaction_photos/`.

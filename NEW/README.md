# NEW (LBAS Experimental Branch Reconstruction - JSON Phase)

This folder is the clean transition workspace requested for LBAS v3.1 flow reconstruction using **JSON-only** storage.

## Run
```bash
cd NEW
python app.py
```

## Implemented modules
- JSON data model (`registration_requests.json`, `users.json`, `borrow_transactions.json`).
- Student User Management portal with Reservations List, Cancel/Extend logic, notification polling, and Approved By column.
- Mobile QR trigger route with direct camera capture upload to `/media/book_borrow_transaction_photos/`.
- Admin dashboard registration-request pipeline and borrowed-book live log chart linked to `proof_image_path`.
- Sync pop toasts for status changes and Phase 9 date restriction enforcement on extend.

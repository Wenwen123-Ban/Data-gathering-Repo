"""
Seeds demo data. Safe to run multiple times — skips existing records.
    python manage.py seed_demo
"""
from django.core.management.base import BaseCommand
from core.models import UserProfile, Book, HomeCard, Category, RegistrationRequest


BOOKS = {
    'Science': [
        ('SCI-001', 'Introduction to Physics'),
        ('SCI-002', 'Biology: Life on Earth'),
        ('SCI-003', 'Chemistry Fundamentals'),
        ('SCI-004', 'Earth Science Essentials'),
        ('SCI-005', 'Environmental Science Today'),
    ],
    'Mathematics': [
        ('MATH-001', 'Algebra and Trigonometry'),
        ('MATH-002', 'Calculus for Beginners'),
        ('MATH-003', 'Statistics and Probability'),
        ('MATH-004', 'Discrete Mathematics'),
        ('MATH-005', 'Linear Algebra Basics'),
    ],
    'Literature': [
        ('LIT-001', 'Philippine Literature Anthology'),
        ('LIT-002', 'World Classics Collection'),
        ('LIT-003', 'Introduction to Poetry'),
        ('LIT-004', 'Fiction Writing Workshop'),
        ('LIT-005', 'Reading and Critical Thinking'),
    ],
    'General': [
        ('GEN-001', 'Research Methods for Students'),
        ('GEN-002', 'Study Skills and Time Management'),
        ('GEN-003', 'Introduction to Computer Science'),
        ('GEN-004', 'Ethics and Values Education'),
        ('GEN-005', 'Practical Communication Skills'),
    ],
}


class Command(BaseCommand):
    help = 'Seeds demo data for LBAS'

    def handle(self, *args, **kwargs):
        self.stdout.write('[seed] Cleaning up stale photo references...')
        import os
        from django.conf import settings
        AVATARS = {f'avatar_{a}.svg' for a in ['fox','bear','rabbit','cat','dog','panda','owl','penguin']} | {'default.png'}
        fixed = 0
        for user in UserProfile.objects.all():
            if user.photo and user.photo not in AVATARS:
                full = os.path.join(settings.MEDIA_ROOT, user.photo)
                if not os.path.isfile(full):
                    user.photo = 'default.png'
                    user.save(update_fields=['photo'])
                    fixed += 1
        if fixed:
            self.stdout.write(f'  Fixed {fixed} stale user photo reference(s)')

        # Also clean registration requests
        from core.models import RegistrationRequest
        for req in RegistrationRequest.objects.all():
            if req.photo and req.photo not in AVATARS:
                full = os.path.join(settings.MEDIA_ROOT, req.photo)
                if not os.path.isfile(full):
                    req.photo = 'default.png'
                    req.save(update_fields=['photo'])

        self.stdout.write('[seed] Seeding users...')

        _, created = UserProfile.objects.get_or_create(
            school_id='admin',
            defaults={
                'name': 'System Administrator',
                'password': 'admin',
                'category': 'Staff',
                'is_staff': True,
                'status': 'approved',
                'photo': 'avatar_owl.svg',
            },
        )
        if not created:
            UserProfile.objects.filter(school_id='admin').update(photo='avatar_owl.svg')
        self.stdout.write(f'  Admin account: {"created" if created else "already exists (skipped)"}')

        _, created = UserProfile.objects.get_or_create(
            school_id='2024-00001',
            defaults={
                'name': 'Demo Student',
                'password': 'student123',
                'category': 'Student',
                'is_staff': False,
                'status': 'approved',
                'photo': 'avatar_fox.svg',
                'year_level': '1',
                'school_level': 'college',
                'course': 'BSIT',
            },
        )
        if not created:
            UserProfile.objects.filter(school_id='2024-00001').update(photo='avatar_fox.svg')
        self.stdout.write(f'  Demo student: {"created" if created else "already exists (skipped)"}')

        self.stdout.write('[seed] Seeding categories...')
        for cat in ['General', 'Mathematics', 'Science', 'Literature']:
            _, created = Category.objects.get_or_create(name=cat)
            if created:
                self.stdout.write(f'  Category created: {cat}')

        self.stdout.write('[seed] Seeding books...')
        book_count = 0
        for category, book_list in BOOKS.items():
            for book_no, title in book_list:
                _, created = Book.objects.get_or_create(
                    book_no=book_no,
                    defaults={'title': title, 'category': category, 'status': 'Available'},
                )
                if created:
                    book_count += 1
        self.stdout.write(f'  Books: {book_count} added (skipped existing)')

        step_cards = [
            (1, 'Step 1 — Create an Account',
                'Click "Log in" on the navigation bar then choose "Sign Up". Fill in your name, School ID, password, year level, course, and at least one contact (phone or email). Pick an avatar and submit. Wait for the librarian to approve your account before you can log in.'),
            (2, 'Step 2 — Browse & Reserve a Book',
                'Go to the Books page and search or filter by category to find the book you need. Click "Reserve" on any available book. Fill in your preferred pickup schedule and contact details, then confirm your reservation.'),
            (3, 'Step 3 — Pick Up Your Book',
                'Visit the library on your scheduled pickup date. Show your School ID to the librarian. The librarian will process your reservation and hand over the book. Your borrow period starts from this date.'),
            (4, 'Step 4 — Return on Time',
                'Return the book to the library on or before the due date shown in your account panel. The librarian will mark it as returned. Returning on time keeps your account in good standing and lets other students reserve the book.'),
        ]
        for card_id, title, body in step_cards:
            obj, created = HomeCard.objects.get_or_create(card_id=card_id)
            # Always update so changes reflect on restart
            obj.title = title
            obj.body = body
            obj.save()

        self.stdout.write(self.style.SUCCESS(
            '\n[seed] Done. Login: admin / admin  |  Student: 2024-00001 / student123'
        ))

from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Adds email to UserProfile and phone_number/email to RegistrationRequest.
    Uses RunSQL with IF NOT EXISTS so it's safe even if columns already exist
    (prevents crash on databases that were partially migrated before).
    """
    dependencies = [
        ('core', '0002_category'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE lbas_users
                        ADD COLUMN IF NOT EXISTS email VARCHAR(150) NOT NULL DEFAULT '';
                    """,
                    reverse_sql="ALTER TABLE lbas_users DROP COLUMN IF EXISTS email;"
                ),
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE lbas_registration_requests
                        ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20) NOT NULL DEFAULT '';
                    """,
                    reverse_sql="ALTER TABLE lbas_registration_requests DROP COLUMN IF EXISTS phone_number;"
                ),
                migrations.RunSQL(
                    sql="""
                        ALTER TABLE lbas_registration_requests
                        ADD COLUMN IF NOT EXISTS email VARCHAR(150) NOT NULL DEFAULT '';
                    """,
                    reverse_sql="ALTER TABLE lbas_registration_requests DROP COLUMN IF EXISTS email;"
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name='userprofile',
                    name='email',
                    field=models.CharField(blank=True, max_length=150),
                ),
                migrations.AddField(
                    model_name='registrationrequest',
                    name='phone_number',
                    field=models.CharField(blank=True, max_length=20),
                ),
                migrations.AddField(
                    model_name='registrationrequest',
                    name='email',
                    field=models.CharField(blank=True, max_length=150),
                ),
            ],
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        CREATE TABLE IF NOT EXISTS lbas_categories (
                            id BIGINT AUTO_INCREMENT PRIMARY KEY,
                            name VARCHAR(100) NOT NULL UNIQUE,
                            created_at DATETIME(6) NOT NULL
                        ) CHARACTER SET utf8mb4;
                    """,
                    reverse_sql="DROP TABLE IF EXISTS lbas_categories;"
                ),
            ],
            state_operations=[
                migrations.CreateModel(
                    name='Category',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('name', models.CharField(max_length=100, unique=True)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                    ],
                    options={'db_table': 'lbas_categories'},
                ),
            ],
        ),
    ]

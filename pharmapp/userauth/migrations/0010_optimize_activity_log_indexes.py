from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('userauth', '0009_add_password_change_history'),
    ]

    operations = [
        # Add a composite index for user and timestamp queries
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_activitylog_user_timestamp ON userauth_activitylog(user_id, timestamp DESC);",
            reverse_sql="DROP INDEX IF EXISTS idx_activitylog_user_timestamp;"
        ),
        # Add a composite index for timestamp alone for better ordering
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_activitylog_timestamp ON userauth_activitylog(timestamp DESC);",
            reverse_sql="DROP INDEX IF EXISTS idx_activitylog_timestamp;"
        ),
    ]

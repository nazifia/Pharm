from django.db import migrations


def create_activity_log_indexes(apps, schema_editor):
    """Create indexes with MySQL-compatible syntax"""
    # Use schema_editor.connection to get the correct connection during migrations
    db_engine = schema_editor.connection.vendor.lower()
    
    if db_engine == 'mysql':
        # MySQL: Check if index exists before creating
        # Note: MySQL doesn't support DESC in index columns for older versions
        indexes_to_create = [
            ('idx_activitylog_user_timestamp', 'userauth_activitylog', 'user_id, timestamp'),
            ('idx_activitylog_timestamp', 'userauth_activitylog', 'timestamp'),
        ]
        
        with schema_editor.connection.cursor() as cursor:
            for index_name, table_name, columns in indexes_to_create:
                # Check if index exists
                cursor.execute("""
                    SELECT COUNT(1) FROM information_schema.STATISTICS 
                    WHERE table_schema = DATABASE() 
                    AND table_name = %s 
                    AND index_name = %s
                """, [table_name, index_name])
                
                if cursor.fetchone()[0] == 0:
                    # Index doesn't exist, create it
                    try:
                        cursor.execute(f"CREATE INDEX {index_name} ON {table_name}({columns})")
                    except Exception as e:
                        # Ignore if index already exists or other non-critical errors
                        print(f"Warning: Could not create index {index_name}: {e}")
    else:
        # SQLite and others: Use IF NOT EXISTS syntax
        with schema_editor.connection.cursor() as cursor:
            try:
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_activitylog_user_timestamp "
                    "ON userauth_activitylog(user_id, timestamp)"
                )
            except Exception:
                pass
            try:
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_activitylog_timestamp "
                    "ON userauth_activitylog(timestamp)"
                )
            except Exception:
                pass


def drop_activity_log_indexes(apps, schema_editor):
    """Drop indexes with database-agnostic syntax"""
    # Use schema_editor.connection to get the correct connection during migrations
    db_engine = schema_editor.connection.vendor.lower()
    
    indexes_to_drop = [
        'idx_activitylog_user_timestamp',
        'idx_activitylog_timestamp',
    ]
    
    with schema_editor.connection.cursor() as cursor:
        for index_name in indexes_to_drop:
            try:
                if db_engine == 'mysql':
                    cursor.execute(f"DROP INDEX {index_name} ON userauth_activitylog")
                else:
                    cursor.execute(f"DROP INDEX IF EXISTS {index_name}")
            except Exception:
                # Ignore if index doesn't exist
                pass


class Migration(migrations.Migration):

    dependencies = [
        ('userauth', '0009_add_password_change_history'),
    ]

    operations = [
        migrations.RunPython(
            create_activity_log_indexes,
            reverse_code=drop_activity_log_indexes,
        ),
    ]

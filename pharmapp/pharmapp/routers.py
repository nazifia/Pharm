class OfflineRouter:
    """
    Router to handle offline/online database switching
    """
    def db_for_read(self, model, **hints):
        """
        Point all read operations to the appropriate database
        """
        from threading import local
        thread_local = local()
        return getattr(thread_local, 'current_database', 'default')

    def db_for_write(self, model, **hints):
        """
        Point all write operations to the appropriate database
        """
        from threading import local
        thread_local = local()
        return getattr(thread_local, 'current_database', 'default')

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow any relation between objects
        """
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Make sure all models are available in both databases
        """
        return True
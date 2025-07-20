from django.core.cache import cache

def marquee_context(request):
    """
    Context processor for marquee text.
    Uses global cache for marquee text as it's intended to be shared across all users.
    """
    return {
        'marquee_text': cache.get('global_marquee_text', 'WELCOME TO NAZZ PHARMACY')
    }
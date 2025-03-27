from django.core.cache import cache

def marquee_context(request):
    return {
        'marquee_text': cache.get('marquee_text', 'WELCOME TO NAZZ PHARMACY')
    }
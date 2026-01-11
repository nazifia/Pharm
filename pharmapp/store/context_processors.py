from django.core.cache import cache
from django.conf import settings

def marquee_context(request):
    """
    Context processor for marquee text.
    Uses global cache for marquee text as it's intended to be shared across all users.
    """
    return {
        'marquee_text': cache.get('global_marquee_text', 'WELCOME TO ANEEQ PHARMACY')
    }

def contact_info_context(request):
    """
    Context processor for pharmacy contact information.
    Provides phone number and other contact details for templates.
    """
    return {
        'pharmacy_phone': getattr(settings, 'PHARMACY_PHONE', '+234-8164707897'),
        'pharmacy_address': getattr(settings, 'PHARMACY_ADDRESS', 'No.4 Ali gizanda plaza, beside gidan Sarki, along katsina General Hospital Road, Katsina'),
        'pharmacy_email': getattr(settings, 'PHARMACY_EMAIL', 'info@nazzpharmacy.com'),
#         'marquee_text': cache.get('global_marquee_text', 'WELCOME TO ANEEQ PHARMACY')
    }
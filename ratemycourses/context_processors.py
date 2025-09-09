from django.conf import settings


def owner_info(request):
    """
    Add owner information to template context for legal pages.
    """
    return {
        'owner_name': getattr(settings, 'OWNER_NAME', '[Ihr Name]'),
        'owner_address': getattr(settings, 'OWNER_ADDRESS', '[Ihre Adresse]'),
        'owner_city': getattr(settings, 'OWNER_CITY', '[PLZ und Ort]'),
        'owner_email': getattr(settings, 'OWNER_EMAIL', '[ihre-email@domain.de]'),
        'owner_phone': getattr(settings, 'OWNER_PHONE', '[Ihre Telefonnummer]'),
    }

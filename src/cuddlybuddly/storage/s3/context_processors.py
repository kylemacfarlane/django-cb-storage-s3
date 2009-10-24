from django.conf import settings


def media(request):
    if request.is_secure() or \
       getattr(request.META, 'HTTP_X_FORWARDED_SSL', 'off') == 'on':
        if hasattr(settings.MEDIA_URL, 'https'):
            url = settings.MEDIA_URL.https()
        else:
            url = settings.MEDIA_URL.replace('http://', 'https://')
    else:
        url = settings.MEDIA_URL.replace('https://', 'http://')
    return {'MEDIA_URL': url}

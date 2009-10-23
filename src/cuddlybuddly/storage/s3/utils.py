from django.conf import settings
from cuddlybuddly.storage.s3.lib import QueryStringAuthGenerator


def create_signed_url(file, expires=60, secure=False):
    generator = QueryStringAuthGenerator(
        settings.AWS_ACCESS_KEY_ID,
        settings.AWS_SECRET_ACCESS_KEY,
        calling_format=settings.AWS_CALLING_FORMAT,
        is_secure=secure)
    generator.set_expires_in(expires)
    return generator.generate_url(
        'GET',
        settings.AWS_STORAGE_BUCKET_NAME,
        file
    )

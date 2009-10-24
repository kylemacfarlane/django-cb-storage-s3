import re
from django.conf import settings
from cuddlybuddly.storage.s3 import CallingFormat
from cuddlybuddly.storage.s3.lib import QueryStringAuthGenerator


def create_signed_url(file, expires=60, secure=False):
    generator = QueryStringAuthGenerator(
        settings.AWS_ACCESS_KEY_ID,
        settings.AWS_SECRET_ACCESS_KEY,
        calling_format=getattr(settings, 'AWS_CALLING_FORMAT',
                               CallingFormat.SUBDOMAIN),
        is_secure=secure)
    generator.set_expires_in(expires)
    return generator.generate_url(
        'GET',
        settings.AWS_STORAGE_BUCKET_NAME,
        file
    )


class CloudFrontURLs(unicode):
    def __new__(cls, default, patterns={}, https=None):
        obj = super(CloudFrontURLs, cls).__new__(cls, default)
        obj._patterns = []
        for key, value in patterns.iteritems():
            obj._patterns.append((re.compile(key), unicode(value)))
        obj._https = https
        return obj

    def match(self, name):
        for pattern in self._patterns:
            if pattern[0].match(name):
                return pattern[1]
        return self

    def https(self):
        if self._https is not None:
            return unicode(self._https)
        return self

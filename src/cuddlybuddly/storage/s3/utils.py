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


class CloudFrontURLs(object):
    def __init__(self, default, patterns={}, https=None):
        self._default = default
        self._patterns = []
        for key, value in patterns.iteritems():
            self._patterns.append((re.compile(key), value))
        self._https = https

    def match(self, name):
        for pattern in self._patterns:
            if pattern[0].match(name):
                return pattern[1]
        return self._default

    def __getattribute__(self, name):
        if name in ('_default', '_patterns', '_https', 'https', 'match',
                    '__unicode__'):
            return object.__getattribute__(self, name)
        return getattr(unicode(self.__unicode__()), name)

    def https(self):
        if self._https is not None:
            return unicode(self._https)
        return self.__unicode__()

    def __unicode__(self):
        return unicode(self._default)

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
    def __init__(self, cnames, https=None):
        self.cnames = cnames
        self.https = https
        self._counter = 1

    def __getattribute__(self, name):
        if name in ('https', '_get_cname', '_counter', 'cnames'):
            return object.__getattribute__(self, name)
        return getattr(unicode(self._get_cname()), name)

    def https(self):
        if self.https is not None:
            return unicode(self.https)
        return self._get_cname()

    def _get_cname(self):
        self._counter = self._counter + 1
        if self._counter > len(self.cnames):
            self._counter = 1
        return unicode(self.cnames[self._counter-1])

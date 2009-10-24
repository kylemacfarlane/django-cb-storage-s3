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


def CloudFrontURLs(object):
    def __init__(self, cnames, https=None):
        self.cnames = cnames
        self.https = https
        self.__counter = 1

    def https(self):
        if self.https is not None:
            return self.https
        return self.__unicode__()

    def __unicode__(self):
        self.__counter = self.__counter + 1
        if self.__counter > len(self.cnames):
            self.__counter = 1
        return self.cnames[self.__counter-1]

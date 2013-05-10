import base64
import json
import re
import rsa
import time
from urlparse import urljoin
from django.conf import settings
from django.utils.encoding import iri_to_uri
from cuddlybuddly.storage.s3 import CallingFormat
from cuddlybuddly.storage.s3.lib import QueryStringAuthGenerator
from cuddlybuddly.storage.s3.middleware import request_is_secure


def create_signed_url(file, expires=60, secure=False, private_cloudfront=False, expires_at=None):
    if not private_cloudfront:
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

    url = settings.MEDIA_URL
    if not isinstance(settings.MEDIA_URL, CloudFrontURLs):
        url = CloudFrontURLs(settings.MEDIA_URL)
    url = url.get_url(file, force_https=True if secure else False)

    if expires_at is None:
        expires = int(time.time() + expires)
    else:
        expires = expires_at

    policy = {
        'Statement': [{
            'Resource': url,
            'Condition': {
                'DateLessThan': {
                    'AWS:EpochTime': expires
                }
            }
        }]
    }

    key = settings.CUDDLYBUDDLY_STORAGE_S3_KEY_PAIR
    policy = json.dumps(policy, separators=(',',':'))
    sig = rsa.PrivateKey.load_pkcs1(key[1])
    sig = rsa.sign(policy, sig, 'SHA-1')
    sig = base64.b64encode(sig).replace('+', '-').replace('=', '_').replace('/', '~')

    return '%s%sExpires=%s&Signature=%s&Key-Pair-Id=%s' % (
        url,
        '&' if '?' in url else '?',
        expires,
        sig,
        key[0]
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
        return self.replace('http://', 'https://')

    def get_url(self, path, force_https=False):
        if force_https or request_is_secure():
            url = self.https()
        else:
            url = self.match(path).replace('https://', 'http://')
        return urljoin(url, iri_to_uri(path))

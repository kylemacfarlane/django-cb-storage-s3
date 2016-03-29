import base64
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
import json
import re
import sys
import time
try:
    from urllib.parse import unquote # Python 3
except ImportError:
    from urllib2 import unquote # Python 2
try:
    from urllib.parse import urljoin, urlparse, urlunparse # Python 3
except ImportError:
    from urlparse import urljoin, urlparse, urlunparse # Python 2
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA
from django.conf import settings
from django.utils.http import urlquote
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

    if url.startswith('//'):
        # A protocol is needed for correct signing
        if secure:
            url = 'https:' + url
        else:
            url = 'http:' + url

    if expires_at is None:
        expires = int(time.time() + expires)
    else:
        expires = expires_at

    # Use OrderedDict to keep things predictable and testable
    policy = OrderedDict()
    policy['Resource'] = url
    policy['Condition'] = {
        'DateLessThan': {
            'AWS:EpochTime': expires
        }
    }
    policy = {
        'Statement': [
            policy
        ]
    }
    policy = json.dumps(policy, separators=(',',':'))

    key = settings.CUDDLYBUDDLY_STORAGE_S3_KEY_PAIR
    dig = SHA.new()
    dig.update(policy.encode('utf-8'))
    sig = PKCS1_v1_5.new(RSA.importKey(key[1]))
    sig = sig.sign(dig)
    sig = base64.b64encode(sig).decode('utf-8')
    sig = sig.replace('+', '-').replace('=', '_').replace('/', '~')

    return '%s%sExpires=%s&Signature=%s&Key-Pair-Id=%s' % (
        url,
        '&' if '?' in url else '?',
        expires,
        sig,
        key[0]
    )


try:
    extend = unicode # Python 2
except NameError:
    extend = str # Python 3


class CloudFrontURLs(extend):
    def __new__(cls, default, patterns={}, https=None):
        obj = super(CloudFrontURLs, cls).__new__(cls, default)
        obj._patterns = []
        for key, value in patterns.items():
            obj._patterns.append((re.compile(key), '%s' % value))
        obj._https = https
        return obj

    def match(self, name):
        for pattern in self._patterns:
            if pattern[0].match(name):
                return pattern[1]
        return self

    def https(self):
        if self._https is not None:
            return '%s' % self._https
        return self.replace('http://', 'https://')

    def get_url(self, path, force_https=False):
        if force_https or request_is_secure():
            url = self.https()
        else:
            url = self.match(path).replace('https://', 'http://')
        url = list(urlparse(urljoin(url, path)))
        if sys.version_info[0] == 2:
            url[2] = url[2].encode('utf-8')
        url[2] = urlquote(unquote(url[2]))
        return urlunparse(url)

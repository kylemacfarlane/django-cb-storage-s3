from email.utils import parsedate
import os
import mimetypes
from time import mktime
import urlparse

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import File
from django.core.files.storage import Storage
from django.utils.http import urlquote_plus
from django.utils.importlib import import_module
from cuddlybuddly.storage.s3 import CallingFormat
from cuddlybuddly.storage.s3.lib import AWSAuthConnection, QueryStringAuthGenerator
from cuddlybuddly.storage.s3.middleware import request_is_secure


ACCESS_KEY_NAME = 'AWS_ACCESS_KEY_ID'
SECRET_KEY_NAME = 'AWS_SECRET_ACCESS_KEY'
HEADERS = 'AWS_HEADERS'


class S3Storage(Storage):
    """Amazon Simple Storage Service"""

    def __init__(self, bucket=None, access_key=None, secret_key=None, acl=None,
            calling_format=None, cache=None, base_url=None):
        if bucket is None:
            bucket = settings.AWS_STORAGE_BUCKET_NAME
        if acl is None:
            acl = getattr(settings, 'AWS_DEFAULT_ACL', 'public-read')
        if calling_format is None:
           calling_format = getattr(settings, 'AWS_CALLING_FORMAT',
                                    CallingFormat.SUBDOMAIN)
        self.bucket = bucket
        self.acl = acl

        if not access_key and not secret_key:
            access_key, secret_key = self._get_access_keys()

        self.connection = AWSAuthConnection(access_key, secret_key,
                            calling_format=calling_format)
        self.generator = QueryStringAuthGenerator(access_key, secret_key,
                            calling_format=calling_format,
                            is_secure=getattr(settings, 'AWS_S3_SECURE_URLS', False))
        self.generator.set_expires_in(getattr(settings, 'AWS_QUERYSTRING_EXPIRE', 60))

        self.headers = getattr(settings, HEADERS, {})

        if cache is not None:
            self.cache = cache
        else:
            cache = getattr(settings, 'CUDDLYBUDDLY_STORAGE_S3_CACHE', None)
            if cache is not None:
                self.cache = self._get_cache_class(cache)()
            else:
                self.cache = None

        if base_url is None:
            base_url = settings.MEDIA_URL
        self.base_url = base_url

    def _get_cache_class(self, import_path=None):
        try:
            dot = import_path.rindex('.')
        except ValueError:
            raise ImproperlyConfigured("%s isn't a cache module." % import_path)
        module, classname = import_path[:dot], import_path[dot+1:]
        try:
            mod = import_module(module)
        except ImportError, e:
            raise ImproperlyConfigured('Error importing cache module %s: "%s"' % (module, e))
        try:
            return getattr(mod, classname)
        except AttributeError:
            raise ImproperlyConfigured('Cache module "%s" does not define a "%s" class.' % (module, classname))

    def _store_in_cache(self, name, response):
        size = int(response.getheader('Content-Length'))
        date = response.getheader('Last-Modified')
        date = mktime(parsedate(date))
        self.cache.save(name, size=size, getmtime=date)

    def _get_access_keys(self):
        access_key = getattr(settings, ACCESS_KEY_NAME, None)
        secret_key = getattr(settings, SECRET_KEY_NAME, None)
        if (access_key or secret_key) and (not access_key or not secret_key):
            access_key = os.environ.get(ACCESS_KEY_NAME)
            secret_key = os.environ.get(SECRET_KEY_NAME)

        if access_key and secret_key:
            # Both were provided, so use them
            return access_key, secret_key

        return None, None

    def _get_connection(self):
        return AWSAuthConnection(*self._get_access_keys())

    def _put_file(self, name, content):
        name = self._path(name)
        placeholder = False
        if self.cache:
            if not self.cache.exists(name):
                self.cache.save(name, 0, 0)
                placedholder = True
        content_type = mimetypes.guess_type(name)[0] or "application/x-octet-stream"
        self.headers.update({'x-amz-acl': self.acl, 'Content-Type': content_type})
        response = self.connection.put(self.bucket, name, content, self.headers)
        if response.http_response.status != 200:
            if placeholder:
                self.cache.remove(name)
            raise IOError("S3StorageError: %s" % response.message)
        if self.cache:
            date = response.http_response.getheader('Date')
            date = mktime(parsedate(date))
            self.cache.save(name, size=len(content), getmtime=date)

    def _open(self, name, mode='rb'):
        remote_file = S3StorageFile(name, self, mode=mode)
        return remote_file

    def _read(self, name, start_range=None, end_range=None):
        name = self._path(name)
        if start_range is None:
            headers = {}
        else:
            headers = {'Range': 'bytes=%s-%s' % (start_range, end_range)}
        response = self.connection.get(self.bucket, name, headers)
        if response.http_response.status != 200:
            raise IOError("S3StorageError: %s" % response.message)
        headers = response.http_response.msg
        return response.object.data, headers.get('etag', None), headers.get('content-range', None)

    def _save(self, name, content):
        content.open()
        if hasattr(content, 'chunks'):
            content_str = ''.join(chunk for chunk in content.chunks())
        else:
            content_str = content.read()
        self._put_file(name, content_str)
        return name

    def delete(self, name):
        name = self._path(name)
        response = self.connection.delete(self.bucket, name)
        if response.http_response.status != 204:
            raise IOError("S3StorageError: %s" % response.message)
        if self.cache:
            self.cache.remove(name)

    def exists(self, name):
        name = self._path(name)
        if self.cache:
            exists = self.cache.exists(name)
            if exists is not None:
                return exists
        response = self.connection._make_request('HEAD', self.bucket, name)
        exists = response.status == 200
        if self.cache and exists:
            self._store_in_cache(name, response)
        return exists

    def size(self, name):
        name = self._path(name)
        if self.cache:
            size = self.cache.size(name)
            if size is not None:
                return size
        response = self.connection._make_request('HEAD', self.bucket, name)
        content_length = response.getheader('Content-Length')
        if self.cache:
            self._store_in_cache(name, response)
        return content_length and int(content_length) or 0

    def getmtime(self, name):
        name = self._path(name)
        if self.cache:
            last_modified = self.cache.getmtime(name)
            if last_modified is not None:
                return last_modified
        response = self.connection._make_request('HEAD', self.bucket, name)
        last_modified = response.getheader('Last-Modified')
        last_modified = last_modified and mktime(parsedate(last_modified)) or \
                float(0)
        if self.cache and last_modified:
            self._store_in_cache(name, response)
        return last_modified

    def url(self, name):
        if self.base_url is None:
            raise ValueError("This file is not accessible via a URL.")
        name = self._path(name)
        if request_is_secure():
            if hasattr(self.base_url, 'https'):
                url = self.base_url.https()
            else:
                if hasattr(self.base_url, 'match'):
                    url = self.base_url.match(name)
                else:
                    url = self.base_url
                url = url.replace('http://', 'https://')
        else:
            if hasattr(self.base_url, 'match'):
                url = self.base_url.match(name)
            else:
                url = self.base_url
            url = url.replace('https://', 'http://')
        return urlparse.urljoin(url, urlquote_plus(name, '/'))

    def listdir(self, path):
        path = self._path(path)
        if not path.endswith('/'):
            path = path+'/'
        directories, files = [], []
        options = {'prefix': path, 'delimiter': '/'}
        response = self.connection.list_bucket(self.bucket, options=options)
        for prefix in response.common_prefixes:
            directories.append(prefix.prefix.replace(path, '').strip('/'))
        for entry in response.entries:
            files.append(entry.key.replace(path, ''))
        return directories, files

    def _path(self, name):
        name = name.replace('\\', '/')
        # Because the S3 lib just loves to add slashes
        if name.startswith('/'):
            name = name[1:]
        return name


class S3StorageFile(File):
    def __init__(self, name, storage, mode):
        self.name = name
        self._storage = storage
        self.mode = mode
        self._is_dirty = False
        self.file = StringIO()
        self.start_range = 0

    @property
    def size(self):
        if not hasattr(self, '_size'):
            self._size = self._storage.size(self.name)
        return self._size

    def read(self, num_bytes=None):
        if num_bytes is None:
            args = []
            self.start_range = 0
        else:
            args = [self.start_range, self.start_range+num_bytes-1]
        data, etags, content_range = self._storage._read(self.name, *args)
        if content_range is not None:
            current_range, size = content_range.split(' ', 1)[1].split('/', 1)
            start_range, end_range = current_range.split('-', 1)
            self._size, self.start_range = int(size), int(end_range)+1
        self.file = StringIO(data)
        return self.file.getvalue()

    def write(self, content):
        if 'w' not in self.mode:
            raise AttributeError("File was opened for read-only access.")
        self.file = StringIO(content)
        self._is_dirty = True

    def close(self):
        if self._is_dirty:
            content = self.file.getvalue()
            self._storage._put_file(self.name, content)
            self._size = len(content)
        self.file.close()

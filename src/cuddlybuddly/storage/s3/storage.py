from calendar import timegm
from datetime import datetime
from email.utils import parsedate
from gzip import GzipFile
import mimetypes
import os
import re
from StringIO import StringIO # Don't use cStringIO as it's not unicode safe
import sys
from urlparse import urljoin
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import File
from django.core.files.storage import Storage
from django.utils.encoding import iri_to_uri
from django.utils.importlib import import_module
from cuddlybuddly.storage.s3 import CallingFormat
from cuddlybuddly.storage.s3.exceptions import S3Error
from cuddlybuddly.storage.s3.lib import AWSAuthConnection
from cuddlybuddly.storage.s3.middleware import request_is_secure


ACCESS_KEY_NAME = 'AWS_ACCESS_KEY_ID'
SECRET_KEY_NAME = 'AWS_SECRET_ACCESS_KEY'
HEADERS = 'AWS_HEADERS'


class S3Storage(Storage):
    """Amazon Simple Storage Service"""

    def __init__(self, bucket=None, access_key=None, secret_key=None,
                 headers=None, calling_format=None, cache=None, base_url=None):
        if bucket is None:
            bucket = settings.AWS_STORAGE_BUCKET_NAME
        if calling_format is None:
           calling_format = getattr(settings, 'AWS_CALLING_FORMAT',
                                    CallingFormat.SUBDOMAIN)
        self.bucket = bucket

        if not access_key and not secret_key:
            access_key, secret_key = self._get_access_keys()

        self.connection = AWSAuthConnection(access_key, secret_key,
                            calling_format=calling_format)

        default_headers = getattr(settings, HEADERS, [])
        # Backwards compatibility for original format from django-storages
        if isinstance(default_headers, dict):
            default_headers = [('.*', default_headers)]
        if headers:
            default_headers.update(headers)
        self.headers = []
        for value in default_headers:
            self.headers.append((re.compile(value[0]), value[1]))

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
        date = timegm(parsedate(date))
        self.cache.save(name, size=size, mtime=date)

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
        headers = {}
        for pattern in self.headers:
            if pattern[0].match(name):
                headers = pattern[1].copy()
                break
        file_pos = content.tell()
        content.seek(0)
        content_length = len(content.read())
        content.seek(0)
        gz_cts = getattr(
            settings,
            'CUDDLYBUDDLY_STORAGE_S3_GZIP_CONTENT_TYPES',
            (
                'text/css',
                'application/javascript',
                'application/x-javascript'
            )
        )
        gz_content = None
        if content_length > 1024 and content_type in gz_cts:
            gz_content = StringIO()
            gzf = GzipFile(mode='wb', fileobj=gz_content)
            gzf.write(content.read())
            content.seek(0)
            gzf.close()
            gz_content.seek(0)
            gz_content_length = len(gz_content.read())
            gz_content.seek(0)
            if gz_content_length < content_length:
                content_length = gz_content_length
                headers.update({
                    'Content-Encoding': 'gzip'
                })
        headers.update({
            'Content-Type': content_type,
            'Content-Length': str(content_length)
        })
        # Httplib in <= 2.6 doesn't accept file like objects, and in >= 2.7 it
        # tries to join the content str object with the headers which results in
        # encoding problems.
        if sys.version_info[0] == 2 and sys.version_info[1] < 7:
            content_to_send = gz_content.read() if gz_content is not None else content.read()
        else:
            content_to_send = gz_content if gz_content is not None else content
        response = self.connection.put(self.bucket, name, content_to_send, headers)
        content.seek(file_pos)
        if response.http_response.status != 200:
            if placeholder:
                self.cache.remove(name)
            raise S3Error(response.message)
        if self.cache:
            date = response.http_response.getheader('Date')
            date = timegm(parsedate(date))
            self.cache.save(name, size=content_length, mtime=date)

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
        valid_responses = [200]
        if start_range is not None or end_range is not None:
            valid_responses.append(206)
        if response.http_response.status not in valid_responses:
            raise S3Error(response.message)
        headers = response.http_response.msg
        data = response.object.data

        if headers.get('Content-Encoding') == 'gzip':
            gzf = GzipFile(mode='rb', fileobj=StringIO(data))
            data = gzf.read()
            gzf.close()

        return data, headers.get('etag', None), headers.get('content-range', None)

    def _save(self, name, content):
        self._put_file(name, content)
        return name

    def delete(self, name):
        name = self._path(name)
        response = self.connection.delete(self.bucket, name)
        if response.http_response.status != 204:
            raise S3Error(response.message)
        if self.cache:
            self.cache.remove(name)

    def exists(self, name, force_check=False):
        if not name:
            return False
        name = self._path(name)
        if self.cache and not force_check:
            exists = self.cache.exists(name)
            if exists is not None:
                return exists
        response = self.connection._make_request('HEAD', self.bucket, name)
        exists = response.status == 200
        if self.cache and exists:
            self._store_in_cache(name, response)
        return exists

    def size(self, name, force_check=False):
        name = self._path(name)
        if self.cache and not force_check:
            size = self.cache.size(name)
            if size is not None:
                return size
        response = self.connection._make_request('HEAD', self.bucket, name)
        content_length = response.getheader('Content-Length')
        if self.cache:
            self._store_in_cache(name, response)
        return content_length and int(content_length) or 0

    def modified_time(self, name, force_check=False):
        name = self._path(name)
        if self.cache and not force_check:
            last_modified = self.cache.modified_time(name)
            if last_modified:
                return datetime.fromtimestamp(last_modified)
        response = self.connection._make_request('HEAD', self.bucket, name)
        if response.status == 404:
            raise S3Error("Cannot find the file specified: '%s'" % name)
        last_modified = timegm(parsedate(response.getheader('Last-Modified')))
        if self.cache:
            self._store_in_cache(name, response)
        return datetime.fromtimestamp(last_modified)

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
        return urljoin(url, iri_to_uri(name))

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
            self._storage._put_file(self.name, self.file)
            self._size = len(self.file.getvalue())
        self.file.close()

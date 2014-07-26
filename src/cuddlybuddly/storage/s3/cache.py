import hashlib
import os
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import force_bytes, force_text


class Cache(object):
    """
    A base cache class, providing some default behaviors that all other
    cache systems can inherit or override, as necessary.
    """

    def exists(self, name):
        """
        Returns True if a file referened by the given name already exists in the
        storage system, or False if the name is available for a new file.

        If the cache doesn't exist then return None.
        """
        raise NotImplementedError()

    def size(self, name):
        """
        Returns the total size, in bytes, of the file specified by name.

        If the cache doesn't exist then return None.
        """
        raise NotImplementedError()

    def modified_time(self, name):
        """
        Return the time of last modification of name. The return value is a
        number giving the number of seconds since the epoch.

        If the cache doesn't exist then return None.
        """
        raise NotImplementedError()

    def save(self, name, size, mtime):
        """
        Save the values to the cache.
        """
        raise NotImplementedError()

    def remove(self, name):
        """
        Remove the values from the cache.
        """
        raise NotImplementedError()


class FileSystemCache(Cache):
    def __init__(self, cache_dir=None):
        if cache_dir is None:
            cache_dir = getattr(settings, 'CUDDLYBUDDLY_STORAGE_S3_FILE_CACHE_DIR', None)
            if cache_dir is None:
                raise ImproperlyConfigured(
                    '%s requires CUDDLYBUDDLY_STORAGE_S3_FILE_CACHE_DIR to be set to a directory.' % type(self)
                )
        self.cache_dir = cache_dir

    def _path(self, name):
        name = force_text(name).encode('utf-8')
        return os.path.join(self.cache_dir, hashlib.md5(name).hexdigest())

    def exists(self, name):
        return None

    def size(self, name):
        try:
            file = open(self._path(name))
            size = int(file.readlines()[1])
            file.close()
        except:
            size = None
        return size

    def modified_time(self, name):
        try:
            file = open(self._path(name))
            mtime = float(file.readlines()[2])
            file.close()
        except:
            mtime = None
        return mtime

    def save(self, name, size, mtime):
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        file = open(self._path(name), 'wb')
        file.write(('%s\n%s\n%s' % (name, size, mtime)).encode('utf-8'))
        file.close()

    def remove(self, name):
        name = self._path(name)
        if os.path.exists(name):
            os.remove(name)

from cuddlybuddly.storage.s3.lib import CallingFormat
from cuddlybuddly.storage.s3.storage import S3Storage, S3StorageStatic


__all__ = ['CallingFormat', 'S3Storage', 'S3StorageStatic']


# Monkey patch form Media as I don't see a better way to do this, especially
# with custom admin javascript on CloudFront that needs to be HTTPS to run.
from django.conf import settings
from django.forms.widgets import Media
from cuddlybuddly.storage.s3.utils import CloudFrontURLs
old_absolute_path = Media.absolute_path
def absolute_path(self, path, prefix=None):
    if not isinstance(settings.STATIC_URL, CloudFrontURLs) or \
       path.startswith(('http://', 'https://', '/')) or \
       prefix is not None:
        return old_absolute_path(self, path, prefix)
    return settings.STATIC_URL.get_url(path)
Media.absolute_path = absolute_path

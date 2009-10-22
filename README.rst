===============================
django-cuddlybuddly-storage-s3
===============================

Updated Amazon S3 storage from django-storages.


Installation
============

1. Add ``cuddlybuddly.storage.s3`` to your ``INSTALLED_APPS``.
2. Set ``DEFAULT_STORAGE`` to ``cuddlybuddly.storage.s3.S3Storage`` (as a string, don't import it).
3. Set ``MEDIA_URL`` to your bucket URL , e.g. ``http://yourbucket.s3.amazonaws.com/``.
4. Enter your AWS credentials in the settings below.


Settings
========

``AWS_ACCESS_KEY_ID``
---------------------

Your Amazon Web Services access key, as a string.

``AWS_SECRET_ACCESS_KEY``
-------------------------

Your Amazon Web Services secret access key, as a string.

``AWS_STORAGE_BUCKET_NAME``
---------------------------

Your Amazon Web Services storage bucket name, as a string.

``AWS_CALLING_FORMAT``
----------------------

The way you'd like to call the Amazon Web Services API, for instance if you prefer subdomains::

    from cuddlybuddly.storage.s3 import CallingFormat
    AWS_CALLING_FORMAT = CallingFormat.SUBDOMAIN


``AWS_HEADERS``
---------------

Optional. If you'd like to set headers sent with each file of the storage::

    # see http://developer.yahoo.com/performance/rules.html#expires
    AWS_HEADERS = {
        'Expires': 'Thu, 15 Apr 2010 20:00:00 GMT',
        'Cache-Control': 'max-age=86400',
    }

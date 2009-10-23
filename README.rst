===============================
django-cuddlybuddly-storage-s3
===============================

Updated Amazon S3 storage from django-storages. Adds more fixes than I can remember, a metadata cache system and some extra utilities.


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


Cache
=====

Included is a cache system to store file metadata to speed up accessing file metadata such as size and the last modified time. It is disabled by edeafult.

``FileSystemCache``
-------------------

The only included cache system is ``FileSystemStorage`` that stores the cache on the local disk. To use it, add the following to your settings file::

    CUDDLYBUDDLY_STORAGE_S3_CACHE = 'cuddlybuddly.storage.s3.cache.FileSystemCache'
    CUDDLYBUDDLY_STORAGE_S3_FILE_CACHE_DIR  = '/location/to/store/cache'

Custom Cache
------------

To create your own cache system, inherit from ``cuddlybuddly.storage.s3.cache.Cache`` and implement the following methods:

* exists
* getmtime
* size
* store


Utilities
=========

create_signed_url(file, expires=60, secure=False)
-------------------------------------------------

Creates a signed URL to ``file`` that will expire in ``expires`` seconds. If ``secure`` is set to ``True`` an ``https`` link will be returned.

To import it::

    from cuddlybuddly.storage.s3.utils import create_signed_url

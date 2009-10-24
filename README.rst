===============================
django-cuddlybuddly-storage-s3
===============================

Updated Amazon S3 storage from django-storages. Adds more fixes than I can remember, a metadata cache system and some extra utilities.


Installation
============

1. Add ``cuddlybuddly.storage.s3`` to your ``INSTALLED_APPS``.
2. Set ``DEFAULT_FILE_STORAGE`` to ``cuddlybuddly.storage.s3.S3Storage`` (as a string, don't import it).
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


HTTPS
=====

Because when you use S3 your ``MEDIA_URL`` must be absolute (i.e. it starts with ``http``) it's more difficult to have URLs that match how the page was requested. The following things should help with that.

``cuddlybuddly.storage.s3.middleware.ThreadLocals``
----------------------------------------------------

This middleware will ensure that the URLs of files retrieved from the databse will have the same protocol as how the page was requested.

``cuddlybuddly.storage.s3.context_processors.media``
----------------------------------------------------

This context processor returns ``MEDIA_URL`` with the protocol matching how the page was requested.


Cache
=====

Included is a cache system to store file metadata to speed up accessing file metadata such as size and the last modified time. It is disabled by edeafult.

``FileSystemCache``
-------------------

The only included cache system is ``FileSystemCache`` that stores the cache on the local disk. To use it, add the following to your settings file::

    CUDDLYBUDDLY_STORAGE_S3_CACHE = 'cuddlybuddly.storage.s3.cache.FileSystemCache'
    CUDDLYBUDDLY_STORAGE_S3_FILE_CACHE_DIR  = '/location/to/store/cache'

Custom Cache
------------

To create your own cache system, inherit from ``cuddlybuddly.storage.s3.cache.Cache`` and implement the following methods:

* exists
* getmtime
* save
* size
* remove


Utilities
=========

``create_signed_url(file, expires=60, secure=False)``
-----------------------------------------------------

Creates a signed URL to ``file`` that will expire in ``expires`` seconds. If ``secure`` is set to ``True`` an ``https`` link will be returned.

To import it::

    from cuddlybuddly.storage.s3.utils import create_signed_url


``CloudFrontURLs(default, patterbs={}, https=None)``
--------------------------------------

Use this with the above context processor to return varying ``MEDIA_URLS`` depending on the path to improve page loading times. This only really works with files from the database.

To use it add something like the following to your settings file::

    from cuddlybuddly.storage.s3.utils import CloudFrontURLs
    MEDIA_URL = CloudFrontURLs('http://cdn1.example.com/', patterns={
        '^images/': 'http://cdn2.example.com/',
        '^banners/': 'http://cdn3.example.com/',
        '^gallery/': 'http://cdn4.example.com/'
        }, https='https://example.s3.amazonaws.com/')

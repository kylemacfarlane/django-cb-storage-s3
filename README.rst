===============================
django-cuddlybuddly-storage-s3
===============================

Updated Amazon S3 storage from django-storages. Adds more fixes than I can remember, a metadata cache system and some extra utilities for dealing with ``MEDIA_URL`` and ``HTTPS``, CloudFront and for creating signed URLs.


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

``AWS_HEADERS``
---------------

A list of regular expressions which if matched add the headers to the file being uploaded to S3. The patterns are matched from first to last::

    # see http://developer.yahoo.com/performance/rules.html#expires
    AWS_HEADERS = [
        ('^private/', {
            'x-amz-acl': 'private',
            'Expires': 'Thu, 15 Apr 2000 20:00:00 GMT',
            'Cache-Control': 'private, max-age=0'
        }),
        ('.*', {
            'x-amz-acl': 'public-read',
            'Expires': 'Sat, 30 Oct 2010 20:00:00 GMT',
            'Cache-Control': 'public, max-age=31556926'
        })
    ]

* ``x-amz-acl`` sets the ACL of the file on S3 and defaults to ``private``.
* ``Expires`` is for old HTTP/1.0 caches and must be a perfectly formatted RFC 1123 date to work properly. ``django.utils.http.http_date`` can help you here.
* ``Cache-Control`` is HTTP/1.1 and takes precedence if supported. ``max-age`` is the number of seconds into the future the response should be cached for.

``AWS_CALLING_FORMAT``
----------------------

Optional and defaults to ``SUBDOMAIN``. The way you'd like to call the Amazon Web Services API, for instance if you need to use the old path method::

    from cuddlybuddly.storage.s3 import CallingFormat
    AWS_CALLING_FORMAT = CallingFormat.PATH


``CUDDLYBUDDLY_STORAGE_S3_GZIP_CONTENT_TYPES``
----------------------------------------------

A list of content types that will be gzipped. Defaults to ``('text/css', 'application/javascript', 'application/x-javascript')``.


``CUDDLYBUDDLY_STORAGE_S3_SKIP_TESTS``
--------------------------------------

Set to a true value to skip the tests as they can be pretty slow.

``CUDDLYBUDDLY_STORAGE_S3_SYNC_EXCLUDE``
----------------------------------------

A list of regular expressions of files and folders to ignore when using the synchronize commands. Defaults to ``['\.svn$', '\.git$', '\.hg$', 'Thumbs\.db$', '\.DS_Store$']``.

``CUDDLYBUDDLY_STORAGE_S3_KEY_PAIR``
------------------------------------

A tuple of a key pair ID and the contents of the private key from the security credentials page of your AWS account. This is used for signing private CloudFront URLs. For example::

    settings.CUDDLYBUDDLY_STORAGE_S3_KEY_PAIR = ('PK12345EXAMPLE',
    """-----BEGIN RSA PRIVATE KEY-----
    ...key contents...
    -----END RSA PRIVATE KEY-----""")


HTTPS
=====

Because when you use S3 your ``MEDIA_URL`` must be absolute (i.e. it starts with ``http``) it's more difficult to have URLs that match how the page was requested. The following things should help with that.

``cuddlybuddly.storage.s3.middleware.ThreadLocals``
----------------------------------------------------

This middleware will ensure that the URLs of files retrieved from the database will have the same protocol as how the page was requested.

``cuddlybuddly.storage.s3.context_processors.media``
----------------------------------------------------

This context processor returns ``MEDIA_URL`` with the protocol matching how the page was requested.


Cache
=====

Included is a cache system to store file metadata to speed up accessing file metadata such as size and the last modified time. It is disabled by default.

``FileSystemCache``
-------------------

The only included cache system is ``FileSystemCache`` that stores the cache on the local disk. To use it, add the following to your settings file::

    CUDDLYBUDDLY_STORAGE_S3_CACHE = 'cuddlybuddly.storage.s3.cache.FileSystemCache'
    CUDDLYBUDDLY_STORAGE_S3_FILE_CACHE_DIR  = '/location/to/store/cache'

Custom Cache
------------

To create your own cache system, inherit from ``cuddlybuddly.storage.s3.cache.Cache`` and implement the following methods:

* exists
* modified_time
* save
* size
* remove


Utilities
=========

``create_signed_url(file, expires=60, secure=False, private_cloudfront=False, expires_at=None)``
------------------------------------------------------------------------------------------------

Creates a signed URL to ``file`` that will expire in ``expires`` seconds. If ``secure`` is set to ``True`` an ``https`` link will be returned.

The ``private_cloudfront`` argument will use they key pair setup with ``CUDDLYBUDDLY_STORAGE_S3_KEY_PAIR`` to create signed URLs for a private CloudFront distribution.

The ``expires_at`` argument will override ``expires`` and expire the URL at a specified UNIX timestamp. It was mostly just added for generating consistent URLs for testing.

To import it::

    from cuddlybuddly.storage.s3.utils import create_signed_url


``CloudFrontURLs(default, patterns={}, https=None)``
----------------------------------------------------

Use this with the context processor or storage backends to return varying ``MEDIA_URL`` or ``STATIC_URL`` depending on the path to improve page loading times.

To use it add something like the following to your settings file::

    from cuddlybuddly.storage.s3.utils import CloudFrontURLs
    MEDIA_URL = CloudFrontURLs('http://cdn1.example.com/', patterns={
        '^images/': 'http://cdn2.example.com/',
        '^banners/': 'http://cdn3.example.com/',
        '^css/': 'http://cdn4.example.com/'
        }, https='https://example.cloudfront.net/')

The ``https`` argument is a URL to bypass CloudFront's lack of HTTPS CNAME support.

``s3_media_url`` Template Tag
-----------------------------

This is for use with ``CloudFrontURLs`` and will return the appropriate URL if a match is found.

Usage::

    {% load s3_tags %}
    {% s3_media_url 'css/common.css' %}

For ``HTTPS``, the ``cuddlybuddly.storage.s3.middleware.ThreadLocals`` middleware must also be used.


``s3_static_url`` Template Tag
------------------------------

The same as ``s3_media_url`` but uses ``STATIC_URL`` instead.


``cuddlybuddly.storage.s3.S3StorageStatic`` Storage Backend
-----------------------------------------------------------

A version of the storage backend that uses ``STATIC_URL`` instead. For use with ``STATICFILES_STORAGE`` and the ``static`` template tag from ``contrib.staticfiles``.


Commands
========

``cb_s3_sync_media``
--------------------

Synchronizes a directory with your S3 bucket. It will skip files that are already up to date or newer in the bucket but will not remove old files as that has the potential to go very wrong. The headers specified in ``AWS_HEADERS`` will be applied.

It has the following options:

* ``--cache``, ``-c`` - Get the modified times of files from the cache (if available) instead of checking S3. This is faster but could be inaccurate.
* ``--dir``, ``-d`` - The directory to synchronize with your bucket, defaults to ``MEDIA_ROOT``.
* ``--exclude``, ``-e`` - A comma separated list of regular expressions to ignore files or folders. Defaults to ``CUDDLYBUDDLY_STORAGE_S3_SYNC_EXCLUDE``.
* ``--force``, ``-f`` - Uploads all files even if the version in the bucket is up to date.
* ``--prefix``, ``-p`` - A prefix to prepend to every file uploaded, i.e. a subfolder to place the files in.

``cb_s3_sync_static``
---------------------

Exactly the same as ``cb_s3_sync_media`` except that ``dir`` defeaults to ``STATIC_ROOT``.


A note on the tests
===================

The tests in ``tests/s3test.py`` are pretty much straight from Amazon but have a tendency to fail if you run them too often / too quickly. When they do this they sometimes leave behind files or buckets in your account that you will need to go and delete to make the tests pass again.

The signed URL tests will also fail if your computer's clock is too far off from Amazon's servers.

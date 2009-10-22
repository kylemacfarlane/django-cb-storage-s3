===============================
django-cuddlybuddly-storage-s3
===============================

Updated Amazon S3 storage from django-storages.


Installation
============

1. Add ``cuddlybuddly.storage.s3`` to your ``INSTALLED_APPS``.
2. Set ``DEFAULT_STORAGE`` to ``cuddlybuddly.storage.s3.S3Storage`` (as a string, don't import it).
3. Set ``MEDIA_ROOT`` to the path leading to your files within your bucket, but excluding the bucket name itself, e.g. ``media/``. You can leave it blank if you want to.
4. Set ``MEDIA_URL`` to your bucket URL plus your ``MEDIA_ROOT``, e.g. ``http://yourbucket.s3.amazonaws.com/media/``.
5. Enter your AWS credentials in the settings below.


Notes on ``MEDIA_ROOT``
=======================

Most S3 storage systems I've seen totally ignore the ``MEDIA_ROOT`` setting, but that results in accessing files behaving differently from the default ``FileSystemStorage`` and you can't have publicly accessible and private files in the same bucket (and none of these storages have any kind of multiple bucket support either).

I like to set ``MEDIA_ROOT`` to a relative path such as ``media`` because then it also works on the local disk. I can then store CSS and so on in a version controlled folder beside ``settings.py`` in my project folder and have things such as ``django-compress`` and the ``sync_media_s3`` command from ``django-command-extensions`` work correctly.


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

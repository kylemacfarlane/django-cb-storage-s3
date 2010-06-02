from django.conf import settings


if not getattr(settings, 'CUDDLYBUDDLY_STORAGE_S3_SKIP_TESTS', False):
    from cuddlybuddly.storage.s3.tests.s3test import TestAWSAuthConnection, TestQueryStringAuthGenerator
    from cuddlybuddly.storage.s3.tests.tests import *

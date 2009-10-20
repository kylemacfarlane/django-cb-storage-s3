import os
import sys


DEBUG = True
DATABASE_ENGINE = 'sqlite3'
if sys.platform[0:3] == 'win':
    TEMP = os.environ.get('TEMP', '')
else:
    TEMP = '/tmp'
DATABASE_NAME = os.path.join(TEMP, 's3.db')
INSTALLED_APPS = [
    'cuddlybuddly.storage.s3'
]
MEDIA_ROOT = '/media/'

DEFAULT_FILE_STORAGE = 'cuddlybuddly.storage.s3.S3Storage'
from cuddlybuddly.storage.s3 import CallingFormat
AWS_CALLING_FORMAT = CallingFormat.SUBDOMAIN

# Below should contain:
#
# MEDIA_URL = 'http://yourbucket.s3.amazonaws.com'
# AWS_ACCESS_KEY_ID = ''
# AWS_SECRET_ACCESS_KEY = ''
# AWS_STORAGE_BUCKET_NAME = ''
from cuddlybuddly.storage.s3.tests3credentials import *

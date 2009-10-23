from datetime import datetime, timedelta
import httplib
from time import mktime, sleep
from urlparse import urlparse
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import TestCase
from django.utils.encoding import force_unicode
from django.utils.http import urlquote_plus
from cuddlybuddly.storage.s3 import lib
from cuddlybuddly.storage.s3.tests.s3test import TestAWSAuthConnection, TestQueryStringAuthGenerator
from cuddlybuddly.storage.s3.utils import create_signed_url


MEDIA_URL = settings.MEDIA_URL
if not MEDIA_URL.endswith('/'):
    MEDIA_URL = MEDIA_URL+'/'


class S3StorageTests(TestCase):
    def run_test(self, filename):
        filename = default_storage.save(filename, ContentFile('Lorem ipsum dolor sit amet'))
        self.assert_(default_storage.exists(filename))

        self.assertEqual(default_storage.size(filename), 26)
        now = datetime.utcnow()
        delta = timedelta(minutes=5)
        mtime = default_storage.getmtime(filename)
        self.assert_(mtime > mktime((now - delta).timetuple()))
        self.assert_(mtime < mktime((now + delta).timetuple()))
        file = default_storage.open(filename)
        self.assertEqual(file.size, 26)
        fileurl = force_unicode(file).replace('\\', '/')
        fileurl = urlquote_plus(fileurl, '/')
        if fileurl.startswith('/'):
            fileurl = fileurl[1:]
        self.assertEqual(
            MEDIA_URL+fileurl,
            default_storage.url(filename)
        )
        file.close()

        default_storage.delete(filename)
        self.assert_(not default_storage.exists(filename))

    def test_absolute_path(self):
        self.run_test('/testsdir/file1.txt')

    def test_relative_path(self):
        self.run_test('testsdir/file2.txt')

    def test_unicode(self):
        self.run_test(u'testsdir/\u00E1\u00E9\u00ED\u00F3\u00FA.txt')

    def test_write_to_file(self):
        filename = 'file6.txt'
        default_storage.save(filename, ContentFile('Lorem ipsum dolor sit amet'))
        self.assert_(default_storage.exists(filename))

        file = default_storage.open(filename, 'w')
        self.assertEqual(file.size, 26)

        file.write('Lorem ipsum')
        file.close()
        self.assertEqual(file.size, 11)

        default_storage.delete(filename)
        self.assert_(not default_storage.exists(filename))

    def run_listdir_test(self, folder):
        content = ('testsdir/file3.txt', 'testsdir/file4.txt',
                 'testsdir/sub/file5.txt')
        for file in content:
            default_storage.save(file, ContentFile('Lorem ipsum dolor sit amet'))
            self.assert_(default_storage.exists(file))

        dirs, files = default_storage.listdir(folder)
        self.assertEqual(dirs, ['sub'])
        self.assertEqual(files, ['file3.txt', 'file4.txt'])
        if not folder.endswith('/'):
            folder = folder+'/'
        dirs, files = default_storage.listdir(folder+dirs[0])
        self.assertEqual(dirs, [])
        self.assertEqual(files, ['file5.txt'])

        for file in content:
            default_storage.delete(file)
            self.assert_(not default_storage.exists(file))

    def test_listdir_absolute_path(self):
        self.run_listdir_test('/testsdir')

    def test_listdir_relative_path(self):
        self.run_listdir_test('testsdir')

    def test_listdir_ending_slash(self):
        self.run_listdir_test('testsdir/')


class SignedURLTests(TestCase):
    def setUp(self):
        self.conn = lib.AWSAuthConnection(
            settings.AWS_ACCESS_KEY_ID,
            settings.AWS_SECRET_ACCESS_KEY
        )

    def get_url(self, url):
        url = urlparse(url)
        if url.scheme == 'https':
            conn = httplib.HTTPSConnection(url.netloc)
        else:
            conn = httplib.HTTPConnection(url.netloc)
        path = url.path
        if url.query:
            path = path+'?'+url.query
        conn.request('GET', path)
        return conn.getresponse()

    def run_test_signed_url(self, filename):
        response = self.conn.put(
            settings.AWS_STORAGE_BUCKET_NAME,
            filename,
            'Lorem ipsum dolor sit amet.',
            {'x-amz-acl': 'private'}
        )
        self.assertEquals(response.http_response.status, 200, 'put with a string argument')
        response = self.get_url(default_storage.url(filename))
        self.assertEqual(response.status, 403)

        signed_url = create_signed_url(filename, expires=5, secure=True)
        response = self.get_url(signed_url)
        self.assertEqual(response.status, 200)
        sleep(6)
        response = self.get_url(signed_url)
        self.assertEqual(response.status, 403)

        default_storage.delete(filename)

    def test_signed_url(self):
        self.run_test_signed_url('testprivatefile.txt')

    def test_signed_url_with_unicode(self):
        self.run_test_signed_url(u'testprivatefile\u00E1\u00E9\u00ED\u00F3\u00FA.txt')

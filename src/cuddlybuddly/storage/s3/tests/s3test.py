#!/usr/bin/env python

# This software code is made available "AS IS" without warranties of any
# kind.  You may copy, display, modify and redistribute the software
# code either by itself or as incorporated into your code; provided that
# you do not remove any proprietary notices.  Your use of this software
# code is at your own risk and you waive any claim against Amazon
# Digital Services, Inc. or its affiliates with respect to your use of
# this software code. (c) 2006-2007 Amazon Digital Services, Inc. or its
# affiliates.

# Incorporated Django settings.
#
# 409 error fix - you can't create and delete the same bucket on US and EU
# servers within a short time. Now appeds location to bucket name.
#
# (c) 2009 Kyle MacFarlane

import unittest
import httplib
from django.conf import settings
from cuddlybuddly.storage.s3 import lib as S3

AWS_ACCESS_KEY_ID = settings.AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY = settings.AWS_SECRET_ACCESS_KEY

# for subdomains (bucket.s3.amazonaws.com),
# the bucket name must be lowercase since DNS is case-insensitive
BUCKET_NAME = "%s-test-bucket" % AWS_ACCESS_KEY_ID.lower();


class TestAWSAuthConnection(unittest.TestCase):
    def setUp(self):
        self.conn = S3.AWSAuthConnection(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)

    # test all operations for both regular and vanity domains
    # regular: http://s3.amazonaws.com/bucket/key
    # subdomain: http://bucket.s3.amazonaws.com/key
    # testing pure vanity domains (http://<vanity domain>/key) is not covered here
    # but is possible with some additional setup (set the server in @conn to your vanity domain)

    def test_subdomain_default(self):
        self.run_tests(S3.CallingFormat.SUBDOMAIN, S3.Location.DEFAULT)

    def test_subdomain_eu(self):
        self.run_tests(S3.CallingFormat.SUBDOMAIN, S3.Location.EU)

    def test_path_default(self):
        self.run_tests(S3.CallingFormat.PATH, S3.Location.DEFAULT)


    def run_tests(self, calling_format, location):
        bucket_name = BUCKET_NAME+str(location).lower()
        self.conn.calling_format = calling_format

        response = self.conn.create_located_bucket(bucket_name, location)
        self.assertEquals(response.http_response.status, 200, 'create bucket')

        response = self.conn.list_bucket(bucket_name)
        self.assertEquals(response.http_response.status, 200, 'list bucket')
        self.assertEquals(len(response.entries), 0, 'bucket is empty')

        text = 'this is a test'
        key = 'example.txt'

        response = self.conn.put(bucket_name, key, text)
        self.assertEquals(response.http_response.status, 200, 'put with a string argument')

        response = \
            self.conn.put(
                    bucket_name,
                    key,
                    S3.S3Object(text, {'title': 'title'}),
                    {'Content-Type': 'text/plain'})

        self.assertEquals(response.http_response.status, 200, 'put with complex argument and headers')

        response = self.conn.get(bucket_name, key)
        self.assertEquals(response.http_response.status, 200, 'get object')
        self.assertEquals(response.object.data, text, 'got right data')
        self.assertEquals(response.object.metadata, { 'title': 'title' }, 'metadata is correct')
        self.assertEquals(int(response.http_response.getheader('Content-Length')), len(text), 'got content-length header')

        title_with_spaces = " \t  title with leading and trailing spaces     "
        response = \
            self.conn.put(
                    bucket_name,
                    key,
                    S3.S3Object(text, {'title': title_with_spaces}),
                    {'Content-Type': 'text/plain'})

        self.assertEquals(response.http_response.status, 200, 'put with headers with spaces')

        response = self.conn.get(bucket_name, key)
        self.assertEquals(response.http_response.status, 200, 'get object')
        self.assertEquals(
                response.object.metadata,
                { 'title': title_with_spaces.strip() },
                'metadata with spaces is correct')

        # delimited list tests
        inner_key = 'test/inner.txt'
        last_key = 'z-last-key.txt'
        response = self.conn.put(bucket_name, inner_key, text)
        self.assertEquals(response.http_response.status, 200, 'put inner key')

        response = self.conn.put(bucket_name, last_key, text)
        self.assertEquals(response.http_response.status, 200, 'put last key')

        response = self.do_delimited_list(bucket_name, False, {'delimiter': '/'}, 2, 1, 'root list')

        response = self.do_delimited_list(bucket_name, True, {'max-keys': 1, 'delimiter': '/'}, 1, 0, 'root list with max keys of 1', 'example.txt')

        response = self.do_delimited_list(bucket_name, True, {'max-keys': 2, 'delimiter': '/'}, 1, 1, 'root list with max keys of 2, page 1', 'test/')

        marker = response.next_marker

        response = self.do_delimited_list(bucket_name, False, {'marker': marker, 'max-keys': 2, 'delimiter': '/'}, 1, 0, 'root list with max keys of 2, page 2')

        response = self.do_delimited_list(bucket_name, False, {'prefix': 'test/', 'delimiter': '/'}, 1, 0, 'test/ list')

        response = self.conn.delete(bucket_name, inner_key)
        self.assertEquals(response.http_response.status, 204, 'delete %s' % inner_key)

        response = self.conn.delete(bucket_name, last_key)
        self.assertEquals(response.http_response.status, 204, 'delete %s' % last_key)


        weird_key = '&=//%# ++++'

        response = self.conn.put(bucket_name, weird_key, text)
        self.assertEquals(response.http_response.status, 200, 'put weird key')

        response = self.conn.get(bucket_name, weird_key)
        self.assertEquals(response.http_response.status, 200, 'get weird key')

        response = self.conn.get_acl(bucket_name, key)
        self.assertEquals(response.http_response.status, 200, 'get acl')

        acl = response.object.data

        response = self.conn.put_acl(bucket_name, key, acl)
        self.assertEquals(response.http_response.status, 200, 'put acl')

        response = self.conn.get_bucket_acl(bucket_name)
        self.assertEquals(response.http_response.status, 200, 'get bucket acl')

        bucket_acl = response.object.data

        response = self.conn.put_bucket_acl(bucket_name, bucket_acl)
        self.assertEquals(response.http_response.status, 200, 'put bucket acl')

        response = self.conn.get_bucket_acl(bucket_name)
        self.assertEquals(response.http_response.status, 200, 'get bucket logging')

        bucket_logging = response.object.data

        response = self.conn.put_bucket_acl(bucket_name, bucket_logging)
        self.assertEquals(response.http_response.status, 200, 'put bucket logging')

        response = self.conn.list_bucket(bucket_name)
        self.assertEquals(response.http_response.status, 200, 'list bucket')
        entries = response.entries
        self.assertEquals(len(entries), 2, 'got back right number of keys')
        # depends on weird_key < key
        self.assertEquals(entries[0].key, weird_key, 'first key is right')
        self.assertEquals(entries[1].key, key, 'second key is right')

        response = self.conn.list_bucket(bucket_name, {'max-keys': 1})
        self.assertEquals(response.http_response.status, 200, 'list bucket with args')
        self.assertEquals(len(response.entries), 1, 'got back right number of keys')

        for entry in entries:
            response = self.conn.delete(bucket_name, entry.key)
            self.assertEquals(response.http_response.status, 204, 'delete %s' % entry.key)

        response = self.conn.list_all_my_buckets()
        self.assertEquals(response.http_response.status, 200, 'list all my buckets')
        buckets = response.entries

        response = self.conn.delete_bucket(bucket_name)
        self.assertEquals(response.http_response.status, 204, 'delete bucket')

        response = self.conn.list_all_my_buckets()
        self.assertEquals(response.http_response.status, 200, 'list all my buckets again')

        self.assertEquals(len(response.entries), len(buckets) - 1, 'bucket count is correct')

    def verify_list_bucket_response(self, response, bucket, is_truncated, parameters, next_marker=''):
        prefix = ''
        marker = ''

        if parameters.has_key('prefix'):
            prefix = parameters['prefix']
        if parameters.has_key('marker'):
            marker = parameters['marker']

        self.assertEquals(bucket, response.name, 'bucket name should match')
        self.assertEquals(prefix, response.prefix, 'prefix should match')
        self.assertEquals(marker, response.marker, 'marker should match')
        if parameters.has_key('max-keys'):
            self.assertEquals(parameters['max-keys'], response.max_keys, 'max-keys should match')
        self.assertEquals(parameters['delimiter'], response.delimiter, 'delimiter should match')
        self.assertEquals(is_truncated, response.is_truncated, 'is_truncated should match')
        self.assertEquals(next_marker, response.next_marker, 'next_marker should match')

    def do_delimited_list(self, bucket_name, is_truncated, parameters, regular_expected, common_expected, test_name, next_marker=''):
        response = self.conn.list_bucket(bucket_name, parameters)
        self.assertEquals(response.http_response.status, 200, test_name)
        self.assertEquals(regular_expected, len(response.entries), 'right number of regular entries')
        self.assertEquals(common_expected, len(response.common_prefixes), 'right number of common prefixes')

        self.verify_list_bucket_response(response, bucket_name, is_truncated, parameters, next_marker)

        return response

class TestQueryStringAuthGenerator(unittest.TestCase):
    def setUp(self):
        self.generator = S3.QueryStringAuthGenerator(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
        if (self.generator.is_secure == True):
            self.connection = httplib.HTTPSConnection(self.generator.server_name)
        else:
            self.connection = httplib.HTTPConnection(self.generator.server_name)

    def check_url(self, url, method, status, message, data=''):
        if (method == 'PUT'):
            headers = { 'Content-Length': str(len(data)) }
            self.connection.request(method, url, data, headers)
        else:
            self.connection.request(method, url)

        response = self.connection.getresponse()
        self.assertEquals(response.status, status, message)

        return response.read()

    # test all operations for both regular and vanity domains
    # regular: http://s3.amazonaws.com/bucket/key
    # subdomain: http://bucket.s3.amazonaws.com/key
    # testing pure vanity domains (http://<vanity domain>/key) is not covered here
    # but is possible with some additional setup (set the server in @conn to your vanity domain)

    def test_subdomain(self):
        self.run_tests(S3.CallingFormat.SUBDOMAIN)

    def test_path(self):
        self.run_tests(S3.CallingFormat.PATH)

    def run_tests(self, calling_format):
        self.generator.calling_format = calling_format

        key = 'test'

        self.check_url(self.generator.create_bucket(BUCKET_NAME), 'PUT', 200, 'create_bucket')
        self.check_url(self.generator.put(BUCKET_NAME, key, ''), 'PUT', 200, 'put object', 'test data')
        self.check_url(self.generator.get(BUCKET_NAME, key), 'GET', 200, 'get object')
        self.check_url(self.generator.list_bucket(BUCKET_NAME), 'GET', 200, 'list bucket')
        self.check_url(self.generator.list_all_my_buckets(), 'GET', 200, 'list all my buckets')
        acl = self.check_url(self.generator.get_acl(BUCKET_NAME, key), 'GET', 200, 'get acl')
        self.check_url(self.generator.put_acl(BUCKET_NAME, key, acl), 'PUT', 200, 'put acl', acl)
        bucket_acl = self.check_url(self.generator.get_bucket_acl(BUCKET_NAME), 'GET', 200, 'get bucket acl')
        self.check_url(self.generator.put_bucket_acl(BUCKET_NAME, bucket_acl), 'PUT', 200, 'put bucket acl', bucket_acl)
        bucket_logging = self.check_url(self.generator.get_bucket_logging(BUCKET_NAME), 'GET', 200, 'get bucket logging')
        self.check_url(self.generator.put_bucket_logging(BUCKET_NAME, bucket_logging), 'PUT', 200, 'put bucket logging', bucket_logging)
        self.check_url(self.generator.delete(BUCKET_NAME, key), 'DELETE', 204, 'delete object')
        self.check_url(self.generator.delete_bucket(BUCKET_NAME), 'DELETE', 204, 'delete bucket')


if __name__ == '__main__':
    unittest.main()



from datetime import datetime
from optparse import make_option
import os
import re
import sys
from django.conf import settings
from django.core.management.base import BaseCommand
from cuddlybuddly.storage.s3.storage import S3Storage


output_length = 0
def output(text, options, min_verbosity=1, rtrn=False, nl=False):
    if int(options['verbosity']) >= min_verbosity:
        global output_length
        if rtrn:
            if len(text) < output_length:
                text = text + ' ' * (output_length - len(text) - 1)
            text = '\r' + text
            output_length = 0
        output_length += len(text)
        if nl:
            output_length = 0
            text = text + '\n'
        sys.stdout.write(text)
        sys.stdout.flush()


def walk(dir, options):
    to_sync = []
    for root, dirs, files in os.walk(dir):
        for dir in dirs:
            for pattern in options['exclude']:
                if pattern.search(os.path.join(root, dir)):
                    dirs.remove(dir)
        for file in files:
            file = os.path.join(root, file)
            exclude = False
            for pattern in options['exclude']:
                if pattern.search(file):
                    exclude = True
                    break
            if exclude:
                continue
            # Because the followlinks parameter is only in >= 2.6 we have to
            # follow symlinks ourselves.
            if os.path.isdir(file) and os.path.islink(file):
                to_sync = to_sync + walk(file)
            else:
                to_sync.append(file)
    return to_sync


class Command(BaseCommand):
    help = 'Sync folder with your S3 bucket'
    option_list = BaseCommand.option_list + (
        make_option('-f', '--force',
            action='store_true',
            dest='force',
            default=False,
            help='Upload all files even if the version on S3 is up to date'),
        make_option('-d', '--dir',
            action='store',
            dest='dir',
            type='string',
            default=None,
            help='Directory to sync to S3'),
        make_option('-e', '--exclude',
            action='store',
            dest='exclude',
            type='string',
            default=None,
            help='A comma separated list of regular expressions of files and folders to skip'),
        make_option('-p', '--prefix',
            action='store',
            dest='prefix',
            type='string',
            default='',
            help='Prefix to prepend to uploaded files'),
    )

    def handle(self, *args, **options):
        if options['dir'] is None:
            options['dir'] = settings.MEDIA_ROOT
        if options['exclude'] is None:
            options['exclude'] = getattr(
                settings,
                'CUDDLYBUDDLY_STORAGE_S3_SYNC_EXCLUDE',
                ['\.svn$', '\.git$', '\.hg$', 'Thumbs\.db$', '\.DS_Store$']
            )
        else:
            options['exclude'] = options['exclude'].split(',')
        exclude = []
        for pattern in options['exclude']:
            exclude.append(re.compile(pattern))
        options['exclude'] = exclude

        files = walk(options['dir'], options)
        skipped = uploaded = 0
        output(
            'Uploaded: %s, Skipped: %s, Total: %s/%s' % (0, 0, 0, len(files)),
            options
        )
        storage = S3Storage()
        for file in files:
            s3name = os.path.join(
                options['prefix'],
                os.path.relpath(file, options['dir'])
            )
            if options['force'] or \
               storage.modified_time(s3name) < \
               datetime.fromtimestamp(os.path.getmtime(file)):
                if storage.exists(s3name):
                    storage.delete(s3name)
                fh = open(file, 'rb')
                output(' Uploading %s...' % s3name, options)
                storage.save(s3name, fh)
                output('Uploaded %s' % s3name, options, rtrn=True, nl=True)
                fh.close()
                uploaded += 1
            else:
                output(
                    'Skipped %s because it hasn\'t been modified' % s3name,
                    options,
                    min_verbosity=2,
                    rtrn=True,
                    nl=True
                )
                skipped += 1
            output(
                'Uploaded: %s, Skipped: %s, Total: %s/%s'
                    % (uploaded, skipped, uploaded + skipped, len(files)),
                options,
                rtrn=True
            )
        output('', options, nl=True)

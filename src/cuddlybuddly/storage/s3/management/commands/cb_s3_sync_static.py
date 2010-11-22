from django.conf import settings
from cuddlybuddly.storage.s3.management.commands.cb_s3_sync_media import \
    Command as BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        if options['dir'] is None:
            options['dir'] = getattr(settings, 'STATIC_ROOT', None)
        return super(Command, self).handle(*args, **options)

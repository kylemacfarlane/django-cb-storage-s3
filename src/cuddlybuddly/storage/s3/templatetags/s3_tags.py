from urlparse import urljoin
from django import template
from django.conf import settings
from django.utils.encoding import iri_to_uri
from cuddlybuddly.storage.s3.middleware import request_is_secure


register = template.Library()


class S3MediaURLNode(template.Node):
    def __init__(self, path, as_var=None):
        self.path = template.Variable(path)
        self.as_var = as_var

    def render(self, context):
        path = self.path.resolve(context)
        base_url = settings.MEDIA_URL
        if request_is_secure():
            if hasattr(base_url, 'https'):
                url = base_url.https()
            else:
                if hasattr(base_url, 'match'):
                    url = base_url.match(path)
                else:
                    url = base_url
                url = url.replace('http://', 'https://')
        else:
            if hasattr(base_url, 'match'):
                url = base_url.match(path)
            else:
                url = base_url
            url = url.replace('https://', 'http://')
        return urljoin(url, iri_to_uri(path))


def do_s3_media_url(parser, token):
    """
    This is for use with ``CloudFrontURLs`` and will return the appropriate url
    if a match is found.

    Usage::

        {% s3_media_url path %}


    For ``HTTPS``, the ``cuddlybuddly.storage.s3.middleware.ThreadLocals``
    middleware must also be used.
    """

    split_token = token.split_contents()
    vars = []
    as_var = False
    for k, v in enumerate(split_token[1:]):
        if v == 'as':
            try:
                while len(vars) < 1:
                    vars.append(None)
                vars.append(split_token[k+2])
                as_var = True
            except IndexError:
                raise template.TemplateSyntaxError, \
                      "%r tag requires a variable name to attach to" \
                      % split_token[0]
            break
        else:
            vars.append(v)

    if (not as_var and len(vars) not in (1,)) \
       or (as_var and len(vars) not in (2,)):
        raise template.TemplateSyntaxError, \
              "%r tag requires a path or url" \
              % token.contents.split()[0]

    return S3MediaURLNode(*vars)


do_s3_media_url = register.tag('s3_media_url', do_s3_media_url)

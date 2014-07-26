from django import template
from django.conf import settings
from cuddlybuddly.storage.s3.utils import CloudFrontURLs


register = template.Library()


class S3MediaURLNode(template.Node):
    def __init__(self, static, path, as_var=None):
        self.static = static
        self.path = template.Variable(path)
        self.as_var = as_var

    def render(self, context):
        path = self.path.resolve(context)
        if self.static:
            base_url = settings.STATIC_URL
        else:
            base_url = settings.MEDIA_URL
        if not isinstance(base_url, CloudFrontURLs):
            base_url = CloudFrontURLs(base_url)
        url = base_url.get_url(path)

        if self.as_var:
            context[self.as_var] = url
            return ''
        else:
            return url


def do_s3_media_url(parser, token, static=False):
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
                raise template.TemplateSyntaxError(
                      "%r tag requires a variable name to attach to" \
                      % split_token[0]
                )
            break
        else:
            vars.append(v)

    if (not as_var and len(vars) not in (1,)) \
       or (as_var and len(vars) not in (2,)):
        raise template.TemplateSyntaxError(
              "%r tag requires a path or url" \
              % token.contents.split()[0]
        )

    return S3MediaURLNode(static, *vars)


do_s3_media_url = register.tag('s3_media_url', do_s3_media_url)


def do_s3_static_url(parser, token):
    """
    This is the same as ``s3_media_url`` but defaults to ``STATIC_URL`` instead.
    """
    return do_s3_media_url(parser, token, static=True)


do_s3_static_url = register.tag('s3_static_url', do_s3_static_url)

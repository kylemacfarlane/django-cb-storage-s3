import os
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = 'django-cuddlybuddly-storage-s3',
    version = '1.2.4',
    license = 'BSD',
    description = 'Updated Amazon S3 storage from django-storages.',
    long_description = read('README.rst'),
    author = 'Kyle MacFarlane',
    author_email = 'kyle@deletethetrees.com',

    package_dir = {'': 'src'},
    packages = find_packages('src'),
    namespace_packages = ['cuddlybuddly'],
    include_package_data = True,
    zip_safe = False,

    install_requires = ['setuptools'],

    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP'
    ],
)

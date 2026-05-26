from .settings import *
import sys
from copy import copy


if sys.version_info >= (3, 14):
    from django.template.context import BaseContext, Context

    def _copy_base_context(self):
        duplicate = self.__class__.__new__(self.__class__)
        duplicate.__dict__.update(self.__dict__)
        duplicate.dicts = self.dicts[:]
        return duplicate

    def _copy_context(self):
        duplicate = _copy_base_context(self)
        duplicate.render_context = copy(self.render_context)
        return duplicate

    BaseContext.__copy__ = _copy_base_context
    Context.__copy__ = _copy_context


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'test_db.sqlite3',
    }
}

STATICFILES_DIRS = []

ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']

LEGAJO_CLOUDINARY = {
    'cloud_name': '',
    'api_key': '',
    'api_secret': '',
    'folder': 'legajo/libros',
}

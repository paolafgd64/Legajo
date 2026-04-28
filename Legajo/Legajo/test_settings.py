from .settings import *


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'test_db.sqlite3',
    }
}

STATICFILES_DIRS = []

ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']

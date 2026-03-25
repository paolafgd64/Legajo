from django.contrib.auth.password_validation import UserAttributeSimilarityValidator


class UserAttributeSimilarityWithoutEmailValidator(UserAttributeSimilarityValidator):
    user_attributes = ('username', 'first_name', 'last_name')

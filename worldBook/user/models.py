from django.contrib.auth.models import AbstractUser
from django.db import models  # Add this import


class User(AbstractUser):
    email = models.EmailField(max_length=100, unique=True)

    def __str__(self):
        return self.username

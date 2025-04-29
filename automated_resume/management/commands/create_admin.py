from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from ...models import AdminData


class Command(BaseCommand):
    help = 'Create a new admin user'

    def handle(self, *args, **kwargs):
        email = input('Enter admin email: ')
        password = make_password(input('Enter admin password: '))

        if AdminData.objects.filter(email=email).exists():
            self.stdout.write(self.style.ERROR('Admin with this email already exists'))
        else:
            AdminData.objects.create(email=email, password=password)
            self.stdout.write(self.style.SUCCESS('Successfully created new admin'))

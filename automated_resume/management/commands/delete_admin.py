from django.core.management.base import BaseCommand
from ...models import AdminData


class Command(BaseCommand):
    help = 'Delete an admin user'

    def handle(self, *args, **kwargs):
        email = input('Enter admin email to delete: ')

        try:
            admin = AdminData.objects.get(email=email)
            admin.delete()
            self.stdout.write(self.style.SUCCESS(f'Successfully deleted admin with email: {email}'))
        except AdminData.DoesNotExist:
            self.stdout.write(self.style.ERROR('Admin with this email does not exist'))
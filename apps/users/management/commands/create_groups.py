from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

class Command(BaseCommand):
    help = 'Create user groups with specific permissions'

    def handle(self, *args, **options):
        # Define the groups and their associated permissions
        groups_permissions = {
            'Customers': [],
            'Staff': [],
            'Administrators': [],
        }

        # Loop through each group
        for group_name, permission_codenames in groups_permissions.items():
            # Create or get the group
            group, created = Group.objects.get_or_create(name=group_name)
            self.stdout.write(f"Group '{group_name}' {'created' if created else 'already exists'}.")

            # Get the content type for the model
            # content_type = ContentType.objects.get_for_model(ServiceTicket)

            # Get the permissions by codename
            # permissions = Permission.objects.filter(
            #     content_type=content_type,
            #     codename__in=permission_codenames
            # )

            # Assign the permissions to the group
            # group.permissions.set(permissions)
            # self.stdout.write(f"Assigned {permissions.count()} permissions to '{group_name}'.")   
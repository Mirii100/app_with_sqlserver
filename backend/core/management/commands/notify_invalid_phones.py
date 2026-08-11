from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from notifications.models import Notification

class Command(BaseCommand):
    help = 'Notifies users with invalid phone number length'

    def handle(self, *args, **options):
        User = get_user_model()
        users_to_notify = User.objects.filter(phone_number__isnull=False).exclude(phone_number='')
        
        count = 0
        for user in users_to_notify:
            if len(user.phone_number) < 10:
                Notification.objects.create(
                    user=user,
                    title='Action Required: Update Phone Number',
                    message='Your registered phone number is incomplete. Please update it in your profile settings to ensure continued service.',
                    type='general'
                )
                count += 1
                self.stdout.write(self.style.SUCCESS(f'Notified user: {user.username}'))
        
        self.stdout.write(self.style.SUCCESS(f'Successfully notified {count} users.'))

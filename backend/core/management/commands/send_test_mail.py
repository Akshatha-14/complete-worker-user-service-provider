from django.core.management.base import BaseCommand
from django.core.mail import send_mail

class Command(BaseCommand):
    help = 'Send a test email'

    def handle(self, *args, **kwargs):
        try:
            send_mail(
                'Test Email from Django',
                'This is a test email to verify SMTP configuration.',
                'kb993726@gmail.com',
                ['leelavathishetty92@gmail.com'],  # Replace with your email for testing
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS('Test email sent successfully'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to send test email: {e}'))

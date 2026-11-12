from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Teste l'envoi SMTP (IONOS en prod, Gmail en local)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--to",
            default=getattr(settings, "CONTACT_EMAIL", settings.DEFAULT_FROM_EMAIL),
            help="Destinataire du mail de test (défaut: CONTACT_EMAIL)",
        )

    def handle(self, *args, **options):
        destinataire = options["to"]

        self.stdout.write(f"EMAIL_HOST        = {settings.EMAIL_HOST}")
        self.stdout.write(f"EMAIL_HOST_USER   = {settings.EMAIL_HOST_USER}")
        self.stdout.write(f"DEFAULT_FROM      = {settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write(f"CONTACT_EMAIL     = {getattr(settings, 'CONTACT_EMAIL', '-')}")
        self.stdout.write(f"Destinataire test = {destinataire}")
        self.stdout.write(f"DEBUG             = {settings.DEBUG}")

        if not settings.EMAIL_HOST_PASSWORD:
            self.stderr.write(
                self.style.ERROR(
                    "EMAIL_HOST_PASSWORD vide. "
                    "Ajoute le mot de passe IONOS de noreply@fag-nrw.de "
                    "dans settings.py (EMAIL_HOST_PASSWORD) ou en variable d'environnement."
                )
            )
            return

        try:
            send_mail(
                subject="[FAG NRW] Test email",
                message=(
                    "Ceci est un email de test depuis l'application FAG NRW.\n"
                    f"Envoyé via {settings.EMAIL_HOST} / {settings.EMAIL_HOST_USER}."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[destinataire],
                fail_silently=False,
            )
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"Échec envoi : {exc}"))
            return

        self.stdout.write(self.style.SUCCESS(f"Email envoyé à {destinataire}"))

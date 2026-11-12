from django.core.management.base import BaseCommand

from gestion.cron import generer_cotisations_auto


class Command(BaseCommand):
    help = "Crée les cotisations du mois pour les associations affiliées actives."

    def handle(self, *args, **options):
        created = generer_cotisations_auto()
        self.stdout.write(self.style.SUCCESS(f"{created} cotisation(s) créée(s)."))

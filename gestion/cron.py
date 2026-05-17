from django.utils import timezone
from .models import AffiliationAssociation, CotisationAssociationMensuelle

def generer_cotisations_auto():
    today = timezone.now()

    affiliations = AffiliationAssociation.objects.filter(statut='active')

    for aff in affiliations:
        exists = CotisationAssociationMensuelle.objects.filter(
            affiliation=aff,
            annee=today.year,
            mois=today.month
        ).exists()

        if not exists:
            CotisationAssociationMensuelle.objects.create(
                affiliation=aff,
                annee=today.year,
                mois=today.month,
                montant_attendu=aff.montant_mensuel
            )
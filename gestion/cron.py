from django.db import transaction
from django.utils import timezone

from .emails import envoyer_notification_generation_cotisation
from .models import (
    AffiliationAssociation,
    CotisationAssociationMensuelle,
    PaiementAssociation,
)


def _appliquer_avances(cotisation, association):
    """Consomme les avances disponibles pour une cotisation nouvellement créée."""
    avances = (
        PaiementAssociation.objects
        .select_for_update()
        .filter(association=association, montant_avance__gt=0)
        .order_by("date_paiement", "created_at")
    )

    reste_a_payer = cotisation.montant_attendu - cotisation.montant_paye
    auto_paid = False
    partial_paid = False

    for paiement in avances:
        if reste_a_payer <= 0:
            break

        montant_utilise = min(paiement.montant_avance, reste_a_payer)

        cotisation.montant_paye += montant_utilise
        cotisation.date_paiement = paiement.date_paiement
        cotisation.mode_paiement = paiement.mode_paiement
        cotisation.date_modification_paiement = timezone.now()

        paiement.montant_avance -= montant_utilise
        paiement.montant_affecte += montant_utilise
        paiement.save(update_fields=["montant_avance", "montant_affecte"])

        reste_a_payer -= montant_utilise

    if cotisation.montant_paye >= cotisation.montant_attendu:
        cotisation.statut = "paye"
        auto_paid = True
    elif cotisation.montant_paye > 0:
        cotisation.statut = "partiel"
        partial_paid = True
    else:
        cotisation.statut = "en_attente"

    cotisation.save()
    return auto_paid, partial_paid


def generer_cotisations_auto():
    today = timezone.now()
    created = 0
    cotisations_creees = []

    affiliations = AffiliationAssociation.objects.filter(
        statut="active"
    ).select_related("association", "association__entite")

    for aff in affiliations:
        with transaction.atomic():
            cotisation, was_created = CotisationAssociationMensuelle.objects.get_or_create(
                affiliation=aff,
                annee=today.year,
                mois=today.month,
                defaults={
                    "montant_attendu": aff.montant_mensuel,
                    "montant_paye": 0,
                    "statut": "en_attente",
                },
            )

            if not was_created:
                continue

            _appliquer_avances(cotisation, aff.association)
            cotisations_creees.append(cotisation.pk)
            created += 1

    for cotisation in CotisationAssociationMensuelle.objects.filter(
        pk__in=cotisations_creees
    ).select_related(
        "affiliation__association__entite",
        "affiliation__federation",
    ):
        envoyer_notification_generation_cotisation(cotisation)

    return created

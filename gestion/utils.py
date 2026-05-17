from .models import Entite, UserEntiteRole,Personne
from .permissions import ROLE_PERMISSIONS
from django.utils import timezone # type: ignore
from collections import defaultdict
from django.db.models import Sum # type: ignore

from .models import (
    Association,
    CotisationAssociationMensuelle,
    ContributionDecesAssociation,
    PaiementAssociation,
)




def get_user_entites(user):
    if user.is_superuser:
        return Entite.objects.all()
    return Entite.objects.filter(userentiterole__user=user).distinct()


def get_user_role_names(user, entite):
    if user.is_superuser:
        return []
    return list(
        UserEntiteRole.objects.filter(user=user, entite=entite)
        .values_list("role__nom", flat=True)
    )


def user_has_role(user, entite, roles):
    if user.is_superuser:
        return True
    return UserEntiteRole.objects.filter(
        user=user,
        entite=entite,
        role__nom__in=roles,
    ).exists()


def require_role(user, entite, roles):
    return user_has_role(user, entite, roles)


def user_has_permission(user, entite, permission):
    if user.is_superuser:
        return True

    role_names = get_user_role_names(user, entite)
    for role_name in role_names:
        perms = ROLE_PERMISSIONS.get(role_name, set())
        if permission in perms:
            return True
    return False

def notifier_users(users, message, type_notification, lien=None):
    from .models import Notification

    notifications = [
        Notification(
            destinataire=user,
            message=message,
            type_notification=type_notification,
            lien=lien,
        )
        for user in users
    ]

    if notifications:
        Notification.objects.bulk_create(notifications)


def generer_numero_personne(federation):
    year = timezone.now().year
    prefix = federation.abreviation or federation.nom[:3].upper()
    base = f"{prefix}-P-{year}"

    last = Personne.objects.filter(
        numero__startswith=base
    ).order_by("-numero").first()

    if last:
        last_number = int(last.numero.split("-")[-1])
        new_number = last_number + 1
    else:
        new_number = 1

    return f"{base}-{str(new_number).zfill(4)}"


def get_resume_financier_associations(federation):
    qs = CotisationAssociationMensuelle.objects.filter(
        affiliation__federation=federation
    )

    contributions_deces = ContributionDecesAssociation.objects.filter(
        dossier__affiliation__federation=federation
    )

    paiements_avance = PaiementAssociation.objects.filter(
        association__federation=federation
    )

    resume = defaultdict(lambda: {
        "code": "",
        "association": "",
        "mensuel_attendu": 0,
        "mensuel_paye": 0,
        "deces_attendu": 0,
        "deces_paye": 0,
        "total_attendu": 0,
        "total_paye": 0,
        "reste": 0,
        "avance": 0,
        "situation": "",
    })

    cotisations_resume = qs.values(
        "affiliation__association_id",
        "affiliation__association__entite__nom",
        "affiliation__association__code_paiement",
    ).annotate(
        total_attendu=Sum("montant_attendu"),
        total_paye=Sum("montant_paye"),
    )

    for item in cotisations_resume:
        association_id = item["affiliation__association_id"]
        resume[association_id]["code"] = item["affiliation__association__code_paiement"]
        resume[association_id]["association"] = item["affiliation__association__entite__nom"]
        resume[association_id]["mensuel_attendu"] = item["total_attendu"] or 0
        resume[association_id]["mensuel_paye"] = item["total_paye"] or 0

    deces_resume = contributions_deces.values(
        "association_id",
        "association__entite__nom",
        "association__code_paiement",
    ).annotate(
        total_attendu=Sum("montant_attendu"),
        total_paye=Sum("montant_paye"),
    )

    for item in deces_resume:
        association_id = item["association_id"]
        resume[association_id]["code"] = item["association__code_paiement"]
        resume[association_id]["association"] = item["association__entite__nom"]
        resume[association_id]["deces_attendu"] = item["total_attendu"] or 0
        resume[association_id]["deces_paye"] = item["total_paye"] or 0

    avances_resume = paiements_avance.values(
        "association_id",
        "association__entite__nom",
        "association__code_paiement",
    ).annotate(
        total_avance=Sum("montant_avance")
    )

    for item in avances_resume:
        association_id = item["association_id"]
        resume[association_id]["code"] = item["association__code_paiement"]
        resume[association_id]["association"] = item["association__entite__nom"]
        resume[association_id]["avance"] = item["total_avance"] or 0

    resume_associations = []

    for item in resume.values():
        item["total_attendu"] = item["mensuel_attendu"] + item["deces_attendu"]
        item["total_paye"] = item["mensuel_paye"] + item["deces_paye"]

        avance_existante = item.get("avance", 0)

        solde_net = item["total_attendu"] - item["total_paye"] - avance_existante

        if solde_net > 0:
            item["reste"] = solde_net
            item["avance"] = 0
            item["situation"] = "En retard"
        else:
            item["reste"] = 0
            item["avance"] = abs(solde_net)

            if item["avance"] > 0:
                item["situation"] = "En avance"
            else:
                item["situation"] = "À jour"

        resume_associations.append(item)
        
    return sorted(resume_associations, key=lambda x: x["association"])
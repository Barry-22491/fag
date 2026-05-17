from datetime import date, timedelta

from .models import (
    CotisationAssociationMensuelle,
    DossierRapatriement,
    ActiviteCulturelle,
    Entite,
    Association,
)
from .utils import get_user_entites, user_has_permission


def federation_courante(request):
    federation = None

    if request.user.is_authenticated:
        entites = get_user_entites(request.user)

        federation = entites.filter(type="federation").first()

        if not federation:
            association_entite = entites.filter(type="association").first()

            if association_entite:
                association = (
                    Association.objects
                    .select_related("federation")
                    .filter(entite=association_entite)
                    .first()
                )

                if association:
                    federation = association.federation

    if not federation:
        federation = Entite.objects.filter(type="federation").first()

    return {
        "federation_courante": federation
    }


def permissions_context(request):
    if not request.user.is_authenticated:
        return {}

    entites = get_user_entites(request.user)
    federation = entites.filter(type="federation").first()
    associations = entites.filter(type="association")

    return {
        "is_federation_user": bool(federation),
        "is_association_user": associations.exists(),

        "can_view_dashboard": bool(
            federation and user_has_permission(request.user, federation, "dashboard_view")
        ) or associations.exists(),

        "can_view_associations": bool(
            federation and user_has_permission(request.user, federation, "associations_view")
        ),

        "can_view_personnes": bool(
            (federation and user_has_permission(request.user, federation, "membres_view_all"))
            or any(user_has_permission(request.user, a, "membres_view_own") for a in associations)
        ),

        "can_view_cotisations": bool(
            (federation and user_has_permission(request.user, federation, "cotisations_view_all"))
            or any(user_has_permission(request.user, a, "cotisations_view_own") for a in associations)
        ),

        "can_view_beneficiaires": bool(
            (federation and user_has_permission(request.user, federation, "beneficiaires_view"))
            or any(user_has_permission(request.user, a, "beneficiaires_view_own") for a in associations)
        ),

        "can_view_rapatriements": bool(
            federation and user_has_permission(request.user, federation, "rapatriements_view")
        ) or any(user_has_permission(request.user, a, "rapatriements_view") for a in associations),

        "can_view_activites": bool(
            (federation and user_has_permission(request.user, federation, "activites_view"))
            or any(user_has_permission(request.user, a, "activites_view") for a in associations)
        ),

        "can_view_transactions": bool(
            federation and user_has_permission(request.user, federation, "transactions_view")
        ),

        "can_view_documents": bool(
            (federation and user_has_permission(request.user, federation, "documents_view"))
            or any(user_has_permission(request.user, a, "documents_view") for a in associations)
        ),

        "can_view_alertes": bool(
            federation and user_has_permission(request.user, federation, "alertes_view")
        ),

        "can_view_reports": bool(
            federation and user_has_permission(request.user, federation, "rapports_view")
        ),

        "can_view_emails": bool(
            federation and user_has_permission(request.user, federation, "emails_view")
        ),

        "can_edit_associations": bool(
            federation and user_has_permission(request.user, federation, "associations_edit")
        ),

        "can_edit_cotisations": bool(
            federation and user_has_permission(request.user, federation, "cotisations_edit")
        ),

        "can_generate_cotisations": bool(
            federation and user_has_permission(request.user, federation, "cotisations_generate")
        ),

        "can_export_cotisations": bool(
            federation and user_has_permission(request.user, federation, "cotisations_export")
        ),

        "can_edit_beneficiaires": bool(
            federation and user_has_permission(request.user, federation, "beneficiaires_edit")
        ),

        "can_edit_rapatriements": bool(
            federation and user_has_permission(request.user, federation, "rapatriements_edit")
        ),

        "can_create_activites": bool(
            federation and user_has_permission(request.user, federation, "activites_create")
        ),

        "can_upload_documents": bool(
            (federation and user_has_permission(request.user, federation, "documents_upload"))
            or any(user_has_permission(request.user, a, "documents_upload") for a in associations)
        ),

        "can_send_notifications": bool(
            federation and user_has_permission(request.user, federation, "notifications_send")
        ),

        "can_publish_annonces": bool(
            federation and user_has_permission(request.user, federation, "annonces_publish")
        ),

        "can_edit_transactions": bool(
            federation and user_has_permission(request.user, federation, "transactions_edit")
        ),

        "can_transmettre_nouveaux_membres": any(
            user_has_permission(request.user, a, "transmettre_nouveaux_membres")
            for a in associations
        ),

        "can_view_informations": bool(
            (federation and user_has_permission(request.user, federation, "informations_view"))
            or any(user_has_permission(request.user, a, "informations_view") for a in associations)
        ),

        "can_publish_informations": bool(
            federation and user_has_permission(request.user, federation, "informations_publish")
        ),

        "can_edit_membres": bool(
            federation and user_has_permission(request.user, federation, "membres_edit")
        ),

        "can_traiter_documents": bool(
            federation and user_has_permission(request.user, federation, "documents_traiter")
        ),

        "can_propose_membres": any(
            user_has_permission(request.user, a, "membres_propose")
            for a in associations
        ),

        "can_manage_users": bool(
            federation and user_has_permission(request.user, federation, "users_manage")
        ),

        "can_export_cotisations_deces": bool(
            federation and user_has_permission(request.user, federation, "rapatriements_view")
        ),

        "can_export_personnes": bool(
            federation and user_has_permission(request.user, federation, "personnes_view")
        ),

        "can_finance_override": bool(
            federation and user_has_permission(request.user, federation, "finance_override")
        ),
    }


def global_alertes(request):
    if not request.user.is_authenticated:
        return {"total_alertes": 0}

    federations = get_user_entites(request.user).filter(type="federation")
    today = date.today()

    cotisations = CotisationAssociationMensuelle.objects.filter(
        affiliation__federation__in=federations,
        annee=today.year,
        mois=today.month,
        statut__in=["impaye", "en_attente", "partiel"],
    ).count()

    rapatriements = DossierRapatriement.objects.filter(
        affiliation__federation__in=federations,
        statut__in=["ouvert", "en_cours"],
    ).count()

    activites = ActiviteCulturelle.objects.filter(
        entite__in=federations,
        date__date__gte=today,
        date__date__lte=today + timedelta(days=7),
    ).count()

    return {
        "total_alertes": cotisations + rapatriements + activites
    }


def permissions_globales(request):
    return {}
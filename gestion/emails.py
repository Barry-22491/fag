from django.conf import settings
from django.core.mail import get_connection, send_mail
from smtplib import SMTPException

from .models import HistoriqueEmail, Notification
from .utils import get_association_users, get_situation_cotisation_association


def _format_euro(montant):
    return f"{montant:.2f} €".replace(".", ",")


def _destinataires_association(association):
    destinataires = []
    if association.email:
        destinataires.append(association.email)

    president = association.get_president()
    if president and president.email and president.email not in destinataires:
        destinataires.append(president.email)

    return destinataires


def _bloc_situation(situation):
    return (
        f"1) Cotisation mensuelle ({situation['periode']})\n"
        f"   - Montant du mois : {_format_euro(situation['montant_mensuel'])}\n"
        f"   - Déjà payé / avance appliquée : {_format_euro(situation['montant_mensuel_paye'])}\n"
        f"   - Reste à payer ce mois : {_format_euro(situation['montant_mensuel_reste'])}\n"
        f"   - Statut : {situation['statut_mois']}\n\n"
        f"2) Retard mensuel (mois antérieurs)\n"
        f"   - Montant en retard : {_format_euro(situation['retard_mensuel'])}\n\n"
        f"3) Contributions décès / rapatriement\n"
        f"   - Montant encore dû : {_format_euro(situation['montant_deces'])}\n\n"
        f"Total à régler : {_format_euro(situation['total_a_regler'])}\n"
        f"Identifiant de paiement : {situation['code_paiement'] or '-'}"
    )


def _resume_situation_court(situation, prefix=""):
    return (
        f"{prefix}"
        f"Mensuel : {_format_euro(situation['montant_mensuel'])} "
        f"(reste {_format_euro(situation['montant_mensuel_reste'])}) · "
        f"Retard : {_format_euro(situation['retard_mensuel'])} · "
        f"Décès : {_format_euro(situation['montant_deces'])} · "
        f"Total : {_format_euro(situation['total_a_regler'])}."
    )


def _creer_notifications_cotisation(association, titre, message):
    users = list(get_association_users(association))
    notifications = []
    for user in users:
        notifications.append(
            Notification(
                entite=association.entite,
                destinataire=user,
                titre=titre[:200],
                message=message,
                type_notification="cotisation",
                lien="/cotisations/",
            )
        )
    if notifications:
        Notification.objects.bulk_create(notifications)
    return len(users)


def _smtp_connection():
    return get_connection(
        backend=getattr(settings, "EMAIL_BACKEND", "gestion.email_backend.EmailBackend"),
        host=settings.EMAIL_HOST,
        port=settings.EMAIL_PORT,
        username=settings.EMAIL_HOST_USER,
        password=settings.EMAIL_HOST_PASSWORD,
        use_tls=getattr(settings, "EMAIL_USE_TLS", False),
        use_ssl=getattr(settings, "EMAIL_USE_SSL", False),
        timeout=getattr(settings, "EMAIL_TIMEOUT", 20),
    )


def _normaliser_type_email(type_email):
    valides = {choice[0] for choice in HistoriqueEmail.TYPE_CHOICES}
    if type_email in valides:
        return type_email
    return "general"


def _historiser(destinataire, type_email, sujet, succes, commentaire="", cotisation=None, activite=None):
    HistoriqueEmail.objects.create(
        destinataire=destinataire,
        type_email=_normaliser_type_email(type_email),
        sujet=sujet[:200],
        succes=succes,
        commentaire=(commentaire or "")[:2000],
        cotisation=cotisation,
        activite=activite,
    )


def envoyer_email_simple(
    sujet,
    message,
    destinataires,
    type_email=None,
    cotisation=None,
    activite=None,
):
    destinataires = [email for email in destinataires if email]
    if not destinataires:
        return False

    type_email = type_email or "notification_activite"

    try:
        send_mail(
            subject=sujet,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=destinataires,
            fail_silently=False,
            connection=_smtp_connection(),
        )
    except (SMTPException, OSError) as exc:
        for email in destinataires:
            _historiser(
                destinataire=email,
                type_email=type_email,
                sujet=sujet,
                succes=False,
                commentaire=str(exc),
                cotisation=cotisation,
                activite=activite,
            )
        return False

    for email in destinataires:
        _historiser(
            destinataire=email,
            type_email=type_email,
            sujet=sujet,
            succes=True,
            commentaire=message[:500],
            cotisation=cotisation,
            activite=activite,
        )

    return True


def envoyer_notification_generation_cotisation(cotisation):
    """
    Informe l'association après génération du mois :
    montant mensuel, retard mensuel, contributions décès.
    """
    situation = get_situation_cotisation_association(cotisation)
    association = situation["association"]
    nom = association.entite.nom

    sujet = f"Cotisations {situation['periode']} - {nom}"
    message = (
        f"Bonjour,\n\n"
        f"Les cotisations du mois de {situation['periode']} ont été générées "
        f"pour l'association {nom}.\n\n"
        f"Voici le détail de votre situation :\n\n"
        f"{_bloc_situation(situation)}\n\n"
        f"Merci de régulariser dès que possible.\n"
        f"Cordialement,\n"
        f"Bureau exécutif - FAG NRW e.V."
    )

    destinataires = _destinataires_association(association)
    email_ok = False
    if destinataires:
        email_ok = envoyer_email_simple(
            sujet=sujet,
            message=message,
            destinataires=destinataires,
            type_email="generation_cotisation",
            cotisation=cotisation,
        )

    notif_message = _resume_situation_court(
        situation,
        prefix=f"Cotisations {situation['periode']} générées pour {nom}. ",
    )
    users_notifies = _creer_notifications_cotisation(association, sujet, notif_message)

    return {
        "email_ok": email_ok,
        "destinataires": destinataires,
        "users_notifies": users_notifies,
        "situation": situation,
    }


def envoyer_rappel_cotisation(cotisation):
    """Rappel mensuel avec situation détaillée (mensuel, retard, décès)."""
    situation = get_situation_cotisation_association(cotisation)
    association = situation["association"]
    nom = association.entite.nom

    destinataires = _destinataires_association(association)
    if not destinataires:
        return False

    sujet = f"Rappel cotisation - {situation['periode']} - {nom}"
    message = (
        f"Bonjour,\n\n"
        f"Nous vous adressons un rappel concernant la situation financière "
        f"de l'association {nom}.\n\n"
        f"La cotisation de {situation['periode']} est actuellement : "
        f"{situation['statut_mois']}.\n\n"
        f"Détail de votre situation :\n\n"
        f"{_bloc_situation(situation)}\n\n"
        f"Merci de procéder au règlement dans les meilleurs délais.\n"
        f"Cordialement,\n"
        f"Bureau exécutif - FAG NRW e.V."
    )

    email_ok = envoyer_email_simple(
        sujet=sujet,
        message=message,
        destinataires=destinataires,
        type_email="rappel_cotisation",
        cotisation=cotisation,
    )

    notif_message = _resume_situation_court(
        situation,
        prefix=f"Rappel cotisation {situation['periode']} - {nom}. ",
    )
    _creer_notifications_cotisation(association, sujet, notif_message)

    return email_ok


def envoyer_confirmation_paiement(cotisation):
    """Confirmation de paiement avec situation actualisée après encaissement."""
    situation = get_situation_cotisation_association(cotisation)
    association = situation["association"]
    nom = association.entite.nom

    destinataires = _destinataires_association(association)
    if not destinataires:
        return False

    date_paiement = (
        cotisation.date_paiement.strftime("%d/%m/%Y")
        if cotisation.date_paiement
        else "-"
    )

    if situation["total_a_regler"] > 0:
        conclusion = (
            f"Il reste encore {_format_euro(situation['total_a_regler'])} à régler "
            f"au total (mensuel, retards et/ou décès).\n"
            f"Merci de compléter le paiement dès que possible."
        )
    else:
        conclusion = (
            "Votre association est à jour pour le mensuel, les retards "
            "et les contributions décès. Merci pour votre règlement."
        )

    sujet = f"Confirmation de paiement - {situation['periode']} - {nom}"
    message = (
        f"Bonjour,\n\n"
        f"Nous confirmons la réception du paiement de cotisation pour "
        f"l'association {nom}.\n\n"
        f"Paiement enregistré :\n"
        f"   - Période : {situation['periode']}\n"
        f"   - Montant payé sur ce mois : {_format_euro(situation['montant_mensuel_paye'])}\n"
        f"   - Date de paiement : {date_paiement}\n"
        f"   - Statut du mois : {situation['statut_mois']}\n\n"
        f"Situation actualisée après ce paiement :\n\n"
        f"{_bloc_situation(situation)}\n\n"
        f"{conclusion}\n\n"
        f"Cordialement,\n"
        f"Bureau exécutif - FAG NRW e.V."
    )

    email_ok = envoyer_email_simple(
        sujet=sujet,
        message=message,
        destinataires=destinataires,
        type_email="confirmation_paiement",
        cotisation=cotisation,
    )

    notif_message = _resume_situation_court(
        situation,
        prefix=f"Paiement confirmé ({situation['periode']}) - {nom}. ",
    )
    _creer_notifications_cotisation(association, sujet, notif_message)

    return email_ok


def envoyer_notification_activite(activite, destinataires):
    sujet = f"Nouvelle activité culturelle : {activite.titre}"
    message = (
        f"Bonjour,\n\n"
        f"Une activité culturelle est programmée.\n\n"
        f"Titre : {activite.titre}\n"
        f"Date : {activite.date.strftime('%d/%m/%Y %H:%M')}\n"
        f"Lieu : {activite.lieu or '-'}\n"
        f"Visibilité : {'Site public' if activite.est_public else 'Interne'}\n"
        f"Accès : {'Bénéficiaires uniquement' if activite.reserve_aux_beneficiaires else 'Ouvert'}\n\n"
        f"Description : {activite.description or '-'}\n"
    )

    return envoyer_email_simple(
        sujet=sujet,
        message=message,
        destinataires=destinataires,
        type_email="notification_activite",
        activite=activite,
    )


def envoyer_email_historise(
    *,
    sujet,
    message,
    destinataires,
    type_email="general",
    utilisateur=None,
    entite=None,
    fail_silently=True,
    cotisation=None,
    activite=None,
):
    """Envoi email compatible avec le modèle HistoriqueEmail actuel."""
    destinataires = [email for email in destinataires if email]
    type_email = _normaliser_type_email(type_email)

    if not destinataires:
        return False

    auteur = f" par {utilisateur}" if utilisateur else ""
    entite_info = f" [{entite}]" if entite else ""

    try:
        send_mail(
            subject=sujet,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=destinataires,
            fail_silently=False,
            connection=_smtp_connection(),
        )
    except Exception as exc:
        if not fail_silently:
            raise
        for email in destinataires:
            _historiser(
                destinataire=email,
                type_email=type_email,
                sujet=sujet,
                succes=False,
                commentaire=f"Erreur{auteur}{entite_info}: {exc}",
                cotisation=cotisation,
                activite=activite,
            )
        return False

    for email in destinataires:
        _historiser(
            destinataire=email,
            type_email=type_email,
            sujet=sujet,
            succes=True,
            commentaire=f"{message[:400]}{auteur}{entite_info}",
            cotisation=cotisation,
            activite=activite,
        )

    return True

from django.conf import settings
from django.core.mail import send_mail
from django.core.mail.backends.smtp import EmailBackend
from smtplib import SMTPException
from .models import HistoriqueEmail


def _smtp_connection():
    return EmailBackend(
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


def envoyer_rappel_cotisation(cotisation):
    association = cotisation.affiliation.association
    email = association.email

    if not email:
        return False

    sujet = "Rappel de cotisation mensuelle"
    message = (
        f"Bonjour,\n\n"
        f"La cotisation mensuelle de l'association {association.entite.nom} "
        f"pour la période {cotisation.mois}/{cotisation.annee} "
        f"est actuellement : {cotisation.get_statut_display()}.\n\n"
        f"Montant attendu : {cotisation.montant_attendu}\n"
        f"Montant payé : {cotisation.montant_paye}\n\n"
        f"Merci de régulariser la situation.\n"
        f"Cordialement,\n"
        f"FAG NRW e.V."
    )

    return envoyer_email_simple(
        sujet=sujet,
        message=message,
        destinataires=[email],
        type_email="rappel_cotisation",
        cotisation=cotisation,
    )


def envoyer_confirmation_paiement(cotisation):
    association = cotisation.affiliation.association
    email = association.email

    if not email:
        return False

    sujet = "Confirmation de paiement de cotisation"
    message = (
        f"Bonjour,\n\n"
        f"Nous confirmons la réception du paiement de la cotisation de l'association "
        f"{association.entite.nom} pour la période {cotisation.mois}/{cotisation.annee}.\n\n"
        f"Montant payé : {cotisation.montant_paye}\n"
        f"Date de paiement : {cotisation.date_paiement.strftime('%d/%m/%Y') if cotisation.date_paiement else '-'}\n\n"
        f"Merci.\n"
        f"Cordialement,\n"
        f"FAG NRW e.V."
    )

    return envoyer_email_simple(
        sujet=sujet,
        message=message,
        destinataires=[email],
        type_email="confirmation_paiement",
        cotisation=cotisation,
    )


def envoyer_notification_activite(activite, destinataires):
    sujet = f"Nouvelle activité culturelle : {activite.titre}"
    message = (
        f"Bonjour,\n\n"
        f"Une activité culturelle est programmée.\n\n"
        f"Titre : {activite.titre}\n"
        f"Date : {activite.date.strftime('%d/%m/%Y %H:%M')}\n"
        f"Lieu : {activite.lieu or '-'}\n\n"
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

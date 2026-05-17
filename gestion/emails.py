from django.conf import settings
from django.core.mail import send_mail 
from .models import HistoriqueEmail
from django.utils import timezone


def envoyer_email_simple(
    sujet,
    message,
    destinataires,
    type_email=None,
    cotisation=None,
    activite=None,
):
    if not destinataires:
        return False

    send_mail(
        subject=sujet,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=destinataires,
        fail_silently=False,
    )

    for email in destinataires:
        HistoriqueEmail.objects.create(
            destinataire=email,
            type_email=type_email or 'notification_activite',
            sujet=sujet,
            succes=True,
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
        type_email='rappel_cotisation',
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
        type_email='confirmation_paiement',
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
        type_email='notification_activite',
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
):
    destinataires = [email for email in destinataires if email]

    historique = HistoriqueEmail.objects.create(
        sujet=sujet,
        message=message,
        destinataires=", ".join(destinataires),
        type_email=type_email,
        envoye_par=utilisateur,
        entite=entite,
        statut="en_attente",
    )

    if not destinataires:
        historique.statut = "erreur"
        historique.erreur = "Aucun destinataire."
        historique.save()
        return False

    try:
        send_mail(
            subject=sujet,
            message=message,
            from_email=None,
            recipient_list=destinataires,
            fail_silently=fail_silently,
        )

        historique.statut = "envoye"
        historique.date_envoi = timezone.now()
        historique.save()
        return True

    except Exception as e:
        historique.statut = "erreur"
        historique.erreur = str(e)
        historique.save()
        return False
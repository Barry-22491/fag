from datetime import date

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _

from ..forms import ContactPublicForm
from ..models import (
    ActiviteCulturelle,
    Association,
    Bureau,
    BureauMembre,
    Entite,
    Information,
    MessageContact,
)


def public_home(request):
    now = timezone.now()

    activites = list(
        ActiviteCulturelle.objects
        .filter(est_public=True, date__gte=now)
        .order_by("date")[:3]
    )

    if len(activites) < 3:
        activites = list(
            ActiviteCulturelle.objects
            .filter(est_public=True)
            .order_by("-date")[:3]
        )

    infos = (
        Information.objects
        .filter(est_public=True, statut="publie")
        .order_by("-created_at")[:3]
    )

    return render(request, "public/home.html", {
        "activites": activites,
        "infos": infos,
    })


def public_about(request):
    federation = Entite.objects.filter(type="federation").first()

    bureau = None
    membres_bureau = BureauMembre.objects.none()

    if federation:
        today = date.today()

        bureau = Bureau.objects.filter(
            entite=federation
        ).filter(
            Q(date_fin__isnull=True) | Q(date_fin__gte=today)
        ).order_by("-date_debut").first()

        if bureau:
            membres_bureau = BureauMembre.objects.filter(
                bureau=bureau,
                adhesion__statut="valide"
            ).select_related(
                "poste",
                "adhesion__personne",
                "adhesion__association__entite"
            ).order_by("poste__ordre")

    return render(request, "public/about.html", {
        "bureau": bureau,
        "membres_bureau": membres_bureau,
    })


def public_associations(request):
    associations = (
        Association.objects
        .filter(affiliations__statut="active")
        .select_related("entite")
        .distinct()
        .order_by("entite__nom")
    )
    return render(request, "public/associations.html", {
        "associations": associations,
    })


def public_activites(request):
    activites = (
        ActiviteCulturelle.objects
        .filter(est_public=True)
        .order_by("-date")
    )
    return render(request, "public/activites.html", {
        "activites": activites,
    })


def public_informations(request):
    infos = Information.objects.filter(
        est_public=True,
        statut="publie"
    ).order_by("-created_at")

    return render(request, "public/informations.html", {
        "infos": infos,
    })


def public_contact(request):
    if request.method == "POST":
        form = ContactPublicForm(request.POST)

        if form.is_valid():
            nom = form.cleaned_data["nom"]
            email = form.cleaned_data["email"]
            sujet = form.cleaned_data["sujet"]
            message = form.cleaned_data["message"]

            MessageContact.objects.create(
                nom=nom,
                email=email,
                sujet=sujet,
                message=message,
            )

            mail = EmailMessage(
                subject=f"[Contact public] {sujet}",
                body=f"Nom : {nom}\nEmail : {email}\n\nMessage :\n{message}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[getattr(settings, "CONTACT_EMAIL", settings.DEFAULT_FROM_EMAIL)],
                reply_to=[email],
            )

            try:
                mail.send(fail_silently=False)
                messages.success(request, _("Votre message a été envoyé avec succès."))
            except Exception:
                messages.warning(
                    request,
                    _("Votre message a été enregistré, mais l'envoi email a échoué."),
                )

            return redirect("public_contact")
    else:
        form = ContactPublicForm()

    return render(request, "public/contact.html", {
        "form": form,
    })

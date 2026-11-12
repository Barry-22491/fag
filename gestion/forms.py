from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth.models import User # type: ignore
from django import forms # type: ignore
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _ # type: ignore


from .models import (
    Entite,
    Association,
    AffiliationAssociation,
    Personne,
    Adhesion,
    CotisationAssociationMensuelle,
    BeneficiaireFederation,
    DossierRapatriement,
    ActiviteCulturelle,
    Transaction,
    Document,
    Information,
    ContributionDecesAssociation,
    BureauMembre,
    Bureau, 
    Poste, 
    BureauMembre,
    PaiementAssociation,
)


LANGUE_CHOICES = [
    ("fr", "Français"),
    ("de", "Deutsch"),
    ("en", "English"),
]

class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for _, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput,)):
                widget.attrs['class'] = 'form-check-input'
            elif isinstance(widget, (forms.Select,)):
                widget.attrs['class'] = 'form-select'
            else:
                widget.attrs['class'] = 'form-control'


class DateInput(forms.DateInput):
    input_type = 'date'


class DateTimeInput(forms.DateTimeInput):
    input_type = 'datetime-local'
    format = '%Y-%m-%dT%H:%M'


class AssociationForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Association
        fields = ['entite', 'federation', 'ville', 'adresse', 'email', 'date_creation']
        widgets = {
            'date_creation': DateInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['entite'].queryset = Entite.objects.filter(type='association', association__isnull=True)
        self.fields['federation'].queryset = Entite.objects.filter(type='federation')
        


class AffiliationAssociationForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = AffiliationAssociation
        fields = ['association', 'federation', 'date_affiliation', 'statut', 'date_fin', 'montant_mensuel']
        widgets = {
            'date_affiliation': DateInput(),
            'date_fin': DateInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['federation'].queryset = Entite.objects.filter(type='federation')


class PersonneForm(BootstrapFormMixin,forms.ModelForm):
    class Meta:
        model = Personne
        fields = ['nom', 'prenom', 'email', 'telephone', 'ville','photo']


class AdhesionForm(BootstrapFormMixin,forms.ModelForm):
    class Meta:
        model = Adhesion
        fields = ['association', 'statut', 'type_membre', 'role']


class CotisationAssociationMensuelleForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = CotisationAssociationMensuelle
        fields = [
            'affiliation', 'annee', 'mois', 'montant_attendu', 'montant_paye',
            'date_paiement', 'mode_paiement'
        ]
        widgets = {
            'date_paiement': DateInput(),
        }

class BureauForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Bureau
        fields = ["entite", "date_debut", "date_fin"]
        widgets = {
            "date_debut": DateInput(),
            "date_fin": DateInput(),
        }


class PosteForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Poste
        fields = ["nom", "ordre"]

class BureauMembreForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = BureauMembre
        fields = ["poste", "adhesion"]

    def __init__(self, *args, **kwargs):
        bureau = kwargs.pop("bureau", None)
        super().__init__(*args, **kwargs)

        qs = Adhesion.objects.filter(
            statut="valide"
        ).select_related(
            "personne",
            "association__entite",
            "association__federation",
        )

        if bureau:
            if bureau.entite.type == "association":
                qs = qs.filter(association__entite=bureau.entite)
            elif bureau.entite.type == "federation":
                qs = qs.filter(
                    association__affiliations__federation=bureau.entite,
                    association__affiliations__statut="active",
                ).distinct()
                self.fields["adhesion"].help_text = (
                    "Président, membre du bureau ou simple membre : "
                    "toute adhésion validée d'une association affiliée."
                )

        self.fields["adhesion"].queryset = qs.order_by(
            "association__entite__nom",
            "personne__nom",
            "personne__prenom",
        )
        self.fields["adhesion"].label_from_instance = (
            lambda adhesion: (
                f"{adhesion.personne.prenom} {adhesion.personne.nom} — "
                f"{adhesion.association.entite.nom} ({adhesion.get_role_display()})"
            )
        )


class BeneficiaireFederationForm(BootstrapFormMixin,forms.ModelForm):
    class Meta:
        model = BeneficiaireFederation
        fields = ['personne', 'affiliation', 'date_activation', 'actif', 'motif_desactivation']
        widgets = {
            'date_activation': DateInput(),
        }


class DossierRapatriementForm(BootstrapFormMixin,forms.ModelForm):
    class Meta:
        model = DossierRapatriement
        fields = [
            'personne', 'affiliation', 'date_deces', 'lieu_deces', 'pays_deces',
            'destination_rapatriement', 'cout_total','personne_contact', 
            'telephone_contact','statut', 'observations'
        ]
        widgets = {
            'date_deces': DateInput(),
        }



class ActiviteCulturelleForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ActiviteCulturelle
        fields = [
            "entite",
            "titre_fr",
            "description_fr",
            "titre_de",
            "description_de",
            "titre_en",
            "description_en",
            "date",
            "lieu",
            "capacite",
            "reserve_aux_beneficiaires",
            "est_public",
        ]

        widgets = {
            "date": DateTimeInput(),
            "description_fr": forms.Textarea(attrs={"rows": 5}),
            "description_de": forms.Textarea(attrs={"rows": 5}),
            "description_en": forms.Textarea(attrs={"rows": 5}),
        }
        labels = {
            "entite": "Fédération",
            "titre_fr": "Titre",
            "description_fr": "Description",
            "titre_de": "Titel",
            "description_de": "Beschreibung",
            "titre_en": "Title",
            "description_en": "Description",
            "date": "Date et heure",
            "lieu": "Lieu",
            "capacite": "Capacité",
            "reserve_aux_beneficiaires": "Réservée aux bénéficiaires",
            "est_public": "Visible sur le site public",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date"].input_formats = [
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
        ]
        self.fields["capacite"].required = False
        self.fields["lieu"].required = False
        self.fields["titre_fr"].required = True
        self.fields["description_fr"].required = False
        self.fields["titre_de"].required = False
        self.fields["description_de"].required = False
        self.fields["titre_en"].required = False
        self.fields["description_en"].required = False
        if self.instance and self.instance.pk and not self.instance.titre_fr:
            self.initial["titre_fr"] = self.instance.titre
            self.initial["description_fr"] = self.instance.description

    def save(self, commit=True):
        activite = super().save(commit=False)
        activite.titre = self.cleaned_data["titre_fr"]
        activite.description = self.cleaned_data.get("description_fr") or ""
        if commit:
            activite.save()
        return activite


class TransactionForm(BootstrapFormMixin,forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['entite', 'ligne_budget', 'montant', 'type', 'date', 'libelle', 'donateur']
        widgets = {
            'date': DateInput(),
        }
        labels = {
            "entite": "Entité",
            "ligne_budget": "Ligne budgétaire",
            "montant": "Montant",
            "type": "Type",
            "date": "Date",
            "libelle": "Libellé",
            "donateur": "Donateur",
        }

    def __init__(self, *args, **kwargs):
        federation = kwargs.pop("federation", None)
        super().__init__(*args, **kwargs)

        self.fields["montant"].widget.attrs.setdefault("min", "0.01")
        self.fields["montant"].widget.attrs.setdefault("step", "0.01")

        if federation is not None:
            self.fields["entite"].queryset = Entite.objects.filter(pk=federation.pk)
            if "ligne_budget" in self.fields:
                ligne_qs = self.fields["ligne_budget"].queryset
                if hasattr(ligne_qs.model, "entite"):
                    self.fields["ligne_budget"].queryset = ligne_qs.filter(entite=federation)
                elif hasattr(ligne_qs.model, "budget"):
                    self.fields["ligne_budget"].queryset = ligne_qs.filter(
                        budget__entite=federation
                    )


class DocumentForm(BootstrapFormMixin, forms.ModelForm):

    class Meta:
        model = Document
        fields = [
            'entite',
            'titre',
            'type_document',
            'visibilite',
            'fichier'
        ]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        is_federation = kwargs.pop("is_federation", False)

        super().__init__(*args, **kwargs)

        if user:
            if is_federation:
                self.fields["visibilite"].choices = [
                    ("associations", "Partager aux associations"),
                    ("federation", "Réservé au bureau exécutif"),
                ]
            else:
                self.fields["visibilite"].choices = [
                    ("association", "Envoyé au bureau exécutif"),
                ]

class InformationForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Information
        fields = [
            "entite",
            "titre_fr",
            "contenu_fr",
            "titre_de",
            "contenu_de",
            "titre_en",
            "contenu_en",
            "type_information",
            "priorite",
            "statut",
            "est_public",
            "envoyer_email",
            "date_fin_affichage",
            "piece_jointe",
        ]

        widgets = {
            "date_fin_affichage": DateInput(),
            "contenu_fr": forms.Textarea(attrs={"rows": 5}),
            "contenu_de": forms.Textarea(attrs={"rows": 5}),
            "contenu_en": forms.Textarea(attrs={"rows": 5}),
        }

        labels = {
            "titre_fr": "Titre français",
            "contenu_fr": "Contenu français",
            "titre_de": "Titre allemand",
            "contenu_de": "Contenu allemand",
            "titre_en": "Titre anglais",
            "contenu_en": "Contenu anglais",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["titre_de"].required = False
        self.fields["contenu_de"].required = False
        self.fields["titre_en"].required = False
        self.fields["contenu_en"].required = False


class ContactPublicForm(BootstrapFormMixin, forms.Form):
    nom = forms.CharField(
        max_length=150,
        label=_("Nom")
    )
    email = forms.EmailField(
        label=_("Email")
    )
    sujet = forms.CharField(
        max_length=200,
        label=_("Sujet")
    )
    message = forms.CharField(
        label=_("Message"),
        widget=forms.Textarea(attrs={"rows": 5})
    )


class ContributionDecesAssociationForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ContributionDecesAssociation
        fields = ["montant_attendu", "montant_paye", "statut", "date_paiement"]
        widgets = {
            "date_paiement": DateInput(),
        }


# la gestion des utilisateur - 02.05.2026

ROLE_BUREAU_FEDERAL_CHOICES = [
    ("federation_direction", "Direction"),
    ("federation_finances", "Finances"),
    ("federation_social", "Social"),
    ("federation_organisation", "Organisation"),
    ("federation_projets", "Projets"),
    ("federation_communication", "Communication"),
    ("federation_lecture", "Lecture"),
]


class AdhesionInvitationField(forms.ModelChoiceField):
    def label_from_instance(self, adhesion):
        return (
            f"{adhesion.personne} — {adhesion.association.entite.nom} "
            f"({adhesion.get_role_display()})"
        )


def adhesions_invitables(federation):
    today = timezone.localdate()
    bureau_federal_ids = BureauMembre.objects.filter(
        bureau__entite=federation,
    ).filter(
        Q(bureau__date_fin__isnull=True) | Q(bureau__date_fin__gte=today)
    ).values_list("adhesion_id", flat=True)

    return (
        Adhesion.objects.filter(
            statut="valide",
            association__federation=federation,
            personne__compte__isnull=True,
        )
        .exclude(personne__email="")
        .filter(
            Q(role__in=["president", "membre_bureau"]) | Q(pk__in=bureau_federal_ids)
        )
        .select_related("personne", "association__entite")
        .order_by("personne__nom", "personne__prenom")
    )


def _sur_bureau_federal(adhesion):
    today = timezone.localdate()
    return BureauMembre.objects.filter(
        adhesion=adhesion,
        bureau__entite=adhesion.association.federation,
    ).filter(
        Q(bureau__date_fin__isnull=True) | Q(bureau__date_fin__gte=today)
    ).exists()


class InvitationUtilisateurForm(BootstrapFormMixin, forms.Form):
    mode = forms.ChoiceField(
        label="Type de compte",
        choices=[
            ("membre", "Responsable d'association ou bureau exécutif"),
            ("administrateur", "Administrateur"),
        ],
        initial="membre",
    )
    adhesion = AdhesionInvitationField(
        label="Personne",
        queryset=Adhesion.objects.none(),
        required=False,
        help_text="Président ou bureau d'association, ou personne déjà ajoutée au bureau exécutif de la fédération.",
    )
    role_bureau = forms.ChoiceField(
        label="Rôle au bureau exécutif",
        choices=[("", "—")] + ROLE_BUREAU_FEDERAL_CHOICES,
        required=False,
        help_text="À remplir seulement si la personne siège au bureau exécutif.",
    )
    prenom = forms.CharField(label="Prénom", max_length=100, required=False)
    nom = forms.CharField(label="Nom", max_length=100, required=False)
    email = forms.EmailField(label="Email", required=False)

    def __init__(self, *args, federation=None, **kwargs):
        self.federation = federation
        super().__init__(*args, **kwargs)
        if federation is not None:
            self.fields["adhesion"].queryset = adhesions_invitables(federation)

    def clean(self):
        cleaned = super().clean()
        mode = cleaned.get("mode")
        if mode == "administrateur":
            return self._clean_administrateur(cleaned)
        return self._clean_membre(cleaned)

    def _clean_administrateur(self, cleaned):
        prenom = (cleaned.get("prenom") or "").strip()
        nom = (cleaned.get("nom") or "").strip()
        email = (cleaned.get("email") or "").strip()
        if not prenom:
            self.add_error("prenom", "Indiquez le prénom.")
        if not nom:
            self.add_error("nom", "Indiquez le nom.")
        if not email:
            self.add_error("email", "Indiquez l'email.")
        elif User.objects.filter(email__iexact=email).exists() or User.objects.filter(username__iexact=email).exists():
            self.add_error("email", "Un compte existe déjà avec cet email.")
        if self.errors:
            return cleaned
        cleaned["prenom"] = prenom
        cleaned["nom"] = nom
        cleaned["email"] = email
        cleaned["personne"] = None
        cleaned["attributions"] = [(self.federation, "federation_direction")]
        return cleaned

    def _clean_membre(self, cleaned):
        adhesion = cleaned.get("adhesion")
        if not adhesion:
            self.add_error("adhesion", "Choisissez une personne déjà enregistrée.")
            return cleaned

        if adhesion.personne.compte_id:
            self.add_error("adhesion", "Cette personne a déjà un compte.")
            return cleaned

        attributions = []
        if adhesion.role == "president":
            attributions.append((adhesion.association.entite, "association_president"))
        elif adhesion.role == "membre_bureau":
            attributions.append((adhesion.association.entite, "association_lecture"))

        if _sur_bureau_federal(adhesion):
            role_bureau = cleaned.get("role_bureau")
            if not role_bureau:
                self.add_error("role_bureau", "Choisissez le rôle au bureau exécutif.")
            else:
                attributions.append((adhesion.association.federation, role_bureau))

        if not attributions and not self.errors:
            self.add_error("adhesion", "Cette personne ne peut pas recevoir de compte.")

        cleaned["personne"] = adhesion.personne
        cleaned["prenom"] = adhesion.personne.prenom
        cleaned["nom"] = adhesion.personne.nom
        cleaned["email"] = adhesion.personne.email
        cleaned["attributions"] = attributions
        return cleaned


class MotDePasseOublieForm(BootstrapFormMixin, PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].label = "Email"


class ChangerMotDePasseForm(BootstrapFormMixin, PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["old_password"].label = "Mot de passe actuel"
        self.fields["new_password1"].label = "Nouveau mot de passe"
        self.fields["new_password2"].label = "Confirmer le nouveau mot de passe"


class DefinirMotDePasseForm(BootstrapFormMixin, SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].label = "Nouveau mot de passe"
        self.fields["new_password2"].label = "Confirmer le mot de passe"

class AssociationUpdateForm(BootstrapFormMixin, forms.ModelForm):
    nom = forms.CharField(max_length=200, label="Nom de l'association")
    logo = forms.ImageField(required=False, label="Logo")

    class Meta:
        model = Association
        fields = [
            "nom",
            "logo",
            "ville",
            "adresse",
            "email",
            "date_creation",
        ]
        widgets = {
            "date_creation": DateInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.entite:
            self.fields["nom"].initial = self.instance.entite.nom
            self.fields["logo"].initial = self.instance.entite.logo

    def save(self, commit=True):
        association = super().save(commit=False)

        association.entite.nom = self.cleaned_data["nom"]

        if self.cleaned_data.get("logo"):
            association.entite.logo = self.cleaned_data["logo"]

        if commit:
            association.entite.save()
            association.save()

        return association
    

class PaiementAssociationForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = PaiementAssociation
        fields = [
            "association",
            "montant",
            "date_paiement",
            "mode_paiement",
            "reference",
            "commentaire",
        ]
        widgets = {
            "date_paiement": DateInput(),
            "commentaire": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "association": "Association",
            "montant": "Montant reçu",
            "date_paiement": "Date de paiement",
            "mode_paiement": "Mode de paiement",
            "reference": "Référence",
            "commentaire": "Commentaire",
        }

    def __init__(self, *args, **kwargs):
        federation = kwargs.pop("federation", None)
        super().__init__(*args, **kwargs)

        self.fields["association"].queryset = Association.objects.none()
        self.fields["montant"].widget.attrs.setdefault("min", "0.01")
        self.fields["montant"].widget.attrs.setdefault("step", "0.01")

        if federation:
            self.fields["association"].queryset = Association.objects.filter(
                federation=federation
            ).select_related("entite").order_by("entite__nom")
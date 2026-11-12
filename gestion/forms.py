from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth.models import User # type: ignore
from django import forms # type: ignore
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
        fields = ["bureau", "poste", "adhesion"]

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
                qs = qs.filter(association__federation=bureau.entite)

        self.fields["adhesion"].queryset = qs


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
    langue_publication = forms.ChoiceField(
        choices=LANGUE_CHOICES,
        label=_("Langue de publication")
    )

    class Meta:
        model = ActiviteCulturelle
        fields = [
            "entite",
            "langue_publication",
            "titre",
            "description",
            "date",
            "lieu",
            "capacite",
            "reserve_aux_beneficiaires",
            "est_public",
        ]

        widgets = {
            "date": DateTimeInput(),
            "description": forms.Textarea(attrs={"rows": 5}),
        }
        labels = {
            "entite": "Fédération",
            "titre": "Titre",
            "description": "Description",
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
        if self.instance and self.instance.pk and not self.is_bound:
            if self.instance.titre_de and self.instance.titre == self.instance.titre_de:
                self.initial["langue_publication"] = "de"
            elif self.instance.titre_en and self.instance.titre == self.instance.titre_en:
                self.initial["langue_publication"] = "en"
            else:
                self.initial["langue_publication"] = "fr"


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

ROLE_INVITATION_CHOICES = [
    ("federation_direction", "Direction fédération"),
    ("federation_finances", "Finances fédération"),
    ("federation_social", "Social fédération"),
    ("federation_organisation", "Organisation fédération"),
    ("federation_projets", "Projets fédération"),
    ("federation_communication", "Communication fédération"),
    ("federation_externe", "Externe fédération"),
    ("federation_lecture", "Lecture fédération"),
    ("association_president", "Président d'association"),
    ("association_lecture", "Lecture association"),
]


class InvitationUtilisateurForm(BootstrapFormMixin, forms.Form):
    email = forms.EmailField(label="Email")
    prenom = forms.CharField(max_length=100, label="Prénom")
    nom = forms.CharField(max_length=100, label="Nom")
    role = forms.ChoiceField(label="Rôle", choices=ROLE_INVITATION_CHOICES)
    entite = forms.ModelChoiceField(
        label="Rattachement",
        queryset=Entite.objects.none(),
    )

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role")
        entite = cleaned.get("entite")
        if not role or not entite:
            return cleaned
        if role.startswith("association") and entite.type != "association":
            self.add_error("entite", "Ce rôle se rattache à une association.")
        if role.startswith("federation") and entite.type != "federation":
            self.add_error("entite", "Ce rôle se rattache à la fédération.")
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
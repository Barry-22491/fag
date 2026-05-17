from datetime import date

from django.contrib.auth.models import User # type: ignore
from django.core.exceptions import ValidationError # type: ignore
from django.core.validators import MinValueValidator, MaxValueValidator # type: ignore
from django.db import models # type: ignore
from django.db.models import Q, Sum # type: ignore
from django.utils.translation import get_language # type: ignore
from decimal import Decimal


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Entite(TimeStampedModel):
    TYPE_CHOICES = [
        ("federation", "Fédération"),
        ("association", "Association"),
    ]

    nom = models.CharField(max_length=200)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    logo = models.ImageField(upload_to="logos/", null=True, blank=True)
    abreviation = models.CharField(max_length=10, blank=True)

    class Meta:
        indexes = [models.Index(fields=["type"])]

    def __str__(self):
        return f"{self.nom} ({self.type})"


class Association(TimeStampedModel):
    code_paiement = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        null=True
    )

    entite = models.OneToOneField(
        Entite,
        on_delete=models.CASCADE,
        related_name="association",
    )

    federation = models.ForeignKey(
        Entite,
        on_delete=models.PROTECT,
        related_name="associations",
    )

    ville = models.CharField(max_length=100)
    adresse = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    date_creation = models.DateField()

    def clean(self):
        if self.entite.type != "association":
            raise ValidationError("L'entité doit être de type association.")

        if self.federation.type != "federation":
            raise ValidationError("La fédération doit être de type fédération.")

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        super().save(*args, **kwargs)

        if is_new and not self.code_paiement:
            self.code_paiement = f"ASSO-{self.pk:04d}"
            super().save(update_fields=["code_paiement"])

    def get_president(self):
        adhesion = Adhesion.objects.filter(
            association=self,
            statut="valide",
            role="president",
        ).select_related("personne").first()

        return adhesion.personne if adhesion else None

    def __str__(self):
        if self.code_paiement:
            return f"{self.code_paiement} - {self.entite.nom}"
        return self.entite.nom

class Personne(TimeStampedModel):

    STATUS_ChOICES = [
        ("actif","Actif"),
        ("decede","Decede"),
    ]
    numero = models.CharField(max_length=30, unique=True, blank=True, null=True)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    telephone = models.CharField(max_length=30, blank=True)
    ville = models.CharField(max_length=100, blank=True)
    statut = models.CharField(max_length=20,choices=STATUS_ChOICES,default="actif")
    date_deces = models.DateField(null=True,blank=True)
    photo = models.ImageField(upload_to="personnes/",null=True,blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["email"],
                condition=~Q(email=""),
                name="unique_email_if_not_empty",
            )
        ]

    def __str__(self):
        return f"{self.prenom} {self.nom}"


class Adhesion(TimeStampedModel):
    TYPE_MEMBRE_CHOICES = [
        ("actif", "Actif"),
        ("honoraire", "Honoraire"),
    ]

    ROLE_CHOICES = [
        ("membre", "Membre"),
        ("president", "Président"),
        ("membre_bureau", "Membre du bureau"),
    ]

    STATUT_CHOICES = [
        ("en_attente", "En attente"),
        ("valide", "Validé"),
        ("refuse", "Refusé"),
    ]

    personne = models.ForeignKey(
        Personne,
        on_delete=models.CASCADE,
        related_name="adhesions",
    )
    association = models.ForeignKey(
        Association,
        on_delete=models.CASCADE,
        related_name="adhesions",
    )
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default="en_attente",
    )
    valide_par = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="adhesions_validees",
    )
    date_validation = models.DateTimeField(null=True, blank=True)
    date_adhesion = models.DateField(auto_now_add=True)
    type_membre = models.CharField(
        max_length=20,
        choices=TYPE_MEMBRE_CHOICES,
        default="actif",
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="membre",
    )

    class Meta:
        indexes = [models.Index(fields=["statut"])]
        constraints = [
            models.UniqueConstraint(
                fields=["personne", "association"],
                name="unique_personne_association",
            )
        ]

    def clean(self):
        if self.statut == "valide":
            qs = Adhesion.objects.filter(
                personne=self.personne,
                statut="valide",
            ).exclude(pk=self.pk)

            if qs.exists():
                raise ValidationError("Une seule adhésion validée autorisée.")

    def __str__(self):
        return f"{self.personne} - {self.association}"


class Bureau(TimeStampedModel):
    entite = models.ForeignKey(
        Entite,
        on_delete=models.CASCADE,
        related_name="bureaux",
    )
    date_debut = models.DateField()
    date_fin = models.DateField(null=True, blank=True)

    def clean(self):
        if self.date_fin and self.date_fin <= self.date_debut:
            raise ValidationError("La date de fin doit être après la date de début.")

    def __str__(self):
        return f"Bureau {self.entite.nom} ({self.date_debut})"


class Poste(TimeStampedModel):
    nom = models.CharField(max_length=100, unique=True)
    ordre = models.IntegerField(default=0)

    def __str__(self):
        return self.nom


class BureauMembre(TimeStampedModel):
    bureau = models.ForeignKey(
        Bureau,
        on_delete=models.CASCADE,
        related_name="membres",
    )
    poste = models.ForeignKey(Poste, on_delete=models.PROTECT)
    adhesion = models.ForeignKey(Adhesion, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["bureau", "poste"],
                name="unique_poste_par_bureau",
            )
        ]

    def clean(self):
        if self.adhesion.statut != "valide":
            raise ValidationError("Le membre doit avoir une adhésion validée.")

        if self.bureau.entite.type == "association":
            if self.adhesion.association.entite != self.bureau.entite:
                raise ValidationError("Le membre doit appartenir à cette association.")

        elif self.bureau.entite.type == "federation":
            if self.adhesion.association.federation != self.bureau.entite:
                raise ValidationError(
                    "Le membre doit appartenir à une association affiliée à cette fédération."
                )

    def __str__(self):
        return f"{self.adhesion.personne} - {self.poste}"


class Evenement(TimeStampedModel):
    entite = models.ForeignKey(
        Entite,
        on_delete=models.CASCADE,
        related_name="evenements",
    )
    titre = models.CharField(max_length=150)
    date = models.DateTimeField()
    lieu = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.titre


class Participation(TimeStampedModel):
    evenement = models.ForeignKey(Evenement, on_delete=models.CASCADE)
    personne = models.ForeignKey(Personne, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["evenement", "personne"],
                name="unique_participation",
            )
        ]


class Budget(TimeStampedModel):
    entite = models.ForeignKey(Entite, on_delete=models.CASCADE)
    annee = models.IntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["entite", "annee"],
                name="unique_budget",
            )
        ]

    def __str__(self):
        return f"{self.entite.nom} - {self.annee}"


class LigneBudget(TimeStampedModel):
    TYPE_CHOICES = [
        ("recette", "Recette"),
        ("depense", "Dépense"),
    ]

    budget = models.ForeignKey(
        Budget,
        on_delete=models.CASCADE,
        related_name="lignes",
    )
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    libelle = models.CharField(max_length=200)
    montant_prevu = models.DecimalField(max_digits=10, decimal_places=2)
    montant_realise = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    def __str__(self):
        return self.libelle


class Transaction(TimeStampedModel):
    TYPE_CHOICES = [
        ("recette", "Recette"),
        ("depense", "Dépense"),
    ]

    entite = models.ForeignKey(Entite, on_delete=models.CASCADE)
    ligne_budget = models.ForeignKey(
        LigneBudget,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    date = models.DateField(default=date.today)
    libelle = models.CharField(max_length=200, blank=True)
    donateur = models.ForeignKey(
        Personne,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["type"]),
        ]

    def __str__(self):
        return f"{self.type} - {self.montant}"


class Document(TimeStampedModel):
    STATUT_CHOICES = [
        ("nouveau", "Nouveau"),
        ("vu", "Vu"),
        ("traite", "Traité"),
        ("rejete", "Rejeté"),
    ]

    VISIBILITE_CHOICES = [
        ("association", "Envoyé au bureau exécutif"),
        ("associations", "partager aux associations"),
        ("federation", "Réservé au bureau exécutif"),
    ]

    entite = models.ForeignKey(Entite, on_delete=models.CASCADE)
    titre = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    fichier = models.FileField(upload_to="documents/")
    type_document = models.CharField(max_length=100, blank=True)
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default="nouveau",
    )
    visibilite = models.CharField(
        max_length=20,
        choices=VISIBILITE_CHOICES,
        default="association",
    )
    soumis_par = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="documents_soumis",
    )
    traite_par = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="documents_traites",
    )
    commentaire_traitement = models.TextField(blank=True)
    date_traitement = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.titre


class Notification(TimeStampedModel):
    TYPE_CHOICES = [
        ("document", "Document"),
        ("nouveaux_membres", "Nouveaux membres"),
        ("information", "Information"),
        ("rapatriement", "Rapatriement"),
        ("cotisation", "Cotisation"),
        ("general", "Général"),
    ]

    entite = models.ForeignKey(
        Entite,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    destinataire = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    titre = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    type_notification = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        default="general",
    )
    document = models.ForeignKey(
        Document,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    lien = models.CharField(max_length=255, blank=True)
    lu = models.BooleanField(default=False)

    def __str__(self):
        return self.titre or self.message[:50]


class HistoriqueAdhesion(TimeStampedModel):
    adhesion = models.ForeignKey(
        Adhesion,
        on_delete=models.CASCADE,
        related_name="historique",
    )
    type_evenement = models.CharField(max_length=50)
    date = models.DateField(default=date.today)
    commentaire = models.TextField(blank=True)


class Role(TimeStampedModel):
    nom = models.CharField(max_length=50, unique=True)
    niveau = models.IntegerField(default=0)

    def __str__(self):
        return self.nom


class UserEntiteRole(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    entite = models.ForeignKey(Entite, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.PROTECT)

    class Meta:
        unique_together = ("user", "entite", "role")

    def __str__(self):
        return f"{self.user} - {self.entite} - {self.role}"


class AffiliationAssociation(TimeStampedModel):
    STATUT_CHOICES = [
        ("active", "Active"),
        ("suspendue", "Suspendue"),
        ("radiee", "Radiée"),
    ]

    association = models.ForeignKey(
        Association,
        on_delete=models.CASCADE,
        related_name="affiliations",
    )
    federation = models.ForeignKey(
        Entite,
        on_delete=models.PROTECT,
        related_name="affiliations_associations",
    )
    date_affiliation = models.DateField()
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default="active",
    )
    date_fin = models.DateField(null=True, blank=True)
    montant_mensuel = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["association", "federation"],
                name="unique_affiliation_association_federation",
            )
        ]

    def clean(self):
        if self.federation.type != "federation":
            raise ValidationError("La fédération doit être de type fédération.")
        if self.association.federation_id != self.federation_id:
            raise ValidationError("L'association doit appartenir à cette fédération.")

    def __str__(self):
        return f"{self.association} -> {self.federation.nom}"


class CotisationAssociationMensuelle(TimeStampedModel):
    STATUT_CHOICES = [
        ("en_attente", "En attente"),
        ("paye", "Payé"),
        ("partiel", "Partiel"),
        ("impaye", "Impayé"),
    ]

    MODE_PAIEMENT_CHOICES = [
        ("virement", "Virement"),
        ("cash", "Espèces"),
        ("cheque", "Chèque"),
        ("carte", "Carte bancaire"),
    ]

    affiliation = models.ForeignKey(
        AffiliationAssociation,
        on_delete=models.CASCADE,
        related_name="cotisations_mensuelles",
    )
    annee = models.PositiveIntegerField()
    mois = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    montant_attendu = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=20,
    )
    montant_paye = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default="en_attente",
    )
    date_paiement = models.DateField(null=True, blank=True)
    mode_paiement = models.CharField(
        max_length=20,
        choices=MODE_PAIEMENT_CHOICES,
        blank=True,
    )
    modifie_par = models.ForeignKey(User,null=True,blank=True,on_delete=models.SET_NULL,related_name="cotisation_modifiees")
    date_modification_paiement = models.DateTimeField(null=True,blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["affiliation", "annee", "mois"],
                name="unique_cotisation_mensuelle_par_affiliation",
            )
        ]
        ordering = ["-annee", "-mois"]

    def clean(self):
        if self.montant_paye < 0:
            raise ValidationError("Le montant payé ne peut pas être négatif.")
        if self.montant_paye > self.montant_attendu:
            raise ValidationError("Le montant payé ne peut pas dépasser le montant attendu.")
        if self.montant_paye == 0 and self.statut == "paye":
            raise ValidationError("Une cotisation payée doit avoir un montant payé.")

        if self.montant_paye == self.montant_attendu:
            self.statut = "paye"
        elif 0 < self.montant_paye < self.montant_attendu:
            self.statut = "partiel"

    def __str__(self):
        return f"{self.affiliation.association} - {self.mois}/{self.annee}"


class BeneficiaireFederation(TimeStampedModel):
    personne = models.ForeignKey(
        Personne,
        on_delete=models.CASCADE,
        related_name="benefices_federation",
    )
    affiliation = models.ForeignKey(
        AffiliationAssociation,
        on_delete=models.CASCADE,
        related_name="beneficiaires",
    )
    date_activation = models.DateField()
    actif = models.BooleanField(default=True)
    motif_desactivation = models.CharField(max_length=255, blank=True)
    date_desactivation = models.DateTimeField(null=True,blank=True)
    date_reactivation = models.DateTimeField(null=True, blank=True)
    desactive_par = models.ForeignKey(User,null=True,
                                      blank=True,
                                      on_delete=models.SET_NULL,related_name="beneficiaires_desactives")
    reactive_par = models.ForeignKey(
    User,
    null=True,
    blank=True,
    on_delete=models.SET_NULL,
    related_name="beneficiaires_reactives"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["personne", "affiliation"],
                name="unique_beneficiaire_par_affiliation",
            )
        ]

    def clean(self):
        is_member = Adhesion.objects.filter(
            personne=self.personne,
            association=self.affiliation.association,
            statut="valide",
        ).exists()

        if not is_member:
            raise ValidationError(
                "La personne doit avoir une adhésion validée dans l'association affiliée."
            )

    def __str__(self):
        return f"{self.personne} - {self.affiliation.federation.nom}"


class ServiceFederation(TimeStampedModel):
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    actif = models.BooleanField(default=True)

    def __str__(self):
        return self.nom


class PersonneService(TimeStampedModel):
    beneficiaire = models.ForeignKey(
        BeneficiaireFederation,
        on_delete=models.CASCADE,
        related_name="services",
    )
    service = models.ForeignKey(ServiceFederation, on_delete=models.CASCADE)
    actif = models.BooleanField(default=True)
    date_activation = models.DateField()
    date_fin = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["beneficiaire", "service"],
                name="unique_service_par_beneficiaire",
            )
        ]

    def clean(self):
        if self.date_fin and self.date_fin < self.date_activation:
            raise ValidationError("La date de fin doit être après la date d'activation.")


class DossierRapatriement(TimeStampedModel):
    STATUT_CHOICES = [
        ("ouvert", "Ouvert"),
        ("en_cours", "En cours"),
        ("termine", "Terminé"),
        ("refuse", "Refusé"),
    ]

    personne = models.ForeignKey(
        Personne,
        on_delete=models.PROTECT,
        related_name="dossiers_rapatriement",
    )
    affiliation = models.ForeignKey(
        AffiliationAssociation,
        on_delete=models.PROTECT,
    )
    date_deces = models.DateField()
    lieu_deces = models.CharField(max_length=200)
    pays_deces = models.CharField(max_length=100, blank=True)
    destination_rapatriement = models.CharField(max_length=200)
    personne_contact = models.CharField(max_length=200, blank=True)
    telephone_contact = models.CharField(max_length=50, blank=True)
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default="ouvert",
    )
    observations = models.TextField(blank=True)
    cout_total = models.DecimalField(
    max_digits=10,
    decimal_places=2,
    default=0
    )

    montant_par_association = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    montant_collecte = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    reste_a_collecter = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    contributions_generees = models.BooleanField(
        default=False
    )
    def clean(self):
        is_beneficiaire = BeneficiaireFederation.objects.filter(
            personne=self.personne,
            affiliation=self.affiliation,
            actif=True,
        ).exists()

        if not is_beneficiaire:
            raise ValidationError(
                "La personne doit être bénéficiaire active de la fédération."
            )

    def __str__(self):
        return f"Rapatriement - {self.personne}"


class ActiviteCulturelle(TimeStampedModel):
    entite = models.ForeignKey(
        Entite,
        on_delete=models.CASCADE,
        related_name="activites_culturelles",
    )
    titre = models.CharField(max_length=150)
    titre_fr = models.CharField(max_length=150, blank=True)
    titre_de = models.CharField(max_length=150, blank=True)
    titre_en = models.CharField(max_length=150, blank=True)

    description = models.TextField(blank=True)
    description_fr = models.TextField(blank=True)
    description_de = models.TextField(blank=True)
    description_en = models.TextField(blank=True)

    date = models.DateTimeField()
    lieu = models.CharField(max_length=200, blank=True)
    capacite = models.PositiveIntegerField(null=True, blank=True)
    reserve_aux_beneficiaires = models.BooleanField(default=True)
    est_public = models.BooleanField(default=False)

    def titre_traduit(self):
        lang = get_language()

        if lang == "de" and self.titre_de:
            return self.titre_de
        if lang == "en" and self.titre_en:
            return self.titre_en
        if lang == "fr" and self.titre_fr:
            return self.titre_fr

        return self.titre_fr or self.titre

    def description_traduite(self):
        lang = get_language()

        if lang == "de" and self.description_de:
            return self.description_de
        if lang == "en" and self.description_en:
            return self.description_en
        if lang == "fr" and self.description_fr:
            return self.description_fr

        return self.description_fr or self.description

    def __str__(self):
        return self.titre_fr or self.titre


class ParticipationActivite(TimeStampedModel):
    activite = models.ForeignKey(
        ActiviteCulturelle,
        on_delete=models.CASCADE,
        related_name="participants",
    )
    personne = models.ForeignKey(
        Personne,
        on_delete=models.CASCADE,
        related_name="participations_activites",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["activite", "personne"],
                name="unique_participation_activite",
            )
        ]

    def clean(self):
        if self.activite.reserve_aux_beneficiaires:
            is_beneficiaire = BeneficiaireFederation.objects.filter(
                personne=self.personne,
                affiliation__federation=self.activite.entite,
                actif=True,
            ).exists()

            if not is_beneficiaire:
                raise ValidationError(
                    "Cette activité est réservée aux bénéficiaires de la fédération."
                )


class HistoriqueEmail(TimeStampedModel):
    TYPE_CHOICES = [
        ("rappel_cotisation", "Rappel cotisation"),
        ("confirmation_paiement", "Confirmation paiement"),
        ("notification_activite", "Notification activité"),
    ]

    destinataire = models.EmailField()
    type_email = models.CharField(max_length=30, choices=TYPE_CHOICES)
    sujet = models.CharField(max_length=200)
    succes = models.BooleanField(default=True)
    commentaire = models.TextField(blank=True)

    cotisation = models.ForeignKey(
        CotisationAssociationMensuelle,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="emails",
    )
    activite = models.ForeignKey(
        ActiviteCulturelle,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="emails",
    )

    def __str__(self):
        return f"{self.type_email} - {self.destinataire}"


class Information(TimeStampedModel):
    TYPE_CHOICES = [
        ("annonce", "Annonce"),
        ("communique", "Communiqué"),
        ("convocation", "Convocation"),
        ("rappel", "Rappel"),
        ("note", "Note d'information"),
    ]

    PRIORITE_CHOICES = [
        ("normale", "Normale"),
        ("importante", "Importante"),
        ("urgente", "Urgente"),
    ]

    STATUT_CHOICES = [
        ("brouillon", "Brouillon"),
        ("publie", "Publié"),
        ("archive", "Archivé"),
    ]

    entite = models.ForeignKey(
        Entite,
        on_delete=models.CASCADE,
        related_name="informations",
    )
    titre = models.CharField(max_length=200)
    titre_fr = models.CharField(max_length=200, blank=True)
    titre_de = models.CharField(max_length=200, blank=True)
    titre_en = models.CharField(max_length=200, blank=True)

    contenu = models.TextField()
    contenu_fr = models.TextField(blank=True)
    contenu_de = models.TextField(blank=True)
    contenu_en = models.TextField(blank=True)

    type_information = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default="annonce",
    )
    priorite = models.CharField(
        max_length=20,
        choices=PRIORITE_CHOICES,
        default="normale",
    )
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default="brouillon",
    )
    date_publication = models.DateTimeField(null=True, blank=True)
    date_fin_affichage = models.DateField(null=True, blank=True)
    piece_jointe = models.FileField(
        upload_to="informations/",
        null=True,
        blank=True,
    )
    auteur = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    est_public = models.BooleanField(default=False)
    envoyer_email = models.BooleanField(default=False, verbose_name="Envoyer une notification email")

    def titre_traduit(self):
        lang = get_language()

        if lang == "de" and self.titre_de:
            return self.titre_de
        if lang == "en" and self.titre_en:
            return self.titre_en
        if lang == "fr" and self.titre_fr:
            return self.titre_fr

        return self.titre_fr or self.titre

    def contenu_traduit(self):
        lang = get_language()

        if lang == "de" and self.contenu_de:
            return self.contenu_de
        if lang == "en" and self.contenu_en:
            return self.contenu_en
        if lang == "fr" and self.contenu_fr:
            return self.contenu_fr

        return self.contenu_fr or self.contenu

    def clean(self):
        if self.entite and self.entite.type != "federation":
            raise ValidationError("Une information doit être publiée par une fédération.")

    def __str__(self):
        return self.titre_fr or self.titre


class ContributionDecesAssociation(TimeStampedModel):
    STATUT_CHOICES = [
        ("en_attente", "En attente"),
        ("paye", "Payé"),
        ("partiel", "Partiel"),
        ("impaye", "Impayé"),
    ]

    dossier = models.ForeignKey(
        DossierRapatriement,
        on_delete=models.CASCADE,
        related_name="contributions_deces",
    )
    association = models.ForeignKey(
        Association,
        on_delete=models.CASCADE,
        related_name="contributions_deces",
    )
    montant_attendu = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=200,
    )
    montant_paye = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default="en_attente",
    )
    date_paiement = models.DateField(null=True, blank=True)

    def save(self, *args, **kwargs):

        if self.montant_paye >= self.montant_attendu:
            self.statut = "paye"

        elif self.montant_paye > 0:
            self.statut = "partiel"

        else:
            self.statut = "impaye"

        super().save(*args, **kwargs)

        dossier = self.dossier

        total_collecte = ContributionDecesAssociation.objects.filter(
            dossier=dossier
        ).aggregate(
            total=Sum("montant_paye")
        )["total"] or Decimal("0")

        dossier.montant_collecte = total_collecte

        dossier.reste_a_collecter = (
            dossier.montant_par_association *
            ContributionDecesAssociation.objects.filter(
                dossier=dossier
            ).count()
        ) - total_collecte

        dossier.save(update_fields=[
            "montant_collecte",
            "reste_a_collecter",
        ])

    class Meta:
        unique_together = ("dossier", "association")


    def __str__(self):
        return f"{self.association.entite.nom} - Décès #{self.dossier_id}"


class MessageContact(TimeStampedModel):
    nom = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    sujet = models.CharField(max_length=200, blank=True)
    message = models.TextField(blank=True)
    lu = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.nom} - {self.sujet}"


class PaiementAssociation(TimeStampedModel):
    MODE_PAIEMENT_CHOICES = [
        ("virement", "Virement"),
        ("cash", "Espèces"),
        ("cheque", "Chèque"),
        ("carte", "Carte bancaire"),
    ]

    association = models.ForeignKey(
        Association,
        on_delete=models.PROTECT,
        related_name="paiements"
    )
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    date_paiement = models.DateField(default=date.today)
    mode_paiement = models.CharField(max_length=20, choices=MODE_PAIEMENT_CHOICES, default="virement")
    reference = models.CharField(max_length=100, blank=True)
    commentaire = models.TextField(blank=True)
    montant_affecte = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    montant_avance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    enregistre_par = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="paiements_associations_enregistres"
    )

    def __str__(self):
        return f"{self.association} - {self.montant}"
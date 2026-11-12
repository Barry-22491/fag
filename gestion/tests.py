from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .emails import envoyer_email_historise, envoyer_notification_generation_cotisation
from .forms import InformationForm
from .models import (
    Adhesion,
    AffiliationAssociation,
    Association,
    BeneficiaireFederation,
    ContributionDecesAssociation,
    CotisationAssociationMensuelle,
    DossierRapatriement,
    Entite,
    HistoriqueEmail,
    Notification,
    PaiementAssociation,
    Personne,
    Role,
    UserEntiteRole,
)


class FederationFixturesMixin:
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="test-pass-123",
        )
        self.client.login(username="admin", password="test-pass-123")

        self.federation = Entite.objects.create(
            nom="FAG Test",
            type="federation",
            abreviation="FAG",
        )
        self.asso_entite = Entite.objects.create(
            nom="Association Test",
            type="association",
        )
        self.association = Association.objects.create(
            entite=self.asso_entite,
            federation=self.federation,
            ville="Dortmund",
            adresse="Rue 1",
            email="asso@example.com",
            date_creation=date(2020, 1, 1),
        )
        self.affiliation = AffiliationAssociation.objects.create(
            association=self.association,
            federation=self.federation,
            date_affiliation=date(2020, 2, 1),
            statut="active",
            montant_mensuel=Decimal("20.00"),
        )
        self.personne = Personne.objects.create(
            nom="Doe",
            prenom="John",
            email="john@example.com",
        )
        Adhesion.objects.create(
            personne=self.personne,
            association=self.association,
            statut="valide",
            role="president",
        )
        BeneficiaireFederation.objects.create(
            personne=self.personne,
            affiliation=self.affiliation,
            date_activation=date(2021, 1, 1),
            actif=True,
        )


class RapatriementCreateViewTests(FederationFixturesMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse("rapatriement_create")

    def test_invalid_post_does_not_create_or_fake_success(self):
        response = self.client.post(self.url, data={})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(DossierRapatriement.objects.count(), 0)
        self.assertContains(response, "Créer un dossier de rapatriement")

        message_texts = [str(m) for m in get_messages(response.wsgi_request)]
        self.assertFalse(
            any("Dossier créé avec succès" in text for text in message_texts)
        )

    def test_valid_post_with_zero_cost_does_not_crash(self):
        response = self.client.post(
            self.url,
            data={
                "personne": self.personne.pk,
                "affiliation": self.affiliation.pk,
                "date_deces": "2026-01-15",
                "lieu_deces": "Dortmund",
                "pays_deces": "Allemagne",
                "destination_rapatriement": "Conakry",
                "cout_total": "0",
                "personne_contact": "Jane",
                "telephone_contact": "123",
                "statut": "ouvert",
                "observations": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(DossierRapatriement.objects.count(), 1)
        dossier = DossierRapatriement.objects.get()
        self.assertEqual(dossier.cout_total, Decimal("0"))
        self.assertFalse(dossier.contributions_generees)


class PaiementAssociationTests(FederationFixturesMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.cotisation = CotisationAssociationMensuelle.objects.create(
            affiliation=self.affiliation,
            annee=2026,
            mois=1,
            montant_attendu=Decimal("20.00"),
            montant_paye=Decimal("0"),
            statut="en_attente",
        )
        self.url = reverse("paiement_association_create")

    def test_formulaire_preremplit_association_et_reste_du(self):
        response = self.client.get(
            self.url,
            {"association": self.association.pk},
        )

        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertEqual(form.initial.get("association"), self.association.pk)
        self.assertEqual(form.initial.get("mode_paiement"), "virement")
        self.assertEqual(form.initial.get("date_paiement"), date.today())
        self.assertEqual(form.initial.get("montant"), "20.00")
        self.assertContains(response, "situations-data")

    @patch("gestion.views.send_mail")
    def test_paiement_repartit_sur_cotisation(self, mock_send_mail):
        response = self.client.post(
            self.url,
            data={
                "association": self.association.pk,
                "montant": "20.00",
                "date_paiement": "2026-03-01",
                "mode_paiement": "virement",
                "reference": "VIR-1",
                "commentaire": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.cotisation.refresh_from_db()
        paiement = PaiementAssociation.objects.get()

        self.assertEqual(self.cotisation.statut, "paye")
        self.assertEqual(self.cotisation.montant_paye, Decimal("20.00"))
        self.assertEqual(paiement.montant_affecte, Decimal("20.00"))
        self.assertEqual(paiement.montant_avance, Decimal("0"))

    @patch("gestion.views.send_mail")
    def test_paiement_excedent_devient_avance(self, mock_send_mail):
        response = self.client.post(
            self.url,
            data={
                "association": self.association.pk,
                "montant": "50.00",
                "date_paiement": "2026-03-01",
                "mode_paiement": "virement",
                "reference": "",
                "commentaire": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.cotisation.refresh_from_db()
        paiement = PaiementAssociation.objects.get()

        self.assertEqual(self.cotisation.statut, "paye")
        self.assertEqual(paiement.montant_avance, Decimal("30.00"))
        self.assertEqual(paiement.montant_affecte, Decimal("20.00"))


class GenerationCotisationNotificationTests(FederationFixturesMixin, TestCase):
    def setUp(self):
        super().setUp()
        CotisationAssociationMensuelle.objects.create(
            affiliation=self.affiliation,
            annee=2026,
            mois=1,
            montant_attendu=Decimal("20.00"),
            montant_paye=Decimal("0"),
            statut="en_attente",
        )
        self.dossier = DossierRapatriement.objects.create(
            personne=self.personne,
            affiliation=self.affiliation,
            date_deces=date(2026, 2, 1),
            lieu_deces="Dortmund",
            pays_deces="Allemagne",
            destination_rapatriement="Conakry",
            cout_total=Decimal("400.00"),
            personne_contact="Jane",
            telephone_contact="123",
            statut="ouvert",
        )
        ContributionDecesAssociation.objects.create(
            dossier=self.dossier,
            association=self.association,
            montant_attendu=Decimal("200.00"),
            montant_paye=Decimal("0"),
            statut="en_attente",
        )
        role = Role.objects.create(nom="president_asso")
        UserEntiteRole.objects.create(
            user=self.user,
            entite=self.asso_entite,
            role=role,
        )
        self.url = reverse("generer_cotisations")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_generer_mois_notifie_association(self):
        response = self.client.post(
            self.url,
            data={"annee": "2026", "mois": "3"},
        )
        self.assertEqual(response.status_code, 302)

        cotisation = CotisationAssociationMensuelle.objects.get(
            affiliation=self.affiliation,
            annee=2026,
            mois=3,
        )
        self.assertEqual(cotisation.montant_attendu, Decimal("20.00"))

        hist = HistoriqueEmail.objects.filter(type_email="generation_cotisation")
        self.assertTrue(hist.exists())
        commentaire = hist.first().commentaire
        self.assertIn("Montant du mois", commentaire)
        self.assertIn("Retard mensuel", commentaire)
        self.assertIn("20,00", commentaire)
        self.assertIn("200,00", commentaire)

        notif = Notification.objects.filter(
            type_notification="cotisation",
            destinataire=self.user,
        ).first()
        self.assertIsNotNone(notif)
        self.assertIn("Retard", notif.message)
        self.assertIn("Décès", notif.message)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_situation_detaillee(self):
        cotisation = CotisationAssociationMensuelle.objects.create(
            affiliation=self.affiliation,
            annee=2026,
            mois=3,
            montant_attendu=Decimal("20.00"),
            montant_paye=Decimal("0"),
            statut="en_attente",
        )
        resultat = envoyer_notification_generation_cotisation(cotisation)
        situation = resultat["situation"]
        self.assertEqual(situation["montant_mensuel"], Decimal("20.00"))
        self.assertEqual(situation["retard_mensuel"], Decimal("20.00"))
        self.assertEqual(situation["montant_deces"], Decimal("200.00"))
        self.assertEqual(situation["total_a_regler"], Decimal("240.00"))
        self.assertTrue(resultat["email_ok"])


class AlertesPermissionTests(FederationFixturesMixin, TestCase):
    def test_alertes_forbidden_for_anonymous(self):
        self.client.logout()
        response = self.client.get(reverse("alertes_liste"))
        self.assertEqual(response.status_code, 302)

    def test_alertes_ok_for_superuser(self):
        response = self.client.get(reverse("alertes_liste"))
        self.assertEqual(response.status_code, 200)


class EmailHistoriseTests(TestCase):
    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_envoyer_email_historise_cree_historique(self):
        ok = envoyer_email_historise(
            sujet="Test",
            message="Hello",
            destinataires=["asso@example.com"],
            type_email="rappel_deces",
        )

        self.assertTrue(ok)
        hist = HistoriqueEmail.objects.get()
        self.assertEqual(hist.destinataire, "asso@example.com")
        self.assertTrue(hist.succes)
        self.assertEqual(hist.type_email, "rappel_deces")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_type_email_inconnu_devient_general(self):
        ok = envoyer_email_historise(
            sujet="Test",
            message="Hello",
            destinataires=["asso@example.com"],
            type_email="type_inexistant",
        )
        self.assertTrue(ok)
        self.assertEqual(HistoriqueEmail.objects.get().type_email, "general")


class InformationFormTests(TestCase):
    def test_champs_traduction_optionnels(self):
        federation = Entite.objects.create(nom="FAG", type="federation")
        form = InformationForm(
            data={
                "entite": federation.pk,
                "titre_fr": "Annonce",
                "contenu_fr": "Contenu",
                "titre_de": "",
                "contenu_de": "",
                "titre_en": "",
                "contenu_en": "",
                "type_information": "annonce",
                "priorite": "normale",
                "statut": "brouillon",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)


class MutatingActionsRequirePostTests(FederationFixturesMixin, TestCase):
    def test_adhesion_valider_refuse_get(self):
        adhesion = Adhesion.objects.create(
            personne=Personne.objects.create(nom="X", prenom="Y"),
            association=self.association,
            statut="en_attente",
        )
        response = self.client.get(reverse("adhesion_valider", args=[adhesion.pk]))
        self.assertEqual(response.status_code, 405)

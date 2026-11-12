from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .emails import (
    envoyer_confirmation_paiement,
    envoyer_email_historise,
    envoyer_notification_generation_cotisation,
    envoyer_rappel_cotisation,
)
from .forms import InformationForm
from .models import (
    ActiviteCulturelle,
    Adhesion,
    AffiliationAssociation,
    Association,
    BeneficiaireFederation,
    ContributionDecesAssociation,
    CotisationAssociationMensuelle,
    DossierRapatriement,
    Bureau,
    BureauMembre,
    Entite,
    HistoriqueEmail,
    Notification,
    PaiementAssociation,
    Personne,
    Poste,
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


class RappelEtConfirmationCotisationTests(FederationFixturesMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.cotisation = CotisationAssociationMensuelle.objects.create(
            affiliation=self.affiliation,
            annee=2026,
            mois=2,
            montant_attendu=Decimal("20.00"),
            montant_paye=Decimal("0"),
            statut="en_attente",
        )
        CotisationAssociationMensuelle.objects.create(
            affiliation=self.affiliation,
            annee=2026,
            mois=1,
            montant_attendu=Decimal("20.00"),
            montant_paye=Decimal("0"),
            statut="en_attente",
        )
        dossier = DossierRapatriement.objects.create(
            personne=self.personne,
            affiliation=self.affiliation,
            date_deces=date(2026, 1, 10),
            lieu_deces="Dortmund",
            pays_deces="Allemagne",
            destination_rapatriement="Conakry",
            cout_total=Decimal("400.00"),
            statut="ouvert",
        )
        ContributionDecesAssociation.objects.create(
            dossier=dossier,
            association=self.association,
            montant_attendu=Decimal("150.00"),
            montant_paye=Decimal("0"),
            statut="en_attente",
        )

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_rappel_detaille(self):
        ok = envoyer_rappel_cotisation(self.cotisation)
        self.assertTrue(ok)
        self.assertTrue(mail.outbox)
        body = mail.outbox[0].body
        self.assertIn("Rappel", mail.outbox[0].subject)
        self.assertIn("Retard mensuel", body)
        self.assertIn("150,00", body)
        self.assertIn("meilleurs délais", body)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_confirmation_detaillee(self):
        self.cotisation.montant_paye = Decimal("20.00")
        self.cotisation.statut = "paye"
        self.cotisation.date_paiement = date(2026, 2, 15)
        self.cotisation.save()

        ok = envoyer_confirmation_paiement(self.cotisation)
        self.assertTrue(ok)
        self.assertTrue(mail.outbox)
        body = mail.outbox[0].body
        self.assertIn("Confirmation", mail.outbox[0].subject)
        self.assertIn("Situation actualisée", body)
        self.assertIn("Retard mensuel", body)
        self.assertIn("150,00", body)


class ActiviteCreateTests(FederationFixturesMixin, TestCase):
    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_creation_enregistre_la_langue_et_notifie(self):
        response = self.client.post(
            reverse("activite_create"),
            data={
                "entite": self.federation.pk,
                "titre_fr": "Soirée culturelle",
                "description_fr": "Programme de la soirée",
                "titre_de": "Kulturabend",
                "description_de": "Abendprogramm",
                "titre_en": "",
                "description_en": "",
                "date": "2026-12-01T18:30",
                "lieu": "Dortmund",
                "capacite": "40",
                "reserve_aux_beneficiaires": "on",
                "est_public": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        activite = ActiviteCulturelle.objects.get()
        self.assertEqual(activite.titre_fr, "Soirée culturelle")
        self.assertEqual(activite.titre_de, "Kulturabend")
        self.assertEqual(activite.titre, "Soirée culturelle")
        self.assertEqual(activite.description_fr, "Programme de la soirée")
        self.assertTrue(activite.est_public)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Site public", mail.outbox[0].body)


class BureauExecutifTests(FederationFixturesMixin, TestCase):
    def test_membre_d_association_affiliee_peut_etre_elu(self):
        adhesion = Adhesion.objects.get(personne=self.personne)
        adhesion.role = "membre"
        adhesion.save()
        bureau = Bureau.objects.create(
            entite=self.federation,
            date_debut=date(2026, 1, 1),
        )
        poste = Poste.objects.create(nom="Secrétaire test", ordre=1)
        membre = BureauMembre(
            bureau=bureau,
            poste=poste,
            adhesion=adhesion,
        )
        membre.full_clean()
        membre.save()
        self.assertEqual(BureauMembre.objects.count(), 1)

    def test_association_non_affiliee_est_refusee(self):
        self.affiliation.statut = "suspendue"
        self.affiliation.save()
        adhesion = Adhesion.objects.get(personne=self.personne)
        bureau = Bureau.objects.create(
            entite=self.federation,
            date_debut=date(2026, 1, 1),
        )
        poste = Poste.objects.create(nom="Trésorier test", ordre=2)
        membre = BureauMembre(bureau=bureau, poste=poste, adhesion=adhesion)
        with self.assertRaises(ValidationError):
            membre.full_clean()


class InvitationMotDePasseTests(FederationFixturesMixin, TestCase):
    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_invitation_envoie_lien_pour_choisir_le_mot_de_passe(self):
        adhesion = Adhesion.objects.get(personne=self.personne)
        response = self.client.post(
            reverse("inviter_utilisateur"),
            data={"mode": "membre", "adhesion": adhesion.pk, "role_bureau": ""},
        )

        self.assertEqual(response.status_code, 302)
        self.personne.refresh_from_db()
        user = User.objects.get(email="john@example.com")
        self.assertEqual(self.personne.compte, user)
        self.assertTrue(user.has_usable_password())
        self.assertTrue(
            UserEntiteRole.objects.filter(
                user=user,
                entite=self.asso_entite,
                role__nom="association_president",
            ).exists()
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/accounts/reset/", mail.outbox[0].body)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_administrateur_sans_adhesion(self):
        response = self.client.post(
            reverse("inviter_utilisateur"),
            data={
                "mode": "administrateur",
                "prenom": "Awa",
                "nom": "Diallo",
                "email": "admin-fag@example.com",
            },
        )
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email="admin-fag@example.com")
        self.assertFalse(Personne.objects.filter(compte=user).exists())
        self.assertTrue(
            UserEntiteRole.objects.filter(
                user=user,
                entite=self.federation,
                role__nom="federation_direction",
            ).exists()
        )
        self.assertEqual(len(mail.outbox), 1)

    def test_pages_mot_de_passe_accessibles(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("password_reset")).status_code, 200)
        login = self.client.get(reverse("login"))
        self.assertContains(login, "Mot de passe oublié")

        self.client.login(username="admin", password="test-pass-123")
        self.assertEqual(self.client.get(reverse("password_change")).status_code, 200)

    def test_changement_mot_de_passe(self):
        response = self.client.post(
            reverse("password_change"),
            data={
                "old_password": "test-pass-123",
                "new_password1": "Nouveau-mot-de-passe-1",
                "new_password2": "Nouveau-mot-de-passe-1",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.client.logout()
        self.assertTrue(
            self.client.login(username="admin", password="Nouveau-mot-de-passe-1")
        )


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


class InformationPublicationEmailTests(FederationFixturesMixin, TestCase):
    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_information_publiee_notifie_les_associations(self):
        response = self.client.post(
            reverse("information_create"),
            data={
                "titre_fr": "Assemblée",
                "contenu_fr": "Rendez-vous samedi.",
                "titre_de": "Versammlung",
                "contenu_de": "Treffen am Samstag.",
                "titre_en": "",
                "contenu_en": "",
                "type_information": "convocation",
                "priorite": "importante",
                "statut": "publie",
                "envoyer_email": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.association.email, mail.outbox[0].to)
        self.assertIn("Assemblée", mail.outbox[0].body)
        self.assertIn("Versammlung", mail.outbox[0].body)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_brouillon_n_envoie_pas_d_email(self):
        response = self.client.post(
            reverse("information_create"),
            data={
                "titre_fr": "Brouillon",
                "contenu_fr": "Pas encore.",
                "titre_de": "",
                "contenu_de": "",
                "titre_en": "",
                "contenu_en": "",
                "type_information": "note",
                "priorite": "normale",
                "statut": "brouillon",
                "envoyer_email": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)


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

from django.urls import path # type: ignore
from . import views
from django.conf import settings # type: ignore
from django.conf.urls.static import static # type: ignore


urlpatterns = [
    # PUBLIC
    path('', views.public_home, name='public_home'),
    path('a-propos/', views.public_about, name='public_about'),
    path('public/associations/', views.public_associations, name='public_associations'),
    path('public/activites/', views.public_activites, name='public_activites'),
    path('public/informations/', views.public_informations, name='public_informations'),
    path('contact/', views.public_contact, name='public_contact'),

    # PRIVÉ
    path('dashboard/', views.dashboard, name='dashboard'),

    path('associations/', views.associations_liste, name='associations_liste'),
    path('associations/ajouter/', views.association_create, name='association_create'),
    path('associations/<int:pk>/', views.association_detail, name='association_detail'),
    path('associations/<int:pk>/modifier/', views.association_update, name='association_update'),
    path('associations/<int:pk>/supprimer/', views.association_delete, name='association_delete'),

    path('activites/', views.activites_liste, name='activites_liste'),
    path('activites/ajouter/', views.activite_create, name='activite_create'),
    path('activites/<int:pk>/', views.activite_detail, name='activite_detail'),

    path("informations/", views.informations_liste, name="informations_liste"),
    path("informations/ajouter/", views.information_create, name="information_create"),
    path("informations/<int:pk>/", views.information_detail, name="information_detail"),

    path('affiliations/', views.affiliations_liste, name='affiliations_liste'),
    path('affiliations/ajouter/', views.affiliation_create, name='affiliation_create'),
    path('affiliations/<int:pk>/modifier/', views.affiliation_update, name='affiliation_update'),

    path('personnes/', views.personnes_liste, name='personnes_liste'),
    path('personnes/ajouter/', views.personne_create, name='personne_create'),
    path('personnes/<int:pk>/', views.personne_detail, name='personne_detail'),
    path('personnes/<int:pk>/modifier/', views.personne_update, name='personne_update'),
    path('bureau/', views.bureau_liste, name='bureau_liste'),

    path("bureau/ajouter/", views.bureau_create, name="bureau_create"),
    path("bureau/membre/ajouter/", views.bureau_membre_create, name="bureau_membre_create"),
    path("bureau/postes/", views.postes_liste, name="postes_liste"),
    path("bureau/postes/ajouter/", views.poste_create, name="poste_create"),

    #pour valider les membres lorsqu'un president les ajoute
    path("membres/a-valider/", views.membres_a_valider, name="membres_a_valider"),
    path("adhesions/<int:pk>/valider/", views.adhesion_valider, name="adhesion_valider"),
    path("adhesions/<int:pk>/refuser/", views.adhesion_refuser, name="adhesion_refuser"),

    path('cotisations/', views.cotisations_liste, name='cotisations_liste'),
    path('cotisations/ajouter/', views.cotisation_create, name='cotisation_create'),
    path('cotisations/<int:pk>/', views.cotisation_detail, name='cotisation_detail'),
    path('cotisations/<int:pk>/modifier/', views.cotisation_update, name='cotisation_update'),
    path('cotisations/export/excel/', views.export_cotisations_excel, name='export_cotisations_excel'),
    path('cotisations/<int:pk>/pdf/', views.cotisation_pdf, name='cotisation_pdf'),
    path('cotisations/export/pdf/', views.export_cotisations_pdf, name='export_cotisations_pdf'),
    path('cotisations/generer/', views.generer_cotisations, name='generer_cotisations'),
    path('cotisations/<int:pk>/rappel/', views.envoyer_rappel_cotisation_view, name='envoyer_rappel_cotisation'),
    path('contributions-deces/<int:pk>/rappel/',views.envoyer_rappel_deces_view,name = 'envoyer_rappel_deces_view'),

    path('beneficiaires/', views.beneficiaires_liste, name='beneficiaires_liste'),
    path('beneficiaires/ajouter/', views.beneficiaire_create, name='beneficiaire_create'),
    path("beneficiaires/<int:pk>/toggle/",views.beneficiaire_toggle_actif,name="beneficiaire_toggle_actif"),

    path('rapatriements/', views.rapatriements_liste, name='rapatriements_liste'),
    path('rapatriements/ajouter/', views.rapatriement_create, name='rapatriement_create'),
    path('rapatriements/<int:pk>/', views.rapatriement_detail, name='rapatriement_detail'),

    path('transactions/', views.transactions_liste, name='transactions_liste'),
    path('transactions/ajouter/', views.transaction_create, name='transaction_create'),

    path('documents/', views.documents_liste, name='documents_liste'),
    path('documents/ajouter/', views.document_create, name='document_create'),
    path("documents/<int:pk>/<str:statut>/", views.document_update_statut, name="document_update_statut"),

    path("notifications/", views.notifications_liste, name="notifications_liste"),

    path('emails/', views.emails_liste, name='emails_liste'),
    path('rapports/', views.rapports, name='rapports'),
    path('alertes/', views.alertes_liste, name='alertes_liste'),

    path("cotisations-deces/", views.contributions_deces_liste, name="contributions_deces_liste"),
    path("cotisations-deces/<int:pk>/modifier/", views.contribution_deces_update, name="contribution_deces_update"),

    path("informations/ajouter/", views.information_create, name="information_create"),
    path("adhesions/ajouter/", views.adhesion_create, name="adhesion_create"),
    path("utilisateurs/inviter/", views.inviter_utilisateur, name="inviter_utilisateur"),

    path("personnes/export/excel/",views.export_personnes_excel,name="export_personnes_excel"),

    path("cotisations-deces/export/excel/",views.export_contributions_deces_excel,name="export_contributions_deces_excel"),

    path("cotisations-deces/export/pdf/",views.export_contributions_deces_pdf,name="export_contributions_deces_pdf"),

    path("paiements-associations/ajouter/",views.paiement_association_create,name="paiement_association_create"),

    path("cotisations/export/detail/excel/", views.export_cotisations_detail_excel, name="export_cotisations_detail_excel"),
    path("cotisations/export/detail/pdf/", views.export_cotisations_detail_pdf, name="export_cotisations_detail_pdf"),

    path("cotisations-deces/export/excel/", views.export_contributions_deces_excel, name="export_contributions_deces_excel"),
    path("cotisations-deces/export/pdf/", views.export_contributions_deces_pdf, name="export_contributions_deces_pdf"),

    path("personnes/export/excel/", views.export_personnes_excel, name="export_personnes_excel"),
    path("personnes/export/pdf/", views.export_personnes_pdf, name="export_personnes_pdf"),

    
]


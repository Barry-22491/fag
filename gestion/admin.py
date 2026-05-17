from django.contrib import admin
from .models import HistoriqueEmail
from .models import (
    Entite, Association, Personne, Adhesion, Bureau, Poste, BureauMembre,
    Evenement, Participation, Budget, LigneBudget, Transaction, Document,
    HistoriqueAdhesion, Role, UserEntiteRole, AffiliationAssociation,
    CotisationAssociationMensuelle, BeneficiaireFederation, ServiceFederation,
    PersonneService, DossierRapatriement, ActiviteCulturelle, ParticipationActivite,
    HistoriqueEmail,Information, Notification,ContributionDecesAssociation,MessageContact
)

"""une autre facon de stocker les entites dans une liste et de boucler pour eviter de repeter admin.site.register"""
"""
models_list = [
    Entite, Association, Personne, Adhesion, Bureau, Poste, BureauMembre,
    Evenement, Participation, Budget, LigneBudget, Transaction, Document,
    HistoriqueAdhesion, Role, UserEntiteRole, AffiliationAssociation,
    CotisationAssociationMensuelle, BeneficiaireFederation, ServiceFederation,
    PersonneService, DossierRapatriement, ActiviteCulturelle, ParticipationActivite
]

for model in models_list:
    admin.site.register(model)

"""



admin.site.register(Entite)
admin.site.register(Association)
admin.site.register(Personne)
admin.site.register(Adhesion)
admin.site.register(Bureau)
admin.site.register(Poste)
admin.site.register(BureauMembre)
admin.site.register(Evenement)
admin.site.register(Participation)
admin.site.register(Budget)
admin.site.register(LigneBudget)
admin.site.register(Transaction)
admin.site.register(Document)
admin.site.register(HistoriqueAdhesion)
admin.site.register(Role)
admin.site.register(UserEntiteRole)
admin.site.register(AffiliationAssociation)
admin.site.register(CotisationAssociationMensuelle)
admin.site.register(BeneficiaireFederation)
admin.site.register(ServiceFederation)
admin.site.register(PersonneService)
admin.site.register(DossierRapatriement)
admin.site.register(ActiviteCulturelle)
admin.site.register(ParticipationActivite)
admin.site.register(HistoriqueEmail)
admin.site.register(Information)
admin.site.register(Notification)
admin.site.register(ContributionDecesAssociation)

@admin.register(MessageContact)
class MessageContactAdmin(admin.ModelAdmin):
    list_display = ("nom", "email", "sujet", "lu", "created_at")
    list_filter = ("lu", "created_at")
    search_fields = ("nom", "email", "sujet", "message")
    readonly_fields = ("nom", "email", "sujet", "message", "created_at")




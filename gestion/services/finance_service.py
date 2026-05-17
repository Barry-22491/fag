from django.db.models import Sum
from gestion.models import Transaction

def calcul_solde(entites):
    qs = Transaction.objects.filter(entite__in=entites)

    recettes = qs.filter(type='recette').aggregate(
        total=Sum('montant')
    )['total'] or 0

    depenses = qs.filter(type='depense').aggregate(
        total=Sum('montant')
    )['total'] or 0

    return recettes - depenses
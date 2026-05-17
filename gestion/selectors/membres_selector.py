from fag.models import Adhesion

def get_membres(entites):
    return Adhesion.objects.filter(
        association__entite__in=entites
    ).select_related('personne', 'association')
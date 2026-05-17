from fag.models import UserEntiteRole

def user_has_access(user, entite):
    return UserEntiteRole.objects.filter(
        user=user,
        entite=entite
    ).exists()


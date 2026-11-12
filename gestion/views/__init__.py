"""
Vues de l'application gestion.

Organisation progressive :
- common.py  : helpers partagés (pagination)
- public.py  : site public
- legacy.py  : vues privées (à découper ensuite)
"""

from .common import MONTH_LABELS, paginate
from .public import (
    public_about,
    public_activites,
    public_associations,
    public_contact,
    public_home,
    public_informations,
)
from .legacy import *  # noqa: F403

# Les exports explicites écrasent les doublons éventuels de legacy
from .common import MONTH_LABELS, paginate  # noqa: F401
from .public import (  # noqa: F401
    public_about,
    public_activites,
    public_associations,
    public_contact,
    public_home,
    public_informations,
)

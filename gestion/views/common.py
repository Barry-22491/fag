from django.core.paginator import Paginator


MONTH_LABELS = {
    1: "Jan",
    2: "Fév",
    3: "Mar",
    4: "Avr",
    5: "Mai",
    6: "Juin",
    7: "Juil",
    8: "Août",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Déc",
}


def paginate(request, queryset, per_page=15):
    paginator = Paginator(queryset, per_page)
    return paginator.get_page(request.GET.get("page"))

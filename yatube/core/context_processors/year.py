import datetime


def year(request):
    """Добавляет переменную с текущим годом."""
    d = datetime.date.today()
    return {
        'year': d.year
    }

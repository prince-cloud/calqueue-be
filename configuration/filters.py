import django_filters
from .models import MainService, Service


class MainServiceFilter(django_filters.FilterSet):
    class Meta:
        model = MainService
        fields = ("is_active",)


class ServiceFilter(django_filters.FilterSet):
    class Meta:
        model = Service
        fields = ("is_active", "main_service")

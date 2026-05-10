import django_filters
from .models import Branch, Device, MainService, Service


class BranchFilter(django_filters.FilterSet):
    class Meta:
        model = Branch
        fields = ("is_active",)


class DeviceFilter(django_filters.FilterSet):
    class Meta:
        model = Device
        fields = ("is_active", "branch")


class MainServiceFilter(django_filters.FilterSet):
    class Meta:
        model = MainService
        fields = ("is_active",)


class ServiceFilter(django_filters.FilterSet):
    class Meta:
        model = Service
        fields = ("is_active", "main_service")

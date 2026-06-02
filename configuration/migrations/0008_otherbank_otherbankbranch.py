from django.db import migrations, models
import django.db.models.deletion
from uuid import uuid4


class Migration(migrations.Migration):

    dependencies = [
        ("configuration", "0007_restore_service_type_choices"),
    ]

    operations = [
        migrations.CreateModel(
            name="OtherBank",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=100)),
                ("code", models.CharField(max_length=20, unique=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["name"], "verbose_name": "Other Bank"},
        ),
        migrations.CreateModel(
            name="OtherBankBranch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=uuid4, editable=False, unique=True)),
                ("bank", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="branches", to="configuration.otherbank")),
                ("name", models.CharField(max_length=100)),
                ("code", models.CharField(blank=True, default="", max_length=20)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["bank", "name"], "verbose_name": "Other Bank Branch"},
        ),
        migrations.AlterUniqueTogether(
            name="otherbankbranch",
            unique_together={("bank", "code")},
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("configuration", "0004_systemvoiceconfig_branchtvconfig_branchvoiceconfig_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="service",
            name="prefix",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Ticket number prefix for this service (e.g. 'CD' → CD001). Leave blank to auto-derive.",
                max_length=6,
            ),
        ),
    ]

# Generated manually for Ticket + TicketService and optional deposit FKs.

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
        ("configuration", "0002_counter"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Ticket",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, unique=True
                    ),
                ),
                ("ticket_number", models.CharField(db_index=True, max_length=20)),
                ("phone_number", models.CharField(max_length=20)),
                ("id_number", models.CharField(max_length=50)),
                ("id_type", models.CharField(max_length=50)),
                (
                    "signature",
                    models.FileField(
                        blank=True, null=True, upload_to="ticket_signatures/"
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("WAITING", "Waiting"),
                            ("ON_GOING", "On going"),
                            ("ON_HOLD", "On hold"),
                            ("COMPLETED", "Completed"),
                            ("CANCELLED", "Cancelled"),
                            ("SKIPPED", "Skipped"),
                        ],
                        db_index=True,
                        default="WAITING",
                        max_length=20,
                    ),
                ),
                (
                    "hold_reason",
                    models.CharField(blank=True, max_length=300, null=True),
                ),
                (
                    "ticket_audio",
                    models.FileField(blank=True, null=True, upload_to="ticket_audio/"),
                ),
                (
                    "waiting_time",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Seconds from issue until called.",
                        null=True,
                    ),
                ),
                (
                    "called_time",
                    models.DateTimeField(
                        blank=True,
                        help_text="When the ticket was first called.",
                        null=True,
                    ),
                ),
                (
                    "start_serve_time",
                    models.DateTimeField(
                        blank=True,
                        help_text="When serving started at the counter.",
                        null=True,
                    ),
                ),
                (
                    "served_time",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Seconds from start of serve until completed (optional).",
                        null=True,
                    ),
                ),
                (
                    "total_time_spent",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Seconds from issue until visit completed (optional).",
                        null=True,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "assigned_to",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="tickets_assigned",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "branch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="tickets",
                        to="configuration.branch",
                    ),
                ),
                (
                    "counter",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="tickets_served",
                        to="configuration.counter",
                    ),
                ),
                (
                    "device",
                    models.ForeignKey(
                        help_text="Kiosk / device that issued the ticket.",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="tickets_created",
                        to="configuration.device",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="TicketService",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, unique=True
                    ),
                ),
                (
                    "position",
                    models.PositiveSmallIntegerField(
                        default=0,
                        help_text="Order of services as requested (0 = first).",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "service",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="ticket_services",
                        to="configuration.service",
                    ),
                ),
                (
                    "ticket",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ticket_services",
                        to="core.ticket",
                    ),
                ),
            ],
            options={
                "ordering": ["ticket", "position", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="ticket",
            constraint=models.UniqueConstraint(
                fields=("branch", "ticket_number"),
                name="core_ticket_branch_ticket_number_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="ticketservice",
            constraint=models.UniqueConstraint(
                fields=("ticket", "position"),
                name="core_ticketservice_ticket_position_uniq",
            ),
        ),
        migrations.AddField(
            model_name="cashdeposit",
            name="ticket",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="cash_deposits",
                to="core.ticket",
            ),
        ),
        migrations.AddField(
            model_name="chequedeposit",
            name="ticket",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="cheque_deposits",
                to="core.ticket",
            ),
        ),
        migrations.AddField(
            model_name="ezwichdeposit",
            name="ticket",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="ezwich_deposits",
                to="core.ticket",
            ),
        ),
        migrations.AddField(
            model_name="mobilemoneydeposit",
            name="ticket",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="mobile_money_deposits",
                to="core.ticket",
            ),
        ),
    ]

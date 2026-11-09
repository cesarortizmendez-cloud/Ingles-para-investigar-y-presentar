from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="plan_start",
            field=models.DateField(blank=True, help_text="Día 1 del plan. Puede cambiarla si quiere reiniciar el calendario.",
                                   null=True, verbose_name="Inicio del plan intensivo de 40 días"),
        ),
        migrations.AddField(
            model_name="profile",
            name="daily_minutes",
            field=models.PositiveIntegerField(default=120, verbose_name="Minutos diarios para el plan"),
        ),
    ]

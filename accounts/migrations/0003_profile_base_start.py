from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_profile_plan"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="base_start",
            field=models.DateField(blank=True, help_text="Día 1 del plan base (preparatorio). Puede hacerse antes o en paralelo al de 40 días.",
                                   null=True, verbose_name="Inicio del plan base de 20 días"),
        ),
    ]

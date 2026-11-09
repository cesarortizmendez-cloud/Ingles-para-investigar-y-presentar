from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("curriculum", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="contentpackage",
            name="kind",
            field=models.CharField(choices=[("chapter", "Capítulo"), ("diagnostic", "Diagnóstico"), ("day", "Día del plan 40")],
                                   max_length=12),
        ),
    ]

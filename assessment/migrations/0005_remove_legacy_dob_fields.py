from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('assessment', '0004_birth_year_fields'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='patientprofile',
            name='dob',
        ),
        migrations.RemoveField(
            model_name='assessmentsession',
            name='dob',
        ),
    ]

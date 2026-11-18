from django.db import migrations, models


def populate_birth_year(apps, schema_editor):
    PatientProfile = apps.get_model('assessment', 'PatientProfile')
    AssessmentSession = apps.get_model('assessment', 'AssessmentSession')
    for model in (PatientProfile, AssessmentSession):
        for record in model.objects.exclude(dob__isnull=True):
            model.objects.filter(pk=record.pk).update(birth_year=record.dob.year)


class Migration(migrations.Migration):
    dependencies = [
        ('assessment', '0003_alter_assessmentsession_status_patientprofile_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='patientprofile',
            name='birth_year',
            field=models.PositiveSmallIntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='assessmentsession',
            name='birth_year',
            field=models.PositiveSmallIntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.RunPython(populate_birth_year, migrations.RunPython.noop),
    ]

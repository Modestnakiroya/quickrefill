from django.db import migrations, models


def populate_unique_emails(apps, schema_editor):
    User = apps.get_model('core', 'User')
    used = set()
    for user in User.objects.all().order_by('pk'):
        email = (user.email or '').strip().lower()
        if not email or email in used:
            email = f'account-{user.pk}@quickrefill.invalid'
            while email in used:
                email = f'account-{user.pk}-{len(used)}@quickrefill.invalid'
            User.objects.filter(pk=user.pk).update(email=email)
        used.add(email)


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(populate_unique_emails, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(max_length=254, unique=True),
        ),
    ]

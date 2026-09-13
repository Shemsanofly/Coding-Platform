from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_user_experience_level"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="profile_image",
            field=models.ImageField(
                blank=True,
                help_text="Optional profile photo shown in the app.",
                null=True,
                upload_to="profile_images/%Y/%m/",
            ),
        ),
    ]

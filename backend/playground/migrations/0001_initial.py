from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0003_user_profile_image"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlaygroundChallenge",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField()),
                (
                    "difficulty",
                    models.CharField(
                        choices=[
                            ("beginner", "Beginner"),
                            ("intermediate", "Intermediate"),
                            ("advanced", "Advanced"),
                        ],
                        default="beginner",
                        max_length=16,
                    ),
                ),
                ("starter_code", models.TextField()),
                ("test_cases", models.JSONField(default=list)),
                ("xp_reward", models.PositiveIntegerField(default=50)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("solved", "Solved"),
                            ("abandoned", "Abandoned"),
                        ],
                        db_index=True,
                        default="active",
                        max_length=16,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("solved_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="playground_challenges",
                        to="accounts.user",
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
        migrations.CreateModel(
            name="PlaygroundSubmission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.TextField()),
                ("passed", models.BooleanField(default=False)),
                ("test_results", models.JSONField(default=list)),
                ("xp_earned", models.PositiveIntegerField(default=0)),
                ("submitted_at", models.DateTimeField(auto_now_add=True)),
                (
                    "challenge",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="submissions",
                        to="playground.playgroundchallenge",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="playground_submissions",
                        to="accounts.user",
                    ),
                ),
            ],
            options={
                "ordering": ("-submitted_at",),
            },
        ),
        migrations.AddIndex(
            model_name="playgroundchallenge",
            index=models.Index(fields=["user", "status"], name="playground__user_id_7a8b2d_idx"),
        ),
    ]

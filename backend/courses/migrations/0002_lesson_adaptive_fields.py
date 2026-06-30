# Adaptive lesson shell: separate resource metadata from stored text.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="course",
            options={
                "ordering": ("-created_at",),
                "verbose_name": "course",
                "verbose_name_plural": "courses",
            },
        ),
        migrations.AlterField(
            model_name="course",
            name="created_by",
            field=models.ForeignKey(
                db_index=True,
                on_delete=django.db.models.deletion.PROTECT,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterModelOptions(
            name="coursesource",
            options={
                "ordering": ("pk",),
                "verbose_name": "course source",
                "verbose_name_plural": "course sources",
            },
        ),
        migrations.AlterField(
            model_name="coursesource",
            name="course",
            field=models.ForeignKey(
                db_index=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="sources",
                to="courses.course",
            ),
        ),
        migrations.AlterModelOptions(
            name="lesson",
            options={
                "ordering": ("order", "pk"),
                "verbose_name": "lesson",
                "verbose_name_plural": "lessons",
            },
        ),
        migrations.AlterField(
            model_name="lesson",
            name="content",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="lesson",
            name="course",
            field=models.ForeignKey(
                db_index=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="lessons",
                to="courses.course",
            ),
        ),
        migrations.AddField(
            model_name="lesson",
            name="source_type",
            field=models.CharField(
                choices=[
                    ("internal", "Internal"),
                    ("w3schools", "W3Schools"),
                    ("freecodecamp", "FreeCodeCamp"),
                    ("youtube", "YouTube"),
                    ("mdn", "MDN"),
                    ("geeksforgeeks", "GeeksforGeeks"),
                    ("official_documentation", "Official Documentation"),
                    ("internal_pdf", "Internal PDF"),
                    ("coding_exercise", "Coding Exercise"),
                    ("project", "Project-Based Lesson"),
                ],
                default="internal",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="lesson",
            name="resource_url",
            field=models.URLField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="lesson",
            name="difficulty",
            field=models.CharField(
                choices=[
                    ("beginner", "Beginner"),
                    ("intermediate", "Intermediate"),
                    ("advanced", "Advanced"),
                ],
                default="beginner",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="lesson",
            name="estimated_minutes",
            field=models.PositiveSmallIntegerField(default=15),
        ),
        migrations.AddField(
            model_name="lesson",
            name="tags",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="lesson",
            name="learning_objective",
            field=models.TextField(blank=True),
        ),
    ]

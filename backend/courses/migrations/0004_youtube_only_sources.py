from django.db import migrations, models


def migrate_to_youtube_only(apps, schema_editor):
    Lesson = apps.get_model("courses", "Lesson")
    CourseSource = apps.get_model("courses", "CourseSource")
    Lesson.objects.exclude(source_type="youtube").update(source_type="youtube")
    CourseSource.objects.exclude(source_type="youtube").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("courses", "0003_lesson_source_refresh"),
    ]

    operations = [
        migrations.RunPython(migrate_to_youtube_only, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="coursesource",
            name="source_type",
            field=models.CharField(
                choices=[("youtube", "YouTube")],
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="lesson",
            name="source_type",
            field=models.CharField(
                choices=[("youtube", "YouTube")],
                default="youtube",
                max_length=32,
            ),
        ),
    ]

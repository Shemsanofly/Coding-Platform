# Generated manually — remap deprecated lesson sources and expand choices.

from django.db import migrations, models


def remap_lesson_sources(apps, schema_editor):
    Lesson = apps.get_model("courses", "Lesson")
    Lesson.objects.filter(source_type="w3schools").update(source_type="freecodecamp")
    Lesson.objects.filter(source_type="mdn").update(source_type="official_documentation")
    Lesson.objects.filter(source_type="internal_pdf").update(source_type="internal")


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0002_lesson_adaptive_fields"),
    ]

    operations = [
        migrations.RunPython(remap_lesson_sources, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="lesson",
            name="source_type",
            field=models.CharField(
                choices=[
                    ("internal", "Internal"),
                    ("freecodecamp", "FreeCodeCamp"),
                    ("youtube", "YouTube"),
                    ("geeksforgeeks", "GeeksforGeeks"),
                    ("official_documentation", "Official Documentation"),
                    ("khan_academy", "Khan Academy"),
                    ("codecademy", "Codecademy"),
                    ("coursera", "Coursera"),
                    ("edx", "edX"),
                    ("coding_exercise", "Coding Exercise"),
                    ("project", "Project-Based Lesson"),
                ],
                default="internal",
                max_length=32,
            ),
        ),
    ]

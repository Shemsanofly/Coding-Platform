from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0005_lesson_pdf_notes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="coursesource",
            name="source_type",
            field=models.CharField(
                choices=[
                    ("youtube", "YouTube"),
                    ("pdf", "PDF"),
                    ("webpage", "Web page"),
                    ("link", "External link"),
                    ("internal", "Platform content"),
                ],
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="lesson",
            name="source_type",
            field=models.CharField(
                choices=[
                    ("youtube", "YouTube"),
                    ("pdf", "PDF"),
                    ("webpage", "Web page"),
                    ("link", "External link"),
                    ("internal", "Platform content"),
                ],
                default="youtube",
                max_length=32,
            ),
        ),
    ]

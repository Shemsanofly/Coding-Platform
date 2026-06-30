from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("progress", "0002_lessonprogress"),
    ]

    operations = [
        migrations.AlterField(
            model_name="lessonprogress",
            name="completed_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Official completion: quiz passed plus engagement thresholds (time / scroll / video).",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="lessonprogress",
            name="seconds_engaged",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Cumulative active study seconds reported by the client.",
            ),
        ),
        migrations.AddField(
            model_name="lessonprogress",
            name="max_scroll_depth_pct",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text="Maximum scroll depth observed for inline content (0–100).",
            ),
        ),
        migrations.AddField(
            model_name="lessonprogress",
            name="video_watch_pct",
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text="YouTube or tracked video completion estimate (0–100).",
                null=True,
            ),
        ),
    ]

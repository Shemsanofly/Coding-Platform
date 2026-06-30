from django.db.models.signals import post_save
from django.dispatch import receiver

from courses.models import Course


@receiver(post_save, sender=Course)
def course_post_save_fetch_content(sender, instance, **kwargs):
    # Source scraping is disabled for the current MVP flow.
    return

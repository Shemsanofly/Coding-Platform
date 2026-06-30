from django.contrib import admin

from ai_engine.models import LessonAIProcessing, Recommendation, WeakTopic


@admin.register(LessonAIProcessing)
class LessonAIProcessingAdmin(admin.ModelAdmin):
    list_display = ("lesson", "status", "updated_at")
    list_filter = ("status",)
    search_fields = ("lesson__title",)


admin.site.register(WeakTopic)
admin.site.register(Recommendation)

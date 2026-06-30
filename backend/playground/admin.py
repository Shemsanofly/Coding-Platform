from django.contrib import admin

from playground.models import PlaygroundChallenge, PlaygroundSubmission


@admin.register(PlaygroundChallenge)
class PlaygroundChallengeAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "difficulty", "status", "xp_reward", "created_at", "solved_at")
    list_filter = ("status", "difficulty")
    search_fields = ("title", "user__email")


@admin.register(PlaygroundSubmission)
class PlaygroundSubmissionAdmin(admin.ModelAdmin):
    list_display = ("challenge", "user", "passed", "xp_earned", "submitted_at")
    list_filter = ("passed",)

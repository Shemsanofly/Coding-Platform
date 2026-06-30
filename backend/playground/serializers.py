from rest_framework import serializers

from playground.models import PlaygroundChallenge, PlaygroundSubmission


class PlaygroundChallengeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlaygroundChallenge
        fields = (
            "id",
            "title",
            "description",
            "difficulty",
            "starter_code",
            "xp_reward",
            "status",
            "created_at",
            "solved_at",
        )
        read_only_fields = fields


class PlaygroundSubmissionResultSerializer(serializers.Serializer):
    passed = serializers.BooleanField()
    xp_earned = serializers.IntegerField()
    test_results = serializers.ListField(child=serializers.DictField())
    challenge = PlaygroundChallengeSerializer()
    message = serializers.CharField()


class PlaygroundWeeklyActivitySerializer(serializers.Serializer):
    label = serializers.CharField()
    date = serializers.CharField()
    attempts = serializers.IntegerField()
    height_pct = serializers.IntegerField()


class PlaygroundLeaderboardEntrySerializer(serializers.Serializer):
    rank = serializers.IntegerField(required=False, allow_null=True)
    user_id = serializers.IntegerField()
    display_name = serializers.CharField()
    learning_level = serializers.CharField(allow_null=True, required=False)
    practice_xp = serializers.IntegerField()
    challenges_solved = serializers.IntegerField()
    total_submissions = serializers.IntegerField()
    pass_rate = serializers.FloatField()
    streak_days = serializers.IntegerField()
    tier_title = serializers.CharField()
    tier_icon = serializers.CharField()
    tier_progress_pct = serializers.IntegerField()
    next_tier_title = serializers.CharField(allow_null=True, required=False)
    next_tier_xp = serializers.IntegerField(allow_null=True, required=False)
    weekly_activity = PlaygroundWeeklyActivitySerializer(many=True, required=False)


class PlaygroundLeaderboardSerializer(serializers.Serializer):
    leaderboard = PlaygroundLeaderboardEntrySerializer(many=True)
    total_students = serializers.IntegerField()
    me = PlaygroundLeaderboardEntrySerializer(allow_null=True)

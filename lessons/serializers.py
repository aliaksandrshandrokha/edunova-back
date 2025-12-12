from rest_framework import serializers
from .models import Lesson


class LessonGenerateSerializer(serializers.Serializer):
    """Input serializer for lesson generation request."""
    topic = serializers.CharField(max_length=255)
    subject = serializers.CharField(max_length=255)
    grade_level = serializers.CharField(max_length=50)
    duration_minutes = serializers.IntegerField(min_value=1)

    def validate_duration_minutes(self, value):
        """Ensure duration is positive."""
        if value <= 0:
            raise serializers.ValidationError("Duration must be a positive number.")
        return value


class LessonSerializer(serializers.ModelSerializer):
    """Serializer for Lesson model."""
    user = serializers.StringRelatedField(read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)

    class Meta:
        model = Lesson
        fields = [
            'id',
            'user',
            'user_id',
            'topic',
            'subject',
            'grade_level',
            'duration_minutes',
            'description',
            'content',
            'activities',
            'questions',
            'summary',
            'image_urls',
            'video_links',
            'is_public',
            'slug',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['slug', 'created_at', 'updated_at', 'user', 'user_id']

    def validate_activities(self, value):
        """Ensure activities is a list."""
        if not isinstance(value, list):
            raise serializers.ValidationError("Activities must be a list.")
        return value

    def validate_questions(self, value):
        """Ensure questions is a list."""
        if not isinstance(value, list):
            raise serializers.ValidationError("Questions must be a list.")
        return value

    def validate_image_urls(self, value):
        """Ensure image_urls is a list."""
        if not isinstance(value, list):
            raise serializers.ValidationError("Image URLs must be a list.")
        return value

    def validate_video_links(self, value):
        """Ensure video_links is a list."""
        if not isinstance(value, list):
            raise serializers.ValidationError("Video links must be a list.")
        return value

    def validate_duration_minutes(self, value):
        """Ensure duration is positive."""
        if value <= 0:
            raise serializers.ValidationError("Duration must be a positive number.")
        return value

    def create(self, validated_data):
        """Create lesson and set user from request."""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class LessonPublicSerializer(serializers.ModelSerializer):
    """Serializer for public lesson view (read-only, limited fields)."""
    user = serializers.StringRelatedField(read_only=True)
    creator_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Lesson
        fields = [
            'id',
            'user',
            'creator_email',
            'topic',
            'subject',
            'grade_level',
            'duration_minutes',
            'description',
            'content',
            'activities',
            'questions',
            'summary',
            'image_urls',
            'video_links',
            'slug',
            'created_at',
        ]
        read_only_fields = fields


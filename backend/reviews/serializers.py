from rest_framework import serializers

from .models import Comment


class CommentSerializer(serializers.ModelSerializer):
    """Public shape of a comment: the author's name only, never their email."""

    customerName = serializers.CharField(source="user.name", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "customerName", "text", "approved", "createdAt"]
        read_only_fields = fields


class CreateCommentSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=2000)


class RatingSerializer(serializers.Serializer):
    """1-5 stars (req 5). Ratings are live at once, no approval needed."""

    score = serializers.IntegerField(min_value=1, max_value=5)

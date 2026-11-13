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

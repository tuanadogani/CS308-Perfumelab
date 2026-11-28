from rest_framework import serializers

from .models import Comment


class CommentSerializer(serializers.ModelSerializer):
    """Public shape of a comment: the author's name only, never their email."""

    customerName = serializers.CharField(source="user.name", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    rating = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ["id", "customerName", "rating", "text", "approved", "createdAt"]
        read_only_fields = fields

    def get_rating(self, comment):
        """The author's stars for this product, shown next to their name (None if not rated)."""
        return getattr(comment, "author_rating", None)


class OwnCommentSerializer(serializers.ModelSerializer):
    """A comment as its author sees it while it waits for approval."""

    createdAt = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "text", "createdAt"]
        read_only_fields = fields


class CreateCommentSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=2000)


class RatingSerializer(serializers.Serializer):
    """1-5 stars (req 5). Ratings are live at once, no approval needed."""

    score = serializers.IntegerField(min_value=1, max_value=5)

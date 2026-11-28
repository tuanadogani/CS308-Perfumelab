from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsCustomer
from catalog.models import Product

from .models import Comment, Rating
from .serializers import CommentSerializer, CreateCommentSerializer, OwnCommentSerializer, RatingSerializer
from .services import (
    edit_comment, has_received, pending_comments, submit_comment, submit_rating, visible_comments,
)


class ProductCommentsView(APIView):
    """GET: approved comments, visible to everyone. POST: a customer comments on a delivered product (req 5)."""

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsCustomer()]

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk, active=True)
        comments = visible_comments(product).select_related("user")
        return Response(CommentSerializer(comments, many=True).data)

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk, active=True)
        serializer = CreateCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            comment = submit_comment(request.user, product, serializer.validated_data["text"])
        except ValidationError as exc:
            return Response({"message": " ".join(exc.messages)}, status=400)
        # New comments stay hidden until a product manager approves them.
        return Response(CommentSerializer(comment).data, status=201)


class ProductRatingView(APIView):
    """GET: the customer's own rating and whether they may review. PUT: give or change a 1-5 star rating (req 5).

    `canReview` is true once the product was delivered to this customer, so the page can hide
    the review form from everyone else instead of letting them type and then refusing it.
    """

    permission_classes = [IsCustomer]

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk, active=True)
        rating = Rating.objects.filter(user=request.user, product=product).first()
        pending = pending_comments(request.user, product)
        return Response({
            "score": rating.score if rating else None,
            "canReview": has_received(request.user, product),
            "pendingComments": OwnCommentSerializer(pending, many=True).data,
        })

    def put(self, request, pk):
        product = get_object_or_404(Product, pk=pk, active=True)
        serializer = RatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            rating = submit_rating(request.user, product, serializer.validated_data["score"])
        except ValidationError as exc:
            return Response({"message": " ".join(exc.messages)}, status=400)
        return Response({"score": rating.score})


class OwnCommentView(APIView):
    """PATCH /api/comments/<id>/ {text}: the author edits a comment that is still pending (req 5).

    Someone else's comment is a 404; an approved or rejected comment is a 400.
    """

    permission_classes = [IsCustomer]

    def patch(self, request, pk):
        serializer = CreateCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            comment = edit_comment(request.user, pk, serializer.validated_data["text"])
        except Comment.DoesNotExist:
            return Response({"message": "Comment not found."}, status=404)
        except ValidationError as exc:
            return Response({"message": " ".join(exc.messages)}, status=400)
        return Response(OwnCommentSerializer(comment).data)

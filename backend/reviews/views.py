from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsCustomer
from catalog.models import Product

from .models import Rating
from .serializers import CommentSerializer, CreateCommentSerializer, RatingSerializer
from .services import submit_comment, submit_rating, visible_comments


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
    """GET: the customer's own rating for this product. PUT: give or change a 1-5 star rating (req 5)."""

    permission_classes = [IsCustomer]

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk, active=True)
        rating = Rating.objects.filter(user=request.user, product=product).first()
        return Response({"score": rating.score if rating else None})

    def put(self, request, pk):
        product = get_object_or_404(Product, pk=pk, active=True)
        serializer = RatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            rating = submit_rating(request.user, product, serializer.validated_data["score"])
        except ValidationError as exc:
            return Response({"message": " ".join(exc.messages)}, status=400)
        return Response({"score": rating.score})

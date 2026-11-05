from rest_framework import serializers
from django.db import IntegrityError, transaction
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from .serializers import RegisterSerializer, UserSerializer


class AuthThrottle(AnonRateThrottle):
    rate = "10/min"


class LoginSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"] = serializers.EmailField()

    def validate(self, attrs):
        attrs["email"] = attrs["email"].strip().lower()
        return super().validate(attrs)


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    throttle_classes = [AuthThrottle]


class RefreshView(TokenRefreshView):
    throttle_classes = [AuthThrottle]


class MeView(APIView):
    def get(self, request):
        user = request.user
        return Response(UserSerializer(user).data)


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [AuthThrottle]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                user = serializer.save()
        except IntegrityError:
            return Response({"message": "This email is already registered."}, status=400)
        refresh = RefreshToken.for_user(user)
        return Response({"user": UserSerializer(user).data,
                         "access": str(refresh.access_token), "refresh": str(refresh)}, status=201)


class LogoutView(APIView):
    def post(self, request):
        serializer = serializers.Serializer(data=request.data)
        serializer.fields["refresh"] = serializers.CharField()
        serializer.is_valid(raise_exception=True)
        try:
            token = RefreshToken(serializer.validated_data["refresh"])
            if str(token["user_id"]) != str(request.user.pk):
                return Response({"message": "Invalid refresh token."}, status=400)
            token.blacklist()
        except TokenError:
            return Response({"message": "Invalid refresh token."}, status=400)
        return Response(status=204)

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    taxId = serializers.CharField(source="tax_id", required=True)
    homeAddress = serializers.CharField(source="home_address", required=True)

    class Meta:
        model = User
        fields = ["id", "name", "email", "role", "taxId", "homeAddress"]
        read_only_fields = ["id", "role"]


class RegisterSerializer(UserSerializer):
    password = serializers.CharField(write_only=True)
    name = serializers.CharField(max_length=150)
    taxId = serializers.RegexField(r"^\d{10,11}$", source="tax_id")

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ["password"]

    def validate_name(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Full name must be at least 2 characters.")
        return value.strip()

    def validate_homeAddress(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Please enter your full address.")
        return value.strip()

    def validate_email(self, value):
        value = User.objects.normalize_email(value)
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    def validate(self, attrs):
        try:
            validate_password(attrs["password"], User(**{k: v for k, v in attrs.items() if k != "password"}))
        except ValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

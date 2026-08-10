from rest_framework import serializers
from .models import User

class UserSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'password', 'phone_number',
            'national_id', 'county', 'town', 'postal_code',
            'employment_type', 'monthly_income',
        ]

    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError('Phone number already in use.')
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Email already in use.')
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    phone = serializers.CharField(
        source='phone_number',
        read_only=True
    )

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'phone_number',
            'phone',
            'national_id',
            'county',
            'town',
            'postal_code',
            'employment_type',
            'monthly_income',
            'balance',
            'loan_limit',
            'loan_used',
            'profile_photo',
            'id_photo',
            'selfie_photo',
        ]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username
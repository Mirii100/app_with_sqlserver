from rest_framework import serializers
from .models import User, SecuritySettings

class UserSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'password', 'phone_number',
            'full_name', 'national_id', 'county', 'town', 'postal_code',
            'employment_type', 'monthly_income',
            'account_number',
        ]
        read_only_fields = ['account_number',]

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

class UserSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(
        source='phone_number',
        read_only=True
    )
    biometric_enabled = serializers.SerializerMethodField()

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
            'loan_wallet_balance',
            'chama_wallet_balance',
            'goal_wallet_balance',
            'loan_limit',
            'loan_used',
            'points',
            'profile_photo',
            'id_photo',
            'selfie_photo',
            'biometric_enabled',
            'account_number',
            'referral_code',
        ]
        read_only_fields = [
            'account_number', 'balance',
            'loan_wallet_balance', 'chama_wallet_balance', 'goal_wallet_balance',
            'loan_limit', 'loan_used', 'points',
        ]

    def get_biometric_enabled(self, obj):
        try:
            return obj.security_settings.biometric_enabled
        except SecuritySettings.DoesNotExist:
            return False

    def update(self, instance, validated_data):
        biometric_enabled = validated_data.pop('biometric_enabled', None)
        instance = super().update(instance, validated_data)
        if biometric_enabled is not None:
            security_settings, created = SecuritySettings.objects.get_or_create(user=instance)
            security_settings.biometric_enabled = biometric_enabled
            security_settings.save()
        return instance

class SecuritySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecuritySettings
        fields = '__all__'
        read_only_fields = ['user', 'pin_hash', 'last_pin_changed']

    def validate(self, data):
        pin = data.get('pin')
        if pin is not None:
            from django.contrib.auth.hashers import make_password
            if pin == '':
                data['pin'] = None
            else:
                data['pin_hash'] = make_password(str(pin))
            data.pop('pin', None)
        elif 'biometric_enabled' in data and 'pin' not in data:
            pass
        return data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data.pop('pin_hash', None)
        data.pop('last_pin_changed', None)
        return data

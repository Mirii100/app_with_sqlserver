from rest_framework import serializers
from .models import Account, CreditCard, DebitCard, UserCardSettings


class AccountSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()
    available_balance = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = '__all__'
        read_only_fields = ['balance', 'available_balance']

    def get_balance(self, obj):
        """Always reflect the User's balance — single source of truth."""
        return obj.user.balance

    def get_available_balance(self, obj):
        """Always reflect the User's balance — single source of truth."""
        return obj.user.balance


class CreditCardSerializer(serializers.ModelSerializer):
    """Serializer for Credit Card model."""

    last_four = serializers.SerializerMethodField()
    first_four = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    mask_card_number = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    available_balance = serializers.SerializerMethodField()

    class Meta:
        model = CreditCard
        fields = [
            'id', 'user', 'account_number', 'card_type', 'cardholder_name',
            'reason_for_applying', 'card_number', 'last_four', 'first_four',
            'expiry_date', 'cvv', 'status', 'spend_limit', 'created_at',
            'is_expired', 'mask_card_number', 'balance', 'available_balance'
        ]
        read_only_fields = [
            'card_number', 'last_four', 'first_four', 'is_expired',
            'mask_card_number', 'created_at', 'updated_at', 'account_number',
            'expiry_date', 'cvv', 'balance', 'available_balance',
        ]

    def get_last_four(self, obj):
        return obj.last_four

    def get_first_four(self, obj):
        return obj.first_four

    def get_is_expired(self, obj):
        """Return whether the card is expired."""
        return obj.is_expired()

    def get_mask_card_number(self, obj):
        """Return masked card number for display."""
        return obj.mask_card_number()

    def get_balance(self, obj):
        """Return the user's account balance."""
        return obj.user.account.balance

    def get_available_balance(self, obj):
        """Return the user's available account balance."""
        return obj.user.account.available_balance


class DebitCardSerializer(serializers.ModelSerializer):
    """Serializer for Debit Card model."""

    last_four = serializers.SerializerMethodField()
    first_four = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    mask_card_number = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    available_balance = serializers.SerializerMethodField()

    class Meta:
        model = DebitCard
        fields = [
            'id', 'user', 'account_number', 'card_type', 'cardholder_name',
            'reason_for_applying', 'card_number', 'last_four', 'first_four',
            'expiry_date', 'cvv', 'status', 'spend_limit', 'is_contactless',
            'created_at', 'is_expired', 'mask_card_number', 'balance', 'available_balance'
        ]
        read_only_fields = [
            'card_number', 'last_four', 'first_four', 'is_expired',
            'mask_card_number', 'created_at', 'updated_at', 'account_number',
            'expiry_date', 'cvv', 'balance', 'available_balance',
        ]

    def get_last_four(self, obj):
        return obj.last_four

    def get_first_four(self, obj):
        return obj.first_four

    def get_is_expired(self, obj):
        """Return whether the card is expired."""
        return obj.is_expired()

    def get_mask_card_number(self, obj):
        """Return masked card number for display."""
        return obj.mask_card_number()

    def get_balance(self, obj):
        """Return the user's account balance."""
        return obj.user.account.balance

    def get_available_balance(self, obj):
        """Return the user's available account balance."""
        return obj.user.account.available_balance


class UserCardSettingsSerializer(serializers.ModelSerializer):
    """Serializer for User Card Settings."""

    active_credit_cards_count = serializers.SerializerMethodField()
    active_debit_cards_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserCardSettings
        fields = [
            'id', 'default_credit_card', 'default_debit_card',
            'online_payments_enabled', 'contactless_enabled',
            'sms_notifications', 'email_notifications',
            'total_daily_spend_limit', 'low_spend_alert',
            'active_credit_cards_count', 'active_debit_cards_count'
        ]
        read_only_fields = ['active_credit_cards_count', 'active_debit_cards_count']

    def get_active_credit_cards_count(self, obj):
        """Count active credit cards."""
        return obj.active_credit_cards.count()

    def get_active_debit_cards_count(self, obj):
        """Count active debit cards."""
        return obj.active_debit_cards.count()

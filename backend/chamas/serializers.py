from rest_framework import serializers
from .models import Chama, ChamaMembership

class ChamaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chama
        fields = '__all__'

class ChamaMembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChamaMembership
        fields = '__all__'

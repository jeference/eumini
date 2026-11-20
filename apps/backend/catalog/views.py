from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog import pricing, serializers
from common.permissions import IsPublic


class ProductListView(APIView):
    authentication_classes: list = []
    permission_classes = [IsPublic]

    @extend_schema(responses=serializers.ProductSerializer(many=True), auth=[])
    def get(self, request):
        return Response(serializers.ProductSerializer(pricing.catalog(), many=True).data)

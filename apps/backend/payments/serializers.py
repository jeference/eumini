from common.serializers import GlobalIdSerializer
from payments.models import Charge


class ChargeSerializer(GlobalIdSerializer):
    class Meta:
        model = Charge
        fields = [
            "id",
            "method",
            "status",
            "amount_cents",
            "pix_br_code",
            "pix_qr_base64",
            "card_brand",
            "card_last_four",
            "expires_at",
            "paid_at",
        ]
        read_only_fields = fields

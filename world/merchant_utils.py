# world/merchant_utils.py
from typing import Dict, Any
from world.campaign import Merchant, MerchantItem, MerchantRelationship

def compute_price(
    item: MerchantItem,
    merchant: Merchant,
    rel: MerchantRelationship,
    context: Dict[str, Any]
) -> int:
    """Compute dynamic price based on personality, relationship, and context."""
    price = item.base_price
    # Personality factors
    price *= (1 + merchant.personality.greed * 0.05)
    # Relationship axes
    price *= (1 - rel.affinity * 0.03)
    price *= (1 - rel.trust * 0.02)
    price *= (1 + rel.fear * 0.04)
    # Context modifiers
    if context.get('desperate'):
        price *= 1.25
    if context.get('scarcity'):
        price *= 1.1
    # Clamp by merchant constraints
    max_price = item.base_price * (1 + merchant.constraints.max_markup)
    min_price = item.base_price * (1 - merchant.constraints.max_discount)
    return max(min_price, min(price, max_price))
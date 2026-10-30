# tests/test_activation_token.py — Jeton d'activation à usage unique
"""
Vérifie les trois propriétés de sécurité du jeton d'activation (section 6.4.A) :
1. il ne fonctionne qu'UNE SEULE fois ;
2. un jeton expiré est refusé ;
3. seul le hash est stocké (jamais le jeton en clair).
"""
from datetime import timedelta

from app.models import ActivationToken, utcnow


def test_token_usage_unique():
    obj, clair = ActivationToken.create_for_agent("demo-101")
    assert obj.verify(clair) is True
    obj.consume()
    # Après consommation, le même jeton est refusé.
    assert obj.verify(clair) is False


def test_token_expire_refuse():
    obj, clair = ActivationToken.create_for_agent("demo-101", ttl_hours=48)
    # On simule un jeton expiré en plaçant sa date d'expiration dans le passé.
    obj.expire_le = utcnow() - timedelta(hours=1)
    assert obj.verify(clair) is False


def test_seul_le_hash_est_stocke():
    obj, clair = ActivationToken.create_for_agent("demo-101")
    # L'objet ne contient que le hash (64 caractères hex), pas le jeton en clair.
    assert obj.token_hash == ActivationToken.hash_token(clair)
    assert obj.token_hash != clair
    assert len(obj.token_hash) == 64
    # Aucun attribut de l'objet ne doit contenir le jeton en clair.
    for valeur in obj.__dict__.values():
        assert clair not in str(valeur)

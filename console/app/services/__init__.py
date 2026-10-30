# app/services/__init__.py — Couche de services (logique métier)
"""
Les services contiennent la logique métier SÉPARÉE des routeurs HTTP.
Avantage : ils sont testables unitairement (pytest) sans serveur HTTP,
avec des clients Keycloak/Synapse simulés.
"""

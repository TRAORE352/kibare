# Tests d'intégration — Kibaré

Ces tests s'exécutent contre la plateforme **démarrée** (`docker compose up -d`).
Ils complètent les tests unitaires de la Console (`console/tests/`, 13 tests).

## Épreuves à automatiser (section 12 du brief)

1. **Intrus** : la connexion du compte `intrus` est refusée (il n'existe pas
   dans Keycloak) ; la tentative d'inscription est refusée (`enable_registration: false`).
2. **Serveur ne lit rien** : envoyer un message test chiffré entre deux agents
   puis lancer `scripts/verif_serveur_ne_lit_rien.sh`.
3. **Révocation** : révoquer `demo-203` → ses jetons ne fonctionnent plus
   (`M_UNKNOWN_TOKEN`).

## Contrainte : connexion OIDC uniquement

Synapse est configuré `password_config.enabled: false` (connexion uniquement via
Keycloak). Les clients de test Matrix classiques (`matrix-nio`, `matrix-commander`)
se connectent par mot de passe et ne gèrent pas nativement le flux OIDC navigateur.

**Deux approches possibles :**

- **A. Instance de test dédiée** : pour les tests automatisés uniquement, lancer
  une seconde instance Synapse avec `password_config.enabled: true` et des comptes
  de test à mot de passe, puis vérifier le chiffrement (E2EE) avec
  `matrix-nio[e2e]` (Apache-2.0). Le code de production reste OIDC-only.
- **B. Manuel** : démontrer ces épreuves en direct avec l'application (c'est le
  parcours du jury). Les scripts `verif_serveur_ne_lit_rien.sh` restent
  automatisables après un envoi manuel.

## Exemple (approche A, skeleton)

```python
# tests/integration/test_e2e.py  (à exécuter contre une instance de test)
import asyncio
from nio import AsyncClient, LoginResponse, RoomCreateResponse

async def test_deux_agents_echangent_chiffre():
    # 1. connexion de deux comptes de test (mot de passe, instance de test)
    # 2. création d'un salon chiffré
    # 3. envoi d'un message « MESSAGE-TEST-JURY-123 »
    # 4. vérification qu'il est reçu et déchiffré par l'autre appareil
    ...
```

Dépendance (hors production, test uniquement) : `matrix-nio[e2e]` (Apache-2.0,
https://github.com/matrix-nio/matrix-nio).

## Lancement

```bash
./scripts/run_tests.sh          # tests unitaires + verif_serveur_ne_lit_rien
# puis, sur l'instance de test :
python tests/integration/test_e2e.py
```

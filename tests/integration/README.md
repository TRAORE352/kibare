# Tests d'intégration — Kibaré

Ces tests automatisent les **épreuves du jury** (sections 12 et 17 du brief) :

| Épreuve | Ce qui est vérifié |
|---|---|
| **Intrus** | le compte non enrôlé ne peut ni se connecter ni s'inscrire |
| **Le serveur ne lit rien** | un message réellement chiffré est introuvable en clair dans la base et les journaux |
| **Révocation** | après révocation, le jeton est rejeté et la reconnexion impossible |

## Lancement

```bash
./scripts/run_tests.sh        # tout : tests unitaires + épreuves du jury
```

ou séparément :

```bash
python3 tests/integration/instance_test.py        # démarre l'instance de test
python3 tests/integration/test_epreuves_jury.py   # joue les 3 épreuves
```

**Résultat attendu : 16/16 vérifications réussies.**

## Dépendances (tests uniquement, jamais en production)

```bash
apt-get install -y libolm-dev
pip install matrix-synapse "matrix-nio[e2e]" aiohttp
```

| Bibliothèque | Licence | Lien |
|---|---|---|
| matrix-nio | ISC | https://github.com/matrix-nio/matrix-nio |
| python-olm (libolm) | Apache-2.0 | https://gitlab.matrix.org/matrix-org/olm |
| aiohttp | Apache-2.0 | https://github.com/aio-libs/aiohttp |

## Pourquoi une instance de TEST séparée

En production, Synapse est configuré `password_config.enabled: false` : la
connexion passe **uniquement** par Keycloak (OIDC + OTP). C'est voulu — sans
cela, un mot de passe Synapse permettrait de contourner l'enrôlement et l'OTP.

Mais les clients Matrix automatisés (matrix-nio) se connectent par mot de passe :
ils ne savent pas dérouler un flux OIDC, qui exige un navigateur.

`instance_test.py` fabrique donc une instance **jetable**, identique à la
production sauf sur deux points, tous deux documentés dans le fichier :

1. la connexion par mot de passe y est autorisée ;
2. les limites anti-force-brute sont relevées (sinon le test, qui enchaîne
   plusieurs connexions en quelques secondes, se bloque lui-même et reçoit un
   HTTP 429 qu'il prendrait à tort pour un échec du produit).

Tout le reste est identique : chiffrement imposé pour tous les salons,
fédération coupée, aperçus de liens coupés, inscription désactivée. **La
configuration de production n'est jamais modifiée.**

Le chiffrement utilisé est le **vrai** chiffrement Matrix (Olm/Megolm) fourni
par matrix-nio. Aucune ligne de cryptographie n'est écrite par l'équipe
(règle éliminatoire, section 2 du brief).

## Ce que ces tests prouvent vraiment

Un test qui ne peut jamais échouer ne prouve rien. Ces épreuves ont donc été
soumises à un **test de mutation** : on a volontairement cassé le chiffrement
(serveur sans `encryption_enabled_by_default_for_room_type` et salon créé sans
chiffrement), puis relancé la série.

Résultat de la mutation : **11/16**, avec ces échecs précis —

```
[FAIL] Salon créé avec chiffrement Megolm activé
[FAIL] Message test INTROUVABLE dans event_json (1 occurrence(s))
[FAIL] Aucun événement m.room.message en clair (1)
[FAIL] Les messages sont stockés comme m.room.encrypted (0)
```

Le test a donc **réellement trouvé le message en clair** dans la base quand le
chiffrement était coupé, et n'en trouve aucun quand il est actif. C'est ce qui
fait la différence entre une vérification et une décoration.

### Garde-fou contre un faux vert

La vérification « le message est introuvable » réussit aussi… quand la base est
vide. C'est arrivé pendant la mise au point : un ancien Synapse occupait encore
le port, le nouveau ne démarrait pas, et les tests lisaient une base vide en
affichant du vert partout.

Deux protections ont été ajoutées :

- `instance_test.py` libère le port avant de démarrer et vérifie qu'il l'est ;
- `test_epreuves_jury.py` compte d'abord les événements en base et s'arrête si
  elle est vide, au lieu de conclure à tort que rien n'est en clair.

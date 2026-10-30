# NOTES_HERMES.md — Journal de travail de l'agent

Ce journal consigne les décisions techniques, les écarts avec le brief, les
vérifications effectuées et les points à confirmer par l'équipe. Il est écrit
en français simple pour que chaque membre puisse le relire avant l'épreuve
« explication du code ».

---

## Environnement de travail de l'agent (à lire en premier)

- L'agent tourne dans un conteneur Linux **sans démon Docker** (pas de socket
  Docker, pas de capacité `SYS_ADMIN`). Il est donc **impossible de lancer
  `docker compose up` ici**.
- Conséquence : les configs ont été **vérifiées en natif** (Synapse et Keycloak
  lancés directement), mais le `docker compose up -d` final devra être exécuté
  **sur la machine Docker de l'équipe**.
- Tout ce qui est vérifiable sans Docker a été vérifié réellement (voir plus bas).

## Versions figées (vérifiées comme « stables actuelles » le 30 octobre 2026)

| Composant | Version figée | Vérifiée comment |
|---|---|---|
| Synapse | `matrixdotorg/synapse:v1.164.1` | dernière release GitHub ; config validée par `generate-keys` |
| Keycloak | `quay.io/keycloak/keycloak:26.8.1` | dernière release LTS ; realm importé et testé en natif |
| Caddy | `caddy:2.11.7-alpine` | dernière release GitHub |
| PostgreSQL | `postgres:17.11-alpine` | tag Docker Hub vérifié |

## Corrections apportées à la session précédente (29 octobre)

La session précédente avait écrit des options de configuration **qui n'existent
pas** dans Synapse 1.164.1. Elles auraient empêché Synapse de démarrer.
Corrections (vérifiées dans la documentation officielle de Synapse 1.164.1) :

- `client_secret_file` → **`client_secret_path`** (OIDC).
- `macaroon_secret_key_file` → supprimé (Synapse génère ce secret tout seul).
- `password_file` (base) → **`password`** (la base PostgreSQL n'a pas de variante
  fichier ; le mot de passe est injecté dans le `homeserver.yaml` généré).
- `database` (nom de base) → **`dbname`** (argument psycopg2).
- `email: {enabled: false}` → supprimé (n'existe pas ; l'e-mail est désactivé
  par défaut tant qu'aucun SMTP n'est configuré).
- `experimental_features: {msc3881_enabled, msc3916_enabled}` → supprimé
  (ces flags expérimentaux n'existent plus).
- `trusted_third_party_id_servers` → supprimé (option inexistante) ; remplacé
  par `trusted_key_servers: []`.
- `rc_messages_per_second` / `rc_messages_burst_count` → **`rc_message: {per_second, burst_count}`**.
- `max_message_size` → supprimé (inexistant).
- Listener Synapse : retiré `federation` de `resources` (fédération coupée).

## Corrections importantes de sécurité / OIDC

1. **Callback OIDC** : le chemin correct de Synapse est
   `/_synapse/client/oidc/callback` (pas `/_synapse/oidc/callback`).
2. **`enable_registration: false` + `allow_existing_users: true`** dans le
   provider OIDC : seuls les comptes Matrix **pré-créés par la Console** peuvent
   se connecter. Un compte Keycloak valide mais non enrôlé est refusé.
3. **Scopes clients Keycloak** : la première version du realm référençait des
   scopes (`openid`, `profile`) avant leur création → ils étaient ignorés et le
   client `synapse` n'avait pas le scope `profile` (le mapping `preferred_username`
   aurait échoué). Corrigé en laissant Keycloak créer ses scopes par défaut.
4. **Adresse canonique unique** : l'adresse IP (`KIBARE_SERVER_ADDRESS`) est
   l'hôte HTTP canonique partout (Caddy, Keycloak `KC_HOSTNAME`, issuer OIDC,
   `public_baseurl` Synapse). `kibare.test` reste uniquement le `server_name`
   Matrix (identifiant stable des comptes `@matricule:kibare.test`). Cela évite
   le problème d'« issuer » quand le téléphone se connecte par IP.

## Vérifications réellement effectuées (avec commandes)

1. **init.sh** : `KIBARE_SERVER_ADDRESS=192.168.10.10 ./scripts/init.sh` génère
   la CA, le certificat serveur (SAN : IP + kibare.test + kibare.lan), les 8
   secrets, `homeserver.yaml` et `realm-kibare.json`. → OK.
2. **Config Synapse** : validée par
   `python -m synapse.app.homeserver --config-path ... --generate-keys` (exit 0,
   aucune option inconnue). → OK.
3. **Realm Keycloak** : importé avec `kc.sh start-dev --import-realm` (Keycloak
   26.8.1). 10 utilisateurs, 3 rôles, 3 clients, action requise `CONFIGURE_TOTP`
   sur tous. Scopes `profile`/`email`/`roles` bien assignés au client `synapse`. → OK.
4. **OIDC** : l'endpoint d'autorisation répond 200 avec la page de connexion
   pour le client `synapse` (redirect URI correct). → OK.

## Ce qui reste à vérifier sur la machine Docker de l'équipe

- `docker compose up -d` complet (Caddy + Postgres + Synapse + Keycloak).
- La **confiance CA** de Synapse vers Keycloak en HTTPS (le montage de la CA +
  `update-ca-certificates` est en place, mais à confirmer une fois en Docker).
- Le flux de connexion complet (matricule + mot de passe + OTP) sur téléphone.
- La création du compte technique `@kibare-bot` (voir `scripts/demo_seed.sh`).

## Écarts avec le brief (assumés)

- Le brief mentionne `homeserver.yaml.template` : c'est bien un **modèle** commité,
  et `init.sh` génère `homeserver.yaml` (ignoré par Git). Idem pour le realm.
- Le brief suggère `init.sh` appelé par un conteneur d'init ; nous gardons les
  **deux commandes** (`./scripts/init.sh` puis `docker compose up -d`), plus simple
  et expliqué dans le README.

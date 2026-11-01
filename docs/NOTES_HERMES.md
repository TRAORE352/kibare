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

## Déploiement réel sur la machine de l'équipe (30 octobre) — CORRECTIONS

Le `docker compose up -d` sur la machine Docker de l'équipe a révélé et permis de
corriger les points suivants (tous commités) :

1. **`python-qrcode[pil]` → `qrcode[pil]`** : le paquet PyPI s'appelle `qrcode`
   (le dépôt GitHub s'appelle `python-qrcode`). Sinon le build de l'image Console échoue.
2. **Synapse `command` → `entrypoint`** : l'image `matrixdotorg/synapse` a un
   ENTRYPOINT `/start.py` qui rejetait « sh » (`Unknown execution mode 'sh'`).
3. **Keycloak `KC_*_FILE` non reconnu** : remplacé par `KC_DB_PASSWORD` et
   `KC_BOOTSTRAP_ADMIN_PASSWORD` via `${VAR}` depuis `.env` (init.sh les écrit).
4. **Console `KEYCLOAK_INTERNAL_URL` avec préfixe `/auth`** (404 sinon).
5. **`internal: true` retiré** : bloquait la publication des ports 80/443 par Caddy
   sous Docker Desktop.
6. **Caddy** : HTTP/3 désactivé (port UDP 443 non publié), site `:443` (catch-all)
   au lieu de l'IP (connexion par IP = pas de SNI + NAT Docker), et
   `redir * /console/ 302` (la forme `redir /x 302` = legacy « from→to »).
7. **Certificat serveur `keyUsage` = `digitalSignature, keyEncipherment`**
   (sinon `ERR_SSL_KEY_USAGE_INCOMPATIBLE`).
8. **Realm Keycloak réimporté** avec la bonne IP (il faut supprimer la base
   `keycloak` de PostgreSQL, pas seulement le volume, car le realm vit dans Postgres).
9. **Peuplement de la table `agents` de la Console** (`services/seed.py`) : les
   comptes de démo sont définis dans Keycloak mais la Console a sa propre table.
10. **Flux OIDC manuel** (httpx) + **cookie signé** (itsdangerous) : le cookie de
    session Starlette n'était pas renvoyé via Keycloak (boucle `ERR_TOO_MANY_REDIRECTS`),
    et l'endpoint `userinfo` renvoyait 401 → on lit `preferred_username` dans l'`id_token`.

**État final : la plateforme serveur + Console est FONCTIONNELLE de bout en bout**
(HTTPS, OIDC, OTP, autorisation, tableau des agents).

En lançant Synapse 1.164.1 (sqlite) et Keycloak 26.8.1 **directement** (sans
Docker), j'ai vérifié la chaîne serveur de bout en bout :

1. **OIDC Synapse ↔ Keycloak** : au démarrage, Synapse a téléchargé la
   découverte (`openid-configuration: 200`) et les clés JWKS (`certs: 200`). → OK.
2. **Création du bot** (`@kibare-bot`) via l'API d'enregistrement avec HMAC-SHA1
   + secret partagé (même construction que `register_new_matrix_user`). → OK.
3. **Création des comptes** Matrix (admin API `PUT /_synapse/admin/v2/users/...`). → OK.
4. **Création des salons** (client API `POST /_matrix/client/v3/createRoom`) avec
   état `m.room.encryption = m.megolm.v1.aes-sha2`, `join_rule = invite`,
   `history_visibility = joined`. → OK (vérifié dans l'état du salon).
5. **Désactivation** (révocation) `POST /_synapse/admin/v1/deactivate/@demo-203:kibare.test`
   → `id_server_unbind_result: success`. → OK.

**Écart corrigé pendant ces tests** : la création de salon ne passe PAS par
`POST /_synapse/admin/v1/rooms` (inexistant) mais par l'API client
`POST /_matrix/client/v3/createRoom`. C'est corrigé dans `scripts/demo_seed.py`.

**Reste à vérifier sur la machine Docker de l'équipe** :
- `docker compose up -d` (orchestration complète) ;
- l'échange chiffré réel entre deux clients (nécessite un client Matrix E2EE,
  ex. matrix-nio, pour les tests d'intégration) ;
- le flux de connexion navigateur complet (matricule + mot de passe + OTP).

## Fork Android — lots terminés (1er novembre)

Trois lots de modifications ont été ajoutés au fork (détail dans
`docs/ANDROID_FORK.md`) :

1. **Liens externes coupés** : partage de position, cartes MapTiler,
   statistiques PostHog, rapports de plantage Sentry, signalement de bogue
   « rageshake », annuaire public de salons, Jitsi, passerelles UnifiedPush
   publiques, liens d'aide element.io, et la publicité pour « Element X ».
2. **Métadonnées** : accusés de lecture en `m.read.private`, indicateur
   « en train d'écrire » désactivé, notifications réduites à « Nouveau message »
   (ni texte, ni expéditeur, ni salon, ni image, ni avatars).
3. **Chiffrement** : `enableEncryption()` inconditionnel à la création de salon ;
   l'interrupteur de l'écran de création devient un texte non modifiable.

### Deux défauts trouvés et corrigés dans le livrable précédent

1. **Le patch ne transportait pas ses fichiers binaires.** Il avait été généré
   sans `--binary` : `git apply` échouait sur les 10 PNG d'icône et les 2
   polices TTF (`cannot apply binary patch … without full index line`). Qui
   appliquait le patch sur un clone neuf n'obtenait ni l'icône Kibaré ni IBM
   Plex Sans. Corrigé : le patch est désormais généré avec
   `git diff --cached --binary`, et la procédure est écrite dans
   `docs/ANDROID_FORK.md` (§10).
2. **Import orphelin dans `TimelineFragment.kt`.** La suppression de
   « Ouvrir avec… » avait laissé `import …safeStartActivity` inutilisé. Le
   projet compile avec `allWarningsAsErrors = true` : cet import seul suffisait
   à casser la compilation. Corrigé.

### Pièges évités pendant ces lots

- **`findPreference(...)!!` sur une préférence supprimée = plantage.** Retirer
  la catégorie « rageshake » du XML des réglages aurait fait planter l'écran des
  réglages avancés, car `VectorSettingsAdvancedSettingsFragment` la cherchait
  avec `!!`. La fonction `setupRageShakeSection()` a donc été vidée en même temps.
- **L'icône d'Element est vectorielle, pas un PNG.** C'est une « icône
  adaptative » : remplacer seulement les PNG `mipmap-*` n'aurait rien changé sur
  Android 8 et plus. C'est `drawable-anydpi-v26/ic_launcher_foreground.xml` qui
  fait foi ; les PNG ne servent que de repli pour Android 5 à 7.
- **`allWarningsAsErrors = true`** : tout import ou paramètre de constructeur
  devenu inutilisé casse la compilation. Après chaque suppression de code, les
  imports ont été revérifiés automatiquement.

### Contrôles réellement exécutés (sans Docker, sans Android SDK)

- `git apply --check` puis `git apply` du patch sur un **clone neuf**
  d'element-android : les deux passent sans erreur.
- Les 2 polices TTF relues après application : « IBM Plex Sans » Regular et Bold
  reconnues ; les 12 binaires ont la **même empreinte SHA-256** qu'à la source.
- Les 10 icônes PNG régénérées, contrôlées à l'œil : le « K » est net, centré,
  non rogné, lisible jusqu'en 48 px.
- Les 17 fichiers XML modifiés parsent sans erreur.
- Script de contrôle sur tous les `.kt` modifiés : aucun import inutilisé,
  accolades équilibrées.

**Limite honnête** : aucune compilation Gradle n'a pu être lancée (ni JDK ni
Android SDK dans le conteneur de l'agent). Les contrôles ci-dessus sont
statiques — ils ne remplacent pas un `assembleFdroidRelease` vert, qui reste à
faire sur la machine de build de l'équipe.

## Épreuves du jury automatisées (1er novembre)

Les trois épreuves de la section 12 du brief tournent désormais pour de vrai :
`./scripts/run_tests.sh` → **13 tests unitaires + 16 vérifications d'épreuve**.

| Épreuve | Vérifications |
|---|---|
| Intrus | connexion refusée, inscription libre refusée |
| Le serveur ne lit rien | message chiffré envoyé ET déchiffré, introuvable en base, aucun `m.room.message` en clair, stocké en `m.room.encrypted`, absent des journaux |
| Révocation | jeton valide avant, `M_UNKNOWN_TOKEN` après, sans `soft_logout`, reconnexion impossible |

Le chiffrement employé est le **vrai** Olm/Megolm, via `matrix-nio[e2e]`
(ISC / Apache-2.0). Aucune ligne de cryptographie n'est écrite par l'équipe.

### Pourquoi une instance Synapse de test séparée

La production est **OIDC-seulement** (`password_config.enabled: false`), ce qui
est voulu : un mot de passe Synapse contournerait l'enrôlement et l'OTP. Or un
client automatisé ne sait pas dérouler un flux OIDC, qui demande un navigateur.

`tests/integration/instance_test.py` crée donc une instance jetable, identique à
la production **sauf** la connexion par mot de passe et les limites de débit.
La configuration de production n'est jamais modifiée.

### Ces tests ont été éprouvés par mutation

Un test toujours vert ne prouve rien. En cassant volontairement le chiffrement,
la série tombe à **11/16** et le test **trouve le message en clair dans la base**
(`1 occurrence`). Avec le chiffrement actif : `0 occurrence`. La vérification
distingue donc réellement les deux situations.

### Deux pièges rencontrés, corrigés

1. **Le test se bloquait lui-même.** En enchaînant plusieurs connexions, il
   déclenchait la protection anti-force-brute de Synapse, recevait un HTTP 429
   et interprétait ce refus comme un échec du produit. Les limites sont relevées
   dans l'instance de test uniquement ; la protection reste active en production.
2. **Un faux vert sur l'épreuve éliminatoire.** Un ancien Synapse occupait le
   port, le nouveau ne démarrait pas, et les tests lisaient une base vide : « le
   message est introuvable » passait au vert sans rien prouver. Désormais
   l'instance libère le port avant de démarrer, et le test compte les événements
   en base avant de conclure quoi que ce soit.

### Détail technique utile pour la soutenance

Le premier essai échouait sur « le destinataire déchiffre bien le message ».
Cause réelle : les clients n'avaient pas **publié** leurs clés d'appareil
(`keys_upload`). Le serveur ne connaissait donc aucun appareil, l'envoyeur
n'avait personne à qui remettre la clé de session Megolm, et le destinataire
recevait un message indéchiffrable. C'est exactement le mécanisme qui protège
Kibaré : **la clé de session n'est remise qu'aux appareils connus et vérifiés au
moment de l'envoi**. Un appareil qui apparaît après coup — par exemple celui
d'un agent révoqué puis réactivé — ne reçoit jamais les anciennes clés.

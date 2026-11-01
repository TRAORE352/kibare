# Kibaré — Messagerie souveraine de l'administration

## Concept
Kibaré est une messagerie instantanée souveraine pour l'administration burkinabè, hébergée sur l'infrastructure de l'État, sans aucune dépendance à des services tiers. Elle garantit le chiffrement de bout en bout (Matrix/Olm-Megolm), une identité vérifiée par enrôlement administratif avec OTP obligatoire, une révocation immédiate, et des protections « Zéro fuite » (blocage des captures d'écran, filigrane nominatif, interdiction de copie et de partage externe, effacement à distance).

## Architecture
```
Réseau local (Wi-Fi / réseau de l'État) — Aucune connexion Internet nécessaire

┌──────────────────────┐     HTTPS (CA locale)      ┌──────────────────────────────────────┐
│  Téléphone Android   │ ─────────────────────────▶ │  Serveur (docker compose)            │
│  App « Kibaré »      │                             │  ┌────────┐                         │
│  (fork Element       │                             │  │ Caddy  │ Reverse proxy, HTTPS    │
│   Android, F-Droid)  │                             │  └───┬────┘ (CA locale)            │
└──────────────────────┘                             │      │                               │
                                                     │      ├──▶ Synapse (Matrix)          │
┌──────────────────────┐                             │      ├──▶ Keycloak (identité, OTP)  │
│ Navigateur admin     │ ─────────────────────────▶ │      ├──▶ Console Kibaré (FastAPI)  │
│ Console Kibaré       │                             │      └──▶ Element Web (optionnel)   │
└──────────────────────┘                             │                                    │
                                                     │  PostgreSQL (Synapse + Keycloak)   │
                                                     └────────────────────────────────────┘
```

## Technologies et licences

| Composant | Licence | Lien |
|-----------|---------|------|
| Synapse | AGPL-3.0 | https://github.com/element-hq/synapse |
| Element Android (Element Classic) | AGPL-3.0 | https://github.com/element-hq/element-android |
| Element Web (optionnel) | AGPL-3.0 | https://github.com/element-hq/element-web |
| Matrix Olm/Megolm (vodozemac) | Apache-2.0 | https://github.com/matrix-org/vodozemac |
| Keycloak | Apache-2.0 | https://github.com/keycloak/keycloak |
| PostgreSQL | PostgreSQL License | https://www.postgresql.org |
| Caddy | Apache-2.0 | https://github.com/caddyserver/caddy |
| FastAPI | MIT | https://github.com/fastapi/fastapi |
| Authlib | BSD-3-Clause | https://github.com/lepture/authlib |
| python-qrcode | BSD | https://github.com/lincolnloop/python-qrcode |
| FreeOTP | Apache-2.0 | https://github.com/freeotp |
| Aegis | GPL-3.0 | https://github.com/beemdevelopment/Aegis |
| IBM Plex Sans | SIL OFL 1.1 | https://github.com/IBM/plex |

Licence du projet : **AGPL-3.0** (obligatoire, car nous modifions Element Android et Synapse sous AGPL-3.0). Voir `LICENSE`.

Niveau d'engagement open source : **« Étendre et adapter »** (à partir d'Element Android et Synapse).

## Installation
**Prérequis** : Docker, Docker Compose, 8 Go de RAM minimum.

```bash
./scripts/init.sh      # Génère configs, CA locale, certificats, secrets de démo (une seule fois)
docker compose up -d   # Démarre toute la plateforme
```

Puis sur un téléphone Android :
1. Installer l'APK Kibaré ([page de téléchargement](../../releases/latest)).
   Le certificat de l'autorité Kibaré est **embarqué dans l'application** :
   rien d'autre à installer, aucun avertissement de sécurité à accepter.
2. Ouvrir l'app, se connecter via SSO Keycloak (matricule + mot de passe + code OTP FreeOTP/Aegis).

## Télécharger l'APK déjà compilé (le plus simple)

**[Page de téléchargement →](../../releases/latest)** — téléchargement direct,
sans compte GitHub.

Liens permanents, valables aussi après publication d'une nouvelle version :

```
https://github.com/TRAORE352/kibare/releases/latest/download/kibare-arm64-v8a.apk
https://github.com/TRAORE352/kibare/releases/latest/download/kibare-armeabi-v7a.apk
```

Deux fichiers, un par type de processeur. **Un seul s'installe sur un
téléphone donné** ; si le premier est refusé, prendre le second.

| Fichier | Pour quel téléphone |
|---|---|
| `kibare-arm64-v8a.apk` | tout téléphone vendu depuis 2016 — **à choisir par défaut** |
| `kibare-armeabi-v7a.apk` | appareils d'entrée de gamme plus anciens (32 bits) |

L'APK est signé avec la clé de test d'Element : il s'installe directement,
après avoir autorisé l'installation depuis cette source. **Le certificat de
l'autorité Kibaré est dans l'application** — aucune manipulation dans les
paramètres Android n'est nécessaire.

### Pourquoi le certificat est embarqué, et non installé à la main

Kibaré n'utilise aucune autorité de certification étrangère : le serveur de
l'administration présente un certificat délivré par l'autorité de l'État.
Un téléphone ne connaît pas cette autorité d'origine.

Deux solutions existaient. L'installation manuelle du certificat dans Android
affiche un avertissement, exige six manipulations dans les paramètres, et
l'agent peut la défaire par erreur. L'autre solution — celle retenue — place
l'autorité dans l'application, qui n'accepte **qu'elle** et refuse les
autorités publiques préinstallées par Google.

Le résultat est à la fois plus simple et plus sûr : un seul geste pour
l'agent, et un serveur usurpé muni d'un certificat acheté dans le commerce
est rejeté par l'application.

## Compiler l'APK en local (sans aucun service en ligne)

La messagerie **ne dépend d'aucun service externe** pour fonctionner. L'APK se
compile entièrement hors ligne, sur n'importe quelle machine avec un JDK 21 et
le SDK Android.

```bash
# 1. Récupérer le code d'Element Android (Element Classic)
git clone --depth 1 --branch main https://github.com/element-hq/element-android.git
cd element-android

# 2. Appliquer nos modifications Kibaré (37+ fichiers)
git apply --check ../kibare/docs/android-fork.patch   # doit être silencieux
git apply ../kibare/docs/android-fork.patch

# 3. Compiler la variante F-Droid (aucune bibliothèque Google)
export ANDROID_HOME=/chemin/vers/android-sdk
./gradlew :vector-app:assembleFdroidDebug      # APK signé avec la clé de test, installable
./gradlew :vector-app:assembleFdroidRelease    # variante release (à signer avec votre clé)
```

APK produit dans `vector-app/build/outputs/apk/fdroid/`.

Avec **Android Studio** : ouvrir le dossier `element-android` après avoir
appliqué le patch, puis choisir la variante `fdroidDebug` dans
« Build Variants » et lancer « Run ».

**Vérifier l'APK produit** (absence de Google/Firebase, CA intégrée,
protections « Zéro fuite » présentes) :

```bash
python3 scripts/verifier_apk.py chemin/vers/kibare.apk
```

Le dépôt fournit aussi un workflow GitHub Actions (`.github/workflows/apk.yml`)
qui automatise exactement ces mêmes commandes. C'est un **confort de
développement**, pas une dépendance : la plateforme et l'application
fonctionnent sans Internet.

## Tests

```bash
./scripts/run_tests.sh
```

13 tests unitaires de la Console + 16 vérifications des épreuves du jury
(intrus, le serveur ne lit rien, révocation). Voir `tests/integration/README.md`.

## Comptes de démo
Voir `docs/COMPTES_DEMO.md`. Tous les comptes sont fictifs. Mots de passe de démo dans `.env.example` (marqués « DÉMO »).

## Limites connues
Voir section 13 du brief et `docs/NOTE_SECURITE.md` :
- Photo de l'écran avec un autre appareil : atténuée par filigrane nominatif
- Client Matrix modifié : protections contournables ; atténuation par MDM en production
- Téléphone hors ligne à la révocation : effacement à la reconnexion
- iPhone : hors périmètre (installation via Apple, captures non bloquables)
- Navigateur : protections réduites
- Métadonnées visibles par le serveur (membres de salon, horodatage, taille, IP 1j, appareils, attributs annuaire)
- CA locale à installer sur le téléphone
- Prototype : pas de HA, pas de sauvegarde auto, pas d'audit externe
- Pièces jointes non images/PDF : non consultables dans l'app
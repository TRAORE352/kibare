# Fork Android — Kibaré (plan de modification)

Dépôt de départ : `element-hq/element-android` (Element Classic, Kotlin).
Variante cible : **F-Droid** (flavor `fdroid`), sans aucune bibliothèque Google.

> Statut : toutes les modifications du fork sont faites et rassemblées dans
> `docs/android-fork.patch` (47 fichiers, dont 12 binaires). Le patch a été
> vérifié : il s'applique sans erreur sur un clone neuf d'Element Android
> (`git apply --check` silencieux), et les binaires arrivent intacts
> (empreintes SHA-256 identiques).
>
> Reste à faire : la visionneuse PDF interne (§5) et la **compilation de
> l'APK**, qui doit se faire sur une machine avec JDK et Android SDK.

## 1. Déjà appliqué (au clone local)

| Changement | Fichier | Valeur |
|---|---|---|
| Identifiant d'application | `vector-app/build.gradle` (~l.146) | `applicationId "org.kibare.app"` |
| UnifiedPush externe désactivé | `vector-config/.../Config.kt` (~l.31) | `ALLOW_EXTERNAL_UNIFIED_PUSH_DISTRIBUTORS = false` |
| Blocage captures d'écran forcé | `vector/src/main/java/im/vector/app/core/platform/VectorBaseActivity.kt` (~l.234) | `FLAG_SECURE` inconditionnel |
| Nom de l'application | `vector-app/build.gradle` (~l.250, 258) | `resValue ... "app_name"` → « Kibaré » |
| CA locale intégrée | `matrix-sdk-android/src/main/res/raw/kibare_ca.pem` + `.../xml/network_security_config.xml` | confiance **uniquement** à la CA Kibaré |
| Copie interdite | `vector/.../timeline/action/MessageActionsViewModel.kt` | `Copy`, `Save`, `Share`, `ViewSource` commentés (voir §5) |
| Effacement à distance | `vector/.../signout/hard/SignedOutActivity.kt` + `.../layout/activity_signed_out.xml` + `library/ui-strings/.../strings.xml` | écran « Accès révoqué » terminal (bouton reconnexion retiré) |
| Filigrane nominatif | `vector/.../core/ui/views/WatermarkView.kt` + `fragment_timeline.xml` + `activity_big_image_viewer.xml` + `TimelineFragment.kt` + `BigImageViewerActivity.kt` | texte « Nom · Matricule · date » en diagonale, opacité ~7 % (conversation **et** visionneuse d'images) |
| Serveur par défaut fixé | `vector-config/src/main/res/values/config.xml` (`matrix_org_server_url`) | `https://10.228.115.221` (au lieu de matrix.org) |
| Sélection de texte désactivée | `.../item_timeline_event_text_message_{plain,rich}_stub.xml` | `android:textIsSelectable="false"` |
| Inscription retirée | `vector/.../features/VectorFeatures.kt` | `isOnboardingAlreadyHaveAccountSplashEnabled=false` + `isOnboardingCombinedRegisterEnabled=false` |
| « Ouvrir avec… » retiré | `vector/.../detail/TimelineFragment.kt` (`openFile`) | remplacé par un message « Consultation interne uniquement » |
| Écran serveur retiré | `vector/.../onboarding/OnboardingViewModel.kt` | `SignInSignUp` → login direct (plus de sélection du serveur) |
| Réglage FLAG_SECURE masqué | `vector/src/main/res/xml/vector_settings_security_privacy.xml` | préférence « captures d'écran » supprimée |
| Couleur institutionnelle | `library/ui-styles/.../palette.xml` | vert `#0DBD8B` → `#1F5C3A` |
| Étiquette pièce jointe | `vector/.../item_timeline_event_file_stub.xml` | « Consultation interne uniquement » |
| Icône de lancement | `vector-app/src/main/res/drawable-anydpi-v26/ic_launcher_foreground.xml` + `mipmap-*/ic_launcher*` + `values/colors.xml` | « K » vectoriel blanc sur vert `#1F5C3A` (voir §9) |
| Police IBM Plex Sans | `library/ui-styles/.../font/ibm_plex_sans*` + `theme_light.xml` | intégrée (Regular + Bold, SIL OFL) |
| Partage de position retiré | `vector-config/.../Config.kt` | `ENABLE_LOCATION_SHARING = false`, clé MapTiler vidée |
| Statistiques et rapports de plantage retirés | `vector-config/.../Config.kt` | les 6 variantes passent à `Analytics.Disabled` (plus de PostHog ni Sentry) |
| Publicité « Element X » retirée | `vector-config/.../Config.kt` | `sunsetConfig = SunsetConfig.Disabled` |
| Annuaire public, Jitsi, passerelles externes retirés | `vector-config/src/main/res/values/config.xml` | plus de matrix.org / gitter.im / meet.element.io / unifiedpush.org ; push vers le serveur de l'État |
| Liens d'aide externes retirés | `vector-config/src/main/res/values/urls.xml` | `threads_learn_more_url` et `ftue_ems_url` vidés |
| Signalement de bogue en ligne retiré | `VectorPreferences.useRageshake()` + `vector_settings_advanced_settings.xml` + `VectorSettingsAdvancedSettingsFragment.kt` | renvoie `false` ; catégorie retirée des réglages ; `setupRageShakeSection()` vidée |
| Accusés de lecture privés | `matrix-sdk-android/.../read/SetReadMarkersTask.kt` | envoi en `m.read.private` (MSC2285) au lieu de `m.read` |
| « En train d'écrire » désactivé | `VectorPreferences.sendTypingNotifs()` + `vector_settings_preferences.xml` | renvoie `false` ; réglage retiré |
| Notifications sans contenu | `vector/.../notifications/NotifiableEventResolver.kt` | « Nouveau message » seul : ni texte, ni expéditeur, ni salon, ni image, ni avatars |
| Salons toujours chiffrés | `CreateRoomViewModel.kt` + `CreateRoomController.kt` | `enableEncryption()` inconditionnel ; interrupteur remplacé par un texte non modifiable |

## 2. Identité de l'application

- **Icône et couleurs** : `vector-app/src/main/res/mipmap-*/ic_launcher*` et
  `values/colors.xml`. Vert institutionnel `#1F5C3A` (section 10 du brief).
- **Police IBM Plex Sans** : ajouter les fichiers TTF dans `res/font/` et
  référencer dans le thème (SIL OFL, à citer dans le README).
- **Réglage « Empêcher les captures d'écran » à masquer** : le préférence
  `useFlagSecure()` (VectorPreferences) doit être masquée dans l'écran des
  paramètres, car FLAG_SECURE est désormais forcé.

## 3. Serveur et connexion (section 8.2)

- **Serveur par défaut fixé** à `https://<KIBARE_SERVER_ADDRESS>` : l'écran de
  saisie de l'URL du serveur est
  `vector/src/main/java/im/vector/app/features/onboarding/ftueauth/FtueAuthServerUrlFormFragment.kt`.
  Le supprimer du flux d'onboarding et hardcoder l'URL (via `BuildConfig` ajouté
  dans `vector-app/build.gradle`). Prévoir un écran caché « Configuration du
  serveur » accessible avant l'activation (section 5.8).
- **Supprimer le choix du serveur** de l'écran d'accueil (plus de champ « Homeserver »).
- **Supprimer « Créer un compte »** : l'écran d'accueil ne propose que
  « Se connecter » (SSO Keycloak).
- **Supprimer tout lien externe** — FAIT : voir le tableau du §1. Jitsi, cartes
  MapTiler, rapports de bogue (Sentry / rageshake), statistiques (PostHog),
  annuaire public de salons, passerelles UnifiedPush publiques et liens d'aide
  element.io sont tous retirés (`Config.kt`, `config.xml`, `urls.xml`,
  `VectorPreferences.useRageshake()`).

## 4. CA locale (section 5.7)

- `vector/src/main/res/xml/network_security_config.xml` et
  `matrix-sdk-android/src/main/res/xml/network_security_config.xml` :
  ajouter la CA Kibaré comme **seule** ancre de confiance (`<trust-anchors>`
  avec `<certificates src="@raw/kibare_ca">`), en copiant
  `caddy/kibare-ca.crt` vers `res/raw/kibare_ca.pem`.

## 5. Protections « Zéro fuite » (section 6)

- **FLAG_SECURE forcé** : appliquer `WindowManager.LayoutParams.FLAG_SECURE` à
  toutes les activités (classe de base des activités, `vector-app/src/main/java/...`).
  Forcer à vrai et **masquer** le réglage existant « Empêcher les captures d'écran ».
- **Filigrane nominatif** : vue superposée non interactive sur l'écran de
  conversation et la visionneuse d'images, texte répété en diagonale (opacité
  6-8 %) : `Nom Prénom · Matricule · date`.
- **Copie interdite** : retirer « Copier » du menu d'appui long, désactiver la
  sélection de texte dans les bulles, retirer « Voir la source », retirer
  « Partager ». Garder « Répondre » et « Transférer » (interne uniquement).
- **Pièces jointes internes** : retirer « Enregistrer/Télécharger », « Partager »,
  « Ouvrir avec… ». Garder « Transférer ». Visionneuse d'images interne (avec
  filigrane). PDF via `android.graphics.pdf.PdfRenderer` (API standard).
  Étiquette « Consultation interne uniquement ».
- **Effacement à distance** : à la réception d'une erreur `M_UNKNOWN_TOKEN` (sans
  `soft_logout`), effacer base locale, cache médias, clés, préférences, puis
  afficher l'écran plein écran « Accès révoqué » (sans bouton retour).

## 6. Métadonnées (section 5.5) — FAIT

- **Accusés de lecture en mode privé** : `SetReadMarkersTask` envoie désormais
  `m.read.private` (MSC2285, stable depuis Matrix 1.4) au lieu de `m.read`. Le
  serveur retient la position de lecture pour l'utilisateur, mais ne la diffuse
  plus aux autres membres : personne ne sait « qui a lu quoi et quand ».
  Le marqueur `m.fully_read` est envoyé séparément (il est privé par nature).
- **Indicateur « en train d'écrire » désactivé** : `sendTypingNotifs()` renvoie
  `false` en dur et le réglage a été retiré de l'écran des préférences.
- **Notifications sans contenu** : seule la mention « Nouveau message »
  apparaît. Le texte du message, le nom de l'expéditeur, le nom du salon,
  l'aperçu d'image et les avatars ne sortent plus de l'application — ils
  seraient lisibles sur l'écran verrouillé, donc hors du périmètre protégé
  par FLAG_SECURE. Les fonctions `fetchImageIfPresent()` et
  `downloadAndExportImage()` ont été supprimées : elles exportaient l'image
  vers un URI partageable accessible au système Android.

## 7. Chiffrement (section 5.1) — FAIT

- `CreateRoomViewModel.doCreateRoom()` appelle `enableEncryption()` de façon
  inconditionnelle : aucun salon en clair ne peut être créé, quel que soit le
  type de salon ou le choix de l'utilisateur.
- `CreateRoomController` : l'interrupteur « chiffrement » est remplacé par un
  texte d'information non modifiable.

## 8. Compilation

```bash
# (sur la machine de build, avec JDK 17 ou 21)
export ANDROID_HOME=/opt/android-sdk
./gradlew :vector-app:assembleFdroidRelease
```

APK produit : `vector-app/build/outputs/apk/fdroid/release/`.
Vérifier l'absence de bibliothèque Google/Firebase dans l'APK (section 5.6).

## 9. Icône de lancement

L'icône n'est **pas** un simple PNG : Element utilise une « icône adaptative »
(adaptive icon), composée de deux calques vectoriels.

| Fichier | Rôle |
|---|---|
| `vector-app/src/main/res/drawable/ic_launcher_background.xml` | fond plein, couleur `@color/launcher_background` |
| `vector-app/src/main/res/values/colors.xml` | `launcher_background` = `#1F5C3A` (vert institutionnel) |
| `vector-app/src/main/res/drawable-anydpi-v26/ic_launcher_foreground.xml` | avant-plan : le « K » de Kibaré, tracé vectoriel |
| `vector-app/src/main/res/mipmap-*/ic_launcher*.png` | repli « legacy » pour Android 5 à 7 (minSdk = 21) |

Le « K » reste dans la **zone sûre** des icônes adaptatives (cercle de rayon 33
autour du centre 54,54 dans le repère 108×108) : il n'est jamais rogné, quelle
que soit la forme d'icône choisie par le lanceur (cercle, carré arrondi, goutte).

Les PNG de repli sont générés avec Pillow à partir de la **même géométrie** que
le vectoriel, pour que l'icône soit identique sur toutes les versions d'Android.
Le script est reproduit dans le commit correspondant.

## 10. Le fork est livré sous forme de patch

Il n'y a **pas** de sous-module Git : le fork vit dans
`docs/android-fork.patch`, qui s'applique sur un clone d'Element Android
(Element Classic).

```bash
git clone --depth 1 --branch main https://github.com/element-hq/element-android.git
cd element-android
git apply --check ../kibare/docs/android-fork.patch   # doit être silencieux
git apply ../kibare/docs/android-fork.patch
```

**Piège important** : le patch contient 12 fichiers binaires (10 PNG d'icône et
2 polices TTF). Il **doit** être régénéré avec l'option `--binary`, sinon
`git apply` échoue avec `cannot apply binary patch … without full index line`
et ni l'icône ni la police n'arrivent dans le fork :

```bash
cd element-android
git add -A
git diff --cached --binary > ../kibare/docs/android-fork.patch
```

Après toute régénération, vérifier sur un clone **neuf** que
`git apply --check` passe — c'est le seul contrôle qui prouve que le patch est
livrable.

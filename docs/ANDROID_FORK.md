# Fork Android — Kibaré (plan de modification)

Dépôt de départ : `element-hq/element-android` (Element Classic, Kotlin).
Variante cible : **F-Droid** (flavor `fdroid`), sans aucune bibliothèque Google.

> Statut : l'analyse de la structure est faite, les changements d'identité
> (`applicationId`, UnifiedPush externe) sont appliqués au clone local, et la
> première compilation F-Droid est lancée. Les changements restants sont listés
> ci-dessous avec leur emplacement.

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
- **Supprimer tout lien externe** : serveur d'identité, Jitsi, cartes
  (MapTiler/OpenStreetMap), rapports de bugs (Sentry/rageshake), statistiques
  (PostHog), aide en ligne. Voir `Config.kt` (flags `ENABLE_LOCATION_SHARING`,
  `LOCATION_MAP_TILER_KEY`, `Analytics`…).

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

## 6. Métadonnées (section 5.5)

- Accusés de lecture en mode privé (`m.read.private`) par défaut.
- Indicateur « en train d'écrire » désactivé par défaut.
- Notifications sans contenu (« Nouveau message » uniquement).

## 7. Chiffrement (section 5.1)

- Salons toujours chiffrés : retirer/forcer l'option « non chiffré » de l'écran
  de création de salon.

## 8. Compilation

```bash
# (sur la machine de build, avec JDK 17 ou 21)
export ANDROID_HOME=/opt/android-sdk
./gradlew :vector-app:assembleFdroidRelease
```

APK produit : `vector-app/build/outputs/apk/fdroid/release/`.
Vérifier l'absence de bibliothèque Google/Firebase dans l'APK (section 5.6).

## Sous-module Git

Le dépôt principal inclut `android/` comme sous-module pointant vers le fork
public `kibare-android` (créé sur le compte GitHub de l'équipe). Contenu de
`.gitmodules` :

```
[submodule "android"]
    path = android
    url = https://github.com/<EQUIPE>/kibare-android.git
```

Après création du fork et application des changements ci-dessus, pousser les
commits progressifs (messages en français) puis :
`git submodule add <url-fork> android`.

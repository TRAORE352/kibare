# Le nouveau design n'apparaît pas — diagnostic et remèdes

Trois mécanismes différents peuvent faire croire que la refonte graphique
n'a pas été appliquée. Aucun ne produit d'erreur : tout paraît correct côté
dépôt alors que l'écran ne change pas. Ils se traitent séparément.

Vérifier dans cet ordre.

---

## 1. Console d'administration — le navigateur sert sa copie en cache

### Symptôme
La console garde l'ancienne apparence après une mise à jour, y compris après
un redémarrage du conteneur.

### Cause
`/console/static/css/style.css` était une URL stable. Un navigateur qui avait
déjà ouvert la console servait sa copie en cache, indéfiniment, sans jamais
redemander le fichier au serveur. Le serveur livrait bien la nouvelle feuille :
personne ne la lui demandait.

### Remède — déjà appliqué dans le code
L'URL porte désormais l'empreinte du contenu :
`/console/static/css/style.css?v=7065d8d9fd`. Elle change dès que la feuille
change, donc le navigateur retélécharge. Le cache reste actif quand rien ne
bouge, ce qui est le comportement souhaité.

Implémenté dans `console/app/templating.py` et appliqué aux trois gabarits qui
chargent la feuille — y compris `activate.html` et `activated.html`, qui
n'héritent pas de `base.html`.

### Si le symptôme persiste
Recharger en vidant le cache : `Ctrl + Maj + R` (`Cmd + Maj + R` sur Mac).
Puis vérifier que l'URL servie porte bien un `?v=` :

```bash
curl -s https://<adresse>/console/agents | grep style.css
```

---

## 2. Page de connexion Keycloak — le realm était déjà importé

### Symptôme
La page de connexion garde l'apparence Keycloak par défaut, alors que
`keycloak/themes/kibare/` existe et que `realm-kibare.json` contient bien
`"loginTheme": "kibare"`.

### Cause
`start --import-realm` n'importe le realm qu'au **premier** démarrage. Si la
base PostgreSQL contient déjà le realm « kibare », le fichier JSON est ignoré
**en silence** — pas d'avertissement, pas d'erreur. Ajouter un attribut au
fichier ne change donc rien à une installation existante.

### Remède

```bash
./scripts/appliquer_theme_keycloak.sh
```

Le script écrit l'attribut via l'API d'administration, sans toucher aux
utilisateurs, clients ni rôles, puis **relit la valeur depuis le serveur**
avant d'annoncer un succès — une commande qui retourne 0 ne prouve pas que
l'attribut est en base.

### Si le symptôme persiste après le script
Le thème n'est pas monté dans le conteneur. Vérifier le volume :

```bash
docker exec kibare-keycloak ls /opt/keycloak/themes/kibare/login
docker compose up -d keycloak
```

### Remise à zéro complète (détruit les comptes de démonstration)

```bash
docker compose down -v && docker compose up -d
```

---

## 3. Application Android — l'APK publié précède la refonte

### Symptôme
L'application installée affiche l'ancien écran d'accueil Element.

### Cause
Un APK est un binaire compilé : il fige l'état du code au moment de la
compilation. Les fichiers publiés le 1er novembre à 21h32 ont été compilés
**avant** que la refonte soit écrite (2 novembre, 02h44). Modifier le code
après coup ne modifie aucun APK déjà construit.

### Comment le vérifier soi-même
Les chaînes du nouvel écran n'existent que dans la version refaite :

```python
import zipfile
z = zipfile.ZipFile("kibare-arm64-v8a.apk")
arsc = z.read("resources.arsc")
print(arsc.count("Administration du Burkina Faso".encode()))   # 0 = ancien, 1 = refait
```

Chercher la chaîne dans `classes*.dex` ne donnerait rien : sur Android, les
ressources texte sont compilées dans `resources.arsc`, pas dans le code.

### Remède
Télécharger l'APK à jour depuis la release — les liens ci-dessous pointent
toujours vers la dernière version publiée :

- https://github.com/TRAORE352/kibare/releases/latest/download/kibare-arm64-v8a.apk
  (téléphones récents, 64 bits — à prendre par défaut)
- https://github.com/TRAORE352/kibare/releases/latest/download/kibare-armeabi-v7a.apk
  (si le premier est refusé à l'installation)

Désinstaller l'ancienne version avant d'installer la nouvelle : Android refuse
une réinstallation lorsque la signature ou la version diffère.

### Pour recompiler après une modification
Le workflow `.github/workflows/apk.yml` se déclenche automatiquement à chaque
modification de `docs/android-fork.patch`, ou manuellement depuis l'onglet
Actions du dépôt. Compter environ 25 minutes.

**Un artefact de compilation n'est pas un livrable** : son téléchargement
exige un jeton d'authentification et il expire. Pour diffuser l'application,
toujours passer par une release, dont les liens `latest/download/` sont
publics et stables.

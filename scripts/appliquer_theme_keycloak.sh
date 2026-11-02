#!/usr/bin/env bash
#
# Applique le thème de connexion Kibaré à un realm DÉJÀ IMPORTÉ.
#
# POURQUOI CE SCRIPT EXISTE
#
# `start --import-realm` n'importe le realm qu'au PREMIER démarrage : si la
# base Keycloak contient déjà le realm « kibare », le fichier
# realm-kibare.json est ignoré en silence. Ajouter "loginTheme": "kibare" au
# fichier ne change donc RIEN sur une installation existante — la page de
# connexion garde l'apparence par défaut, sans le moindre message d'erreur.
#
# Le symptôme vu par l'utilisateur : « le nouveau design n'est pas appliqué ».
# La cause n'est ni le thème ni le volume : c'est que le realm en base n'a
# jamais reçu l'attribut.
#
# Ce script écrit l'attribut directement via l'API d'administration, sans
# toucher aux utilisateurs, aux clients ni aux rôles existants.
#
# Usage, depuis le dossier du projet :
#     ./scripts/appliquer_theme_keycloak.sh
#
set -euo pipefail

REALM="${KEYCLOAK_REALM:-kibare}"
THEME="${KEYCLOAK_LOGIN_THEME:-kibare}"
CONTENEUR="${KEYCLOAK_CONTAINER:-kibare-keycloak}"
UTILISATEUR="${KEYCLOAK_ADMIN_USER:-admin}"

echo "→ Application du thème « ${THEME} » au realm « ${REALM} »"

if ! docker ps --format '{{.Names}}' | grep -qx "${CONTENEUR}"; then
  echo "ERREUR : le conteneur ${CONTENEUR} ne tourne pas." >&2
  echo "        Démarrez la pile avec « docker compose up -d » d'abord." >&2
  exit 1
fi

# Le mot de passe est lu depuis le secret monté dans le conteneur : il ne
# transite ni par la ligne de commande (visible dans ps) ni par ce fichier.
MDP=$(docker exec "${CONTENEUR}" cat /run/secrets/keycloak_admin_password)

echo "→ Ouverture d'une session d'administration"
docker exec "${CONTENEUR}" /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080/auth \
  --realm master \
  --user "${UTILISATEUR}" \
  --password "${MDP}" >/dev/null

echo "→ Écriture de l'attribut loginTheme"
docker exec "${CONTENEUR}" /opt/keycloak/bin/kcadm.sh update "realms/${REALM}" \
  -s "loginTheme=${THEME}" >/dev/null

# VÉRIFICATION : on relit la valeur depuis le serveur. Un « succès » de la
# commande précédente ne prouve pas que l'attribut est en base ; seule la
# relecture le prouve.
LU=$(docker exec "${CONTENEUR}" /opt/keycloak/bin/kcadm.sh get "realms/${REALM}" \
       --fields loginTheme 2>/dev/null | tr -d ' \n\r"' | sed 's/.*loginTheme://;s/[{},].*//')

if [ "${LU}" = "${THEME}" ]; then
  echo "✓ Vérifié : le realm ${REALM} utilise désormais le thème « ${LU} »."
  echo
  echo "  Rechargez la page de connexion avec le cache vidé (Ctrl+Maj+R)."
  echo "  Si l'apparence ne change pas, le thème n'est pas monté dans le"
  echo "  conteneur : vérifiez le volume ./keycloak/themes/kibare dans"
  echo "  docker-compose.yml, puis « docker compose up -d keycloak »."
else
  echo "ERREUR : après écriture, le serveur renvoie loginTheme=« ${LU} »" >&2
  echo "        au lieu de « ${THEME} ». L'attribut n'a pas été appliqué." >&2
  exit 1
fi

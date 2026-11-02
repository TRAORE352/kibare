# app/templating.py — Moteur de templates Jinja2 partagé
import hashlib
import os

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")

CHEMIN_CSS = "app/static/css/style.css"

# Mémo : (date de modification, empreinte). Évite de relire et hacher le
# fichier à chaque requête tout en restant juste quand il change.
_memo: tuple[float, str] | None = None


def version_actifs() -> str:
    """
    Empreinte courte du contenu de la feuille de style.

    POURQUOI : `/console/static/css/style.css` est une URL stable, donc le
    navigateur d'un administrateur qui a déjà ouvert la console sert sa copie
    en cache et ignore une mise à jour du design — l'interface paraît
    inchangée alors que le serveur livre bien la nouvelle version. Le défaut
    est invisible côté serveur et ne se voit que sur le poste du visiteur.

    En suffixant l'URL par cette empreinte (`?v=<hash>`), l'adresse change dès
    que le fichier change : le navigateur retélécharge, sans qu'on ait besoin
    de désactiver le cache (qu'on veut garder, justement, quand rien ne bouge).

    POURQUOI RECALCULÉE, ET NON FIGÉE AU DÉMARRAGE : le code de la console est
    monté en volume (`./console/app:/app/app:ro` dans docker-compose.yml), donc
    la feuille PEUT changer sous le processus — un `git pull` suffit, sans
    redémarrage du conteneur. Une empreinte calculée une seule fois à l'import
    resterait alors figée sur l'ancienne valeur, et le cache du navigateur
    continuerait de servir l'ancien design : précisément le défaut que cette
    fonction doit supprimer.

    Le coût est maîtrisé par le mémo sur la date de modification : un appel
    `stat` par requête, et une relecture seulement quand le fichier a bougé.

    Repli sur une valeur constante si le fichier est illisible : mieux vaut un
    cache contourné qu'une console qui refuse de servir une page pour un détail
    d'affichage.
    """
    global _memo
    try:
        mtime = os.path.getmtime(CHEMIN_CSS)
    except OSError:
        return "0"
    if _memo is not None and _memo[0] == mtime:
        return _memo[1]
    try:
        with open(CHEMIN_CSS, "rb") as f:
            empreinte = hashlib.sha256(f.read()).hexdigest()[:10]
    except OSError:
        return "0"
    _memo = (mtime, empreinte)
    return empreinte


# Exposée à tous les gabarits sans avoir à la passer dans chaque contexte.
# C'est la FONCTION qui est exposée, pas sa valeur : Jinja l'appelle à chaque
# rendu, donc une feuille modifiée à chaud est prise en compte immédiatement.
templates.env.globals["version_actifs"] = version_actifs

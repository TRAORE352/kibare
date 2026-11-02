# app/templating.py — Moteur de templates Jinja2 partagé
import hashlib
import os

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")


def _empreinte_actifs() -> str:
    """
    Empreinte courte du contenu de la feuille de style.

    POURQUOI : `/console/static/css/style.css` est une URL stable, donc le
    navigateur d'un administrateur qui a deja ouvert la console sert sa copie
    en cache et ignore une mise a jour du design — l'interface parait
    inchangee alors que le serveur livre bien la nouvelle version. Le defaut
    est invisible cote serveur et ne se voit que sur le poste du visiteur.

    En suffixant l'URL par cette empreinte (`?v=<hash>`), l'adresse change des
    que le fichier change : le navigateur retelecharge, sans qu'on ait besoin
    de desactiver le cache (qu'on veut garder, justement, quand rien ne bouge).

    Repli sur la date de demarrage si le fichier est illisible : mieux vaut un
    cache contourne qu'une console qui refuse de demarrer pour un detail
    d'affichage.
    """
    chemin = "app/static/css/style.css"
    try:
        with open(chemin, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:10]
    except OSError:
        return str(int(os.path.getmtime(".")) if os.path.exists(".") else 0)


# Calculee une fois au demarrage : le conteneur est immuable en production,
# et un hachage par requete couterait une lecture disque a chaque page.
VERSION_ACTIFS = _empreinte_actifs()

# Exposee a tous les gabarits sans avoir a la passer dans chaque contexte.
templates.env.globals["version_actifs"] = VERSION_ACTIFS

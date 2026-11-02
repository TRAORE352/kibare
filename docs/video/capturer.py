"""
Captures pour la vidéo de candidature, prises depuis l'ÉTAT PUBLIÉ du dépôt
(clone frais /tmp/etat-livre), jamais depuis l'arbre de travail.

Le script REFUSE d'écrire une image dont la page n'a pas rendu ce qu'on
attend : une capture muette (page d'erreur, état vide, gabarit cassé) passe
tous les contrôles de taille de fichier et n'est découverte qu'au montage.
Chaque prise déclare donc un TÉMOIN — une chaîne que seule la bonne page
produit — et une capture sans témoin est refusée, pas écrite.
"""
import os
import sys

from playwright.sync_api import sync_playwright

EXE = "/root/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome"
SORTIE = "/root/kibare-video/captures"

CONSOLE = "http://127.0.0.1:8779"
KEYCLOAK = "http://127.0.0.1:8780"

# (nom de fichier, url, témoin attendu dans le texte visible, largeur, hauteur)
PRISES = [
    ("01-connexion-desktop", f"{KEYCLOAK}/login-nominal.html", "Connexion", 1440, 900),
    ("02-connexion-mobile",  f"{KEYCLOAK}/login-nominal.html", "Connexion", 390, 844),
    ("03-agents",            f"{CONSOLE}/agents.html", "Agents enrôlés", 1440, 900),
    ("04-agent-detail",      f"{CONSOLE}/agent_detail.html", "Révocation de l'accès", 1440, 900),
    ("05-annuaire",          f"{CONSOLE}/directory.html", "Annuaire", 1440, 900),
    ("06-enrolement",        f"{CONSOLE}/enroll.html", "Enrôler un agent", 1440, 900),
    ("07-journal",           f"{CONSOLE}/journal.html", "Journal", 1440, 900),
    ("08-agents-mobile",     f"{CONSOLE}/agents.html", "Agents enrôlés", 390, 844),
    # L'écran d'erreur reste utile : il montre que l'accès est refusé.
    ("10-connexion-refus",   f"{KEYCLOAK}/login.html", "incorrect", 1440, 900),
]


def main():
    os.makedirs(SORTIE, exist_ok=True)
    produites, refusees = [], []

    with sync_playwright() as p:
        nav = p.chromium.launch(executable_path=EXE, args=["--no-sandbox"])
        for nom, url, temoin, w, h in PRISES:
            cible = f"{SORTIE}/{nom}.png"
            if os.path.exists(cible):
                os.remove(cible)      # jamais une image périmée d'un essai précédent
            page = nav.new_page(viewport={"width": w, "height": h},
                                device_scale_factor=2)
            try:
                rep = page.goto(url, wait_until="networkidle")
                if rep.status != 200:
                    refusees.append(f"{nom} : HTTP {rep.status}")
                    continue
                page.evaluate("document.fonts.ready")
                texte = page.evaluate("document.body.innerText")
                # `innerText` rend la casse AFFICHÉE : un libellé stylé en
                # `text-transform: uppercase` ressort en capitales et un
                # témoin littéral échoue sur une page pourtant correcte.
                if temoin.lower() not in texte.lower():
                    refusees.append(f"{nom} : témoin « {temoin} » absent de la page")
                    continue
                # Un seuil global sur la longueur du texte ne convient pas :
                # un écran de connexion nominal tient en ~70 caractères
                # visibles, ce qui est normal et non un échec de rendu. On
                # exige donc un nombre d'ÉLÉMENTS INTERACTIFS, qui distingue
                # un vrai écran d'une page d'erreur ou d'un chargement.
                interactifs = page.evaluate(
                    "document.querySelectorAll('input,button,a,table,form').length")
                if interactifs < 2:
                    refusees.append(f"{nom} : page sans contenu interactif "
                                    f"({interactifs} élément(s), {len(texte.strip())} car.)")
                    continue
                # La police doit être chargée, pas seulement déclarée : une
                # capture en police système ne montre pas le produit livré.
                chargees = page.evaluate(
                    "[...document.fonts].filter(f=>f.status==='loaded').map(f=>f.family)")
                if "IBM Plex Sans" not in chargees:
                    refusees.append(f"{nom} : IBM Plex Sans non chargée ({chargees})")
                    continue
                page.screenshot(path=cible, full_page=True)
                produites.append(f"{nom}.png  ({w}x{h}, {os.path.getsize(cible)//1024} Ko)")
            except Exception as e:
                refusees.append(f"{nom} : {type(e).__name__}: {e}")
            finally:
                page.close()
        nav.close()

    for x in produites:
        print("  produite ", x)
    for x in refusees:
        print("  REFUSÉE  ", x)
    print(f"\n{len(produites)} produites, {len(refusees)} refusées")
    return 1 if refusees else 0


if __name__ == "__main__":
    sys.exit(main())

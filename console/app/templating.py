# app/templating.py — Moteur de templates Jinja2 partagé
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")

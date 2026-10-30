# app/models.py — Modèles de données de la Console Kibaré
"""
Modèles : Agent, Jeton d'activation, Journal de révocation.

Point important pour le jury : le jeton d'activation n'est JAMAIS stocké en
clair. Seul son empreinte SHA-256 est enregistrée. Si la base est volée,
l'attaquant ne peut pas reconstruire un jeton valide.
"""
import enum
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Index, Text, Boolean, Integer
from sqlalchemy.orm import relationship
from app.database import Base


def utcnow() -> datetime:
    """Heure UTC actuelle, sans fuseau (compatible SQLAlchemy DateTime)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AgentStatus(str, enum.Enum):
    """Statut d'un agent dans le système."""
    PENDING = "pending"    # enrôlé, en attente d'activation
    ACTIVE = "active"      # activé, peut se connecter
    REVOKED = "revoked"    # révoqué, accès coupé


class AgentRole(str, enum.Enum):
    """Rôles (identiques aux rôles de realm Keycloak)."""
    SUPER_ADMIN = "super-admin"
    ADMIN_MINISTERE = "admin-ministere"
    AGENT = "agent"


class Ministere(str, enum.Enum):
    """Ministères (codes)."""
    MTDPCE = "MTDPCE"
    SANTE = "SANTE"
    SECURITE = "SECURITE"
    MEF = "MEF"


class Agent(Base):
    """Un agent enrôlé dans Kibaré."""
    __tablename__ = "agents"

    matricule = Column(String(50), primary_key=True, index=True)
    nom = Column(String(100), nullable=False)
    prenom = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    ministere = Column(Enum(Ministere), nullable=False, index=True)
    direction = Column(String(200), nullable=False)
    service = Column(String(200), nullable=True)
    fonction = Column(String(200), nullable=False)
    role = Column(Enum(AgentRole), nullable=False, default=AgentRole.AGENT)
    status = Column(Enum(AgentStatus), nullable=False, default=AgentStatus.PENDING, index=True)

    date_enrolement = Column(DateTime, default=utcnow, nullable=False)
    date_activation = Column(DateTime, nullable=True)
    date_revocation = Column(DateTime, nullable=True)
    revoque_par = Column(String(50), ForeignKey("agents.matricule"), nullable=True)
    motif_revocation = Column(Text, nullable=True)

    # Identifiant Keycloak (UUID) de l'utilisateur, pour les appels API admin
    keycloak_id = Column(String(64), nullable=True)

    activation_token = relationship("ActivationToken", back_populates="agent", uselist=False)


class ActivationToken(Base):
    """
    Jeton d'activation à usage unique (section 6.4.A du brief).

    - Généré avec 32 octets aléatoires (secrets.token_urlsafe).
    - Seul le HASH SHA-256 est stocké (jamais le jeton en clair).
    - Expire après 48 h.
    - Utilisable UNE SEULE fois.
    """
    __tablename__ = "activation_tokens"

    token_hash = Column(String(64), primary_key=True, index=True)  # SHA-256 hex (64 car.)
    agent_matricule = Column(String(50), ForeignKey("agents.matricule"), nullable=False, unique=True, index=True)

    cree_le = Column(DateTime, default=utcnow, nullable=False)
    expire_le = Column(DateTime, nullable=False, index=True)
    utilise = Column(Boolean, default=False, nullable=False)
    utilise_le = Column(DateTime, nullable=True)

    agent = relationship("Agent", back_populates="activation_token")

    @staticmethod
    def generate_token(bytes_length: int = 32) -> str:
        """Génère un jeton aléatoire sûr pour les URLs (token_urlsafe)."""
        return secrets.token_urlsafe(bytes_length)

    @staticmethod
    def hash_token(token: str) -> str:
        """Calcule l'empreinte SHA-256 du jeton (hex)."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @classmethod
    def create_for_agent(cls, agent_matricule: str, ttl_hours: int = 48,
                         token_bytes: int = 32):
        """
        Crée un jeton pour un agent.
        Renvoie (objet_ActivationToken, jeton_en_clair).
        Le jeton en clair n'est renvoyé QU'UNE SEULE FOIS, ici, pour l'afficher
        en QR code. Ensuite il n'existe plus nulle part (sauf chez l'admin).
        """
        token = cls.generate_token(token_bytes)
        obj = cls(
            token_hash=cls.hash_token(token),
            agent_matricule=agent_matricule,
            expire_le=utcnow() + timedelta(hours=ttl_hours),
        )
        return obj, token

    def verify(self, token: str) -> bool:
        """
        Vérifie qu'un jeton fourni est valide.
        Conditions : non utilisé, non expiré, et le hash correspond.
        """
        if self.utilise:
            return False
        if utcnow() > self.expire_le:
            return False
        # Comparaison à temps constant pour éviter les attaques par timing.
        return secrets.compare_digest(self.hash_token(token), self.token_hash)

    def consume(self):
        """Marque le jeton comme utilisé (définitivement)."""
        self.utilise = True
        self.utilise_le = utcnow()


class RevocationLog(Base):
    """
    Journal d'audit des révocations.
    Contient : qui a révoqué qui, quand, et le motif.
    Ne contient JAMAIS de contenu de message (règle éliminatoire).
    """
    __tablename__ = "revocation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_matricule = Column(String(50), ForeignKey("agents.matricule"), nullable=False, index=True)
    revoque_par = Column(String(50), ForeignKey("agents.matricule"), nullable=False, index=True)
    motif = Column(Text, nullable=True)
    date_revocation = Column(DateTime, default=utcnow, nullable=False, index=True)

    # Suivi technique des deux étapes (Keycloak puis Synapse)
    keycloak_disabled = Column(Boolean, default=False, nullable=False)
    keycloak_sessions_closed = Column(Boolean, default=False, nullable=False)
    synapse_deactivated = Column(Boolean, default=False, nullable=False)

    __table_args__ = (
        Index("ix_revocation_agent_date", "agent_matricule", "date_revocation"),
        Index("ix_revocation_admin_date", "revoque_par", "date_revocation"),
    )

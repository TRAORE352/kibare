# app/models.py - Modèles SQLAlchemy pour la Console Kibaré
"""
Modèles de données : Agent, Jeton d'activation, Journal de révocation.
"""

import enum
import secrets
import hashlib
from datetime import datetime, timedelta
from sqlalchemy import (
    Column, String, DateTime, Enum, ForeignKey, Index, Text, Boolean, Integer
)
from sqlalchemy.orm import relationship, declarative_mixin
from app.database import Base


class AgentStatus(str, enum.Enum):
    """Statut d'un agent dans le système."""
    PENDING = "pending"          # Enrôlé, en attente d'activation
    ACTIVE = "active"            # Activé, connecté
    REVOKED = "revoked"          # Révoqué, accès coupé


class AgentRole(str, enum.Enum):
    """Rôles Keycloak correspondants."""
    SUPER_ADMIN = "super-admin"
    ADMIN_MINISTERE = "admin-ministere"
    AGENT = "agent"


class Ministere(str, enum.Enum):
    """Ministères (codes officiels)."""
    MTDPCE = "MTDPCE"
    SANTE = "SANTE"
    SECURITE = "SECURITE"
    MEF = "MEF"


class Agent(Base):
    """Agent enrôlé dans Kibaré."""
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
    
    # Métadonnées
    date_enrolement = Column(DateTime, default=datetime.utcnow, nullable=False)
    date_activation = Column(DateTime, nullable=True)
    date_revocation = Column(DateTime, nullable=True)
    revoque_par = Column(String(50), ForeignKey("agents.matricule"), nullable=True)
    motif_revocation = Column(Text, nullable=True)
    
    # Relations
    activation_token = relationship("ActivationToken", back_populates="agent", uselist=False)
    revocations_initiees = relationship("RevocationLog", foreign_keys="RevocationLog.revoque_par", back_populates="admin")
    revocations_subies = relationship("RevocationLog", foreign_keys="RevocationLog.agent_matricule", back_populates="agent")


class ActivationToken(Base):
    """
    Jeton d'activation à usage unique.
    SEUL LE HASH (SHA-256) EST STOCKÉ - JAMAIS LE JETEN EN CLAIR.
    """
    __tablename__ = "activation_tokens"

    token_hash = Column(String(64), primary_key=True, index=True)  # SHA-256 hex
    agent_matricule = Column(String(50), ForeignKey("agents.matricule"), nullable=False, unique=True, index=True)
    
    # Métadonnées
    cree_le = Column(DateTime, default=datetime.utcnow, nullable=False)
    expire_le = Column(DateTime, nullable=False, index=True)
    utilise_le = Column(DateTime, nullable=True)
    utilise = Column(Boolean, default=False, nullable=False)
    
    # Relation
    agent = relationship("Agent", back_populates="activation_token")

    @staticmethod
    def generate_token(bytes_length: int = 32) -> str:
        """Génère un jeton aléatoire URL-safe."""
        return secrets.token_urlsafe(bytes_length)

    @staticmethod
    def hash_token(token: str) -> str:
        """Calcule le hash SHA-256 du jeton (hex)."""
        return hashlib.sha256(token.encode()).hexdigest()

    @classmethod
    def create_for_agent(cls, agent_matricule: str, ttl_hours: int = 48, token_bytes: int = 32) -> tuple["ActivationToken", str]:
        """
        Crée un jeton pour un agent.
        Retourne (objet ActivationToken, jeton_en_clair).
        LE JETON EN CLAIR N'EST RETOURNÉ QU'UNE SEULE FOIS ICI.
        """
        token = cls.generate_token(token_bytes)
        token_hash = cls.hash_token(token)
        expire_le = datetime.utcnow() + timedelta(hours=ttl_hours)
        
        obj = cls(
            token_hash=token_hash,
            agent_matricule=agent_matricule,
            expire_le=expire_le,
        )
        return obj, token

    def verify(self, token: str) -> bool:
        """Vérifie un jeton fourni par l'utilisateur."""
        if self.utilise:
            return False
        if datetime.utcnow() > self.expire_le:
            return False
        return self.hash_token(token) == self.token_hash

    def consume(self):
        """Marque le jeton comme utilisé."""
        self.utilise = True
        self.utilise_le = datetime.utcnow()


class RevocationLog(Base):
    """Journal d'audit des révocations (sans contenu de message)."""
    __tablename__ = "revocation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_matricule = Column(String(50), ForeignKey("agents.matricule"), nullable=False, index=True)
    revoque_par = Column(String(50), ForeignKey("agents.matricule"), nullable=False, index=True)
    motif = Column(Text, nullable=True)
    date_revocation = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Détails techniques (pour audit)
    keycloak_disabled: bool = Column(Boolean, default=False)
    synapse_deactivated: bool = Column(Boolean, default=False)
    sessions_closed: bool = Column(Boolean, default=False)
    
    # Relations
    agent = relationship("Agent", foreign_keys=[agent_matricule], back_populates="revocations_subies")
    admin = relationship("Agent", foreign_keys=[revoque_par], back_populates="revocations_initiees")

    # Index composés pour requêtes fréquentes
    __table_args__ = (
        Index("ix_revocation_agent_date", "agent_matricule", "date_revocation"),
        Index("ix_revocation_admin_date", "revoque_par", "date_revocation"),
    )
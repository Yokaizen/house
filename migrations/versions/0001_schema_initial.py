"""schema initial

Revision ID: 0001
Revises:
Create Date: 2026-10-13 06:03:26.111211
"""
from alembic import op
import sqlalchemy as sa


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('etablissements',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=30), nullable=False),
    sa.Column('nom', sa.String(length=120), nullable=False),
    sa.Column('adresse_numero', sa.String(length=20), nullable=True),
    sa.Column('adresse_voie', sa.String(length=200), nullable=True),
    sa.Column('adresse_complement', sa.String(length=200), nullable=True),
    sa.Column('code_postal', sa.String(length=10), nullable=True),
    sa.Column('ville', sa.String(length=120), nullable=True),
    sa.Column('latitude', sa.Float(), nullable=True),
    sa.Column('longitude', sa.Float(), nullable=True),
    sa.Column('rayon_m', sa.Integer(), nullable=False),
    sa.Column('actif', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('code')
    )
    op.create_table('parametres',
    sa.Column('cle', sa.String(length=60), nullable=False),
    sa.Column('valeur', sa.JSON(), nullable=True),
    sa.PrimaryKeyConstraint('cle')
    )
    op.create_table('utilisateurs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('matricule', sa.String(length=30), nullable=False),
    sa.Column('nom', sa.String(length=120), nullable=False),
    sa.Column('prenom', sa.String(length=120), nullable=False),
    sa.Column('email', sa.String(length=200), nullable=True),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('etablissement_id', sa.Integer(), nullable=True),
    sa.Column('manager_id', sa.Integer(), nullable=True),
    sa.Column('heures_hebdo', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('adresse_numero', sa.String(length=20), nullable=True),
    sa.Column('adresse_voie', sa.String(length=200), nullable=True),
    sa.Column('adresse_complement', sa.String(length=200), nullable=True),
    sa.Column('code_postal', sa.String(length=10), nullable=True),
    sa.Column('ville', sa.String(length=120), nullable=True),
    sa.Column('domicile_lat', sa.Float(), nullable=True),
    sa.Column('domicile_lon', sa.Float(), nullable=True),
    sa.Column('domicile_rayon_m', sa.Integer(), nullable=True),
    sa.Column('teletravail_autorise', sa.Boolean(), nullable=False),
    sa.Column('mot_de_passe_hash', sa.String(length=255), nullable=True),
    sa.Column('doit_changer_mdp', sa.Boolean(), nullable=False),
    sa.Column('echecs_connexion', sa.Integer(), nullable=False),
    sa.Column('bloque_jusqu_a', sa.DateTime(timezone=True), nullable=True),
    sa.Column('derniere_connexion', sa.DateTime(timezone=True), nullable=True),
    sa.Column('actif', sa.Boolean(), nullable=False),
    sa.Column('date_sortie', sa.Date(), nullable=True),
    sa.Column('cree_le', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['etablissement_id'], ['etablissements.id'], ),
    sa.ForeignKeyConstraint(['manager_id'], ['utilisateurs.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    with op.batch_alter_table('utilisateurs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_utilisateurs_matricule'), ['matricule'], unique=True)

    op.create_table('audit',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('horodatage', sa.DateTime(timezone=True), nullable=False),
    sa.Column('acteur_id', sa.Integer(), nullable=True),
    sa.Column('action', sa.String(length=50), nullable=False),
    sa.Column('cible_type', sa.String(length=30), nullable=False),
    sa.Column('cible_id', sa.Integer(), nullable=True),
    sa.Column('avant', sa.JSON(), nullable=True),
    sa.Column('apres', sa.JSON(), nullable=True),
    sa.ForeignKeyConstraint(['acteur_id'], ['utilisateurs.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('audit', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_audit_horodatage'), ['horodatage'], unique=False)

    op.create_table('pointages',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('utilisateur_id', sa.Integer(), nullable=False),
    sa.Column('type', sa.String(length=10), nullable=False),
    sa.Column('horodatage', sa.DateTime(timezone=True), nullable=False),
    sa.Column('source', sa.String(length=15), nullable=False),
    sa.Column('zone_statut', sa.String(length=20), nullable=False),
    sa.Column('appareil', sa.String(length=15), nullable=True),
    sa.Column('precision_m', sa.Integer(), nullable=True),
    sa.Column('motif', sa.Text(), nullable=True),
    sa.Column('saisi_le', sa.DateTime(timezone=True), nullable=False),
    sa.Column('statut_validation', sa.String(length=15), nullable=False),
    sa.Column('valide_par_id', sa.Integer(), nullable=True),
    sa.Column('valide_le', sa.DateTime(timezone=True), nullable=True),
    sa.Column('commentaire_validation', sa.Text(), nullable=True),
    sa.Column('cree_par_id', sa.Integer(), nullable=True),
    sa.Column('modifie_par_id', sa.Integer(), nullable=True),
    sa.Column('modifie_le', sa.DateTime(timezone=True), nullable=True),
    sa.Column('relance_envoyee', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['cree_par_id'], ['utilisateurs.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['modifie_par_id'], ['utilisateurs.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['utilisateur_id'], ['utilisateurs.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['valide_par_id'], ['utilisateurs.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('pointages', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_pointages_horodatage'), ['horodatage'], unique=False)
        batch_op.create_index(batch_op.f('ix_pointages_utilisateur_id'), ['utilisateur_id'], unique=False)

    op.create_table('sessions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('csrf_token', sa.String(length=64), nullable=False),
    sa.Column('utilisateur_id', sa.Integer(), nullable=False),
    sa.Column('cree_le', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expire_le', sa.DateTime(timezone=True), nullable=False),
    sa.Column('vu_le', sa.DateTime(timezone=True), nullable=False),
    sa.Column('user_agent', sa.String(length=300), nullable=True),
    sa.ForeignKeyConstraint(['utilisateur_id'], ['utilisateurs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('sessions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_sessions_token_hash'), ['token_hash'], unique=True)



def downgrade() -> None:
    with op.batch_alter_table('sessions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_sessions_token_hash'))

    op.drop_table('sessions')
    with op.batch_alter_table('pointages', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_pointages_utilisateur_id'))
        batch_op.drop_index(batch_op.f('ix_pointages_horodatage'))

    op.drop_table('pointages')
    with op.batch_alter_table('audit', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_audit_horodatage'))

    op.drop_table('audit')
    with op.batch_alter_table('utilisateurs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_utilisateurs_matricule'))

    op.drop_table('utilisateurs')
    op.drop_table('parametres')
    op.drop_table('etablissements')

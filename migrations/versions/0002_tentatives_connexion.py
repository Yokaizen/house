"""tentatives de connexion par adresse IP

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-22 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('tentatives_connexion',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('horodatage', sa.DateTime(timezone=True), nullable=False),
    sa.Column('adresse_ip', sa.String(length=45), nullable=False),
    sa.Column('identifiant', sa.String(length=200), nullable=False),
    sa.Column('utilisateur_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['utilisateur_id'], ['utilisateurs.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('tentatives_connexion', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_tentatives_connexion_adresse_ip'), ['adresse_ip'], unique=False)
        batch_op.create_index(batch_op.f('ix_tentatives_connexion_horodatage'), ['horodatage'], unique=False)
        batch_op.create_index(batch_op.f('ix_tentatives_connexion_utilisateur_id'), ['utilisateur_id'], unique=False)

    # Remplacé par tentatives_connexion : le compteur par compte permettait à n'importe qui
    # de bloquer un salarié.
    with op.batch_alter_table('utilisateurs', schema=None) as batch_op:
        batch_op.drop_column('echecs_connexion')


def downgrade() -> None:
    with op.batch_alter_table('utilisateurs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('echecs_connexion', sa.Integer(), nullable=False, server_default='0'))

    with op.batch_alter_table('tentatives_connexion', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_tentatives_connexion_utilisateur_id'))
        batch_op.drop_index(batch_op.f('ix_tentatives_connexion_horodatage'))
        batch_op.drop_index(batch_op.f('ix_tentatives_connexion_adresse_ip'))

    op.drop_table('tentatives_connexion')

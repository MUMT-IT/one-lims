"""added speciment container number

Revision ID: 411a9930b05d
Revises: a86e5d610807
Create Date: 2024-10-29 04:24:49.022422

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '411a9930b05d'
down_revision = 'a86e5d610807'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('lab_specimen_containers', schema=None) as batch_op:
        batch_op.add_column(sa.Column('number', sa.Integer(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('lab_specimen_containers', schema=None) as batch_op:
        batch_op.drop_column('number')

    # ### end Alembic commands ###

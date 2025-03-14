"""added composite unique keys

Revision ID: 75683cf127bb
Revises: fadaab7d39ba
Create Date: 2025-03-13 11:38:21.165821

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '75683cf127bb'
down_revision = 'fadaab7d39ba'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('lab_test_profiles', schema=None) as batch_op:
        batch_op.create_unique_constraint('lab_test_profiles_lab_id_code_unique', ['lab_id', 'code'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('lab_test_profiles', schema=None) as batch_op:
        batch_op.drop_constraint('lab_test_profiles_lab_id_code_unique', type_='unique')

    # ### end Alembic commands ###

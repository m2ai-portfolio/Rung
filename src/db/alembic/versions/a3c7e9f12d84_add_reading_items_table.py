"""add_reading_items_table

Revision ID: a3c7e9f12d84
Revises: 1eb9a81756bc
Create Date: 2026-02-09 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3c7e9f12d84'
down_revision: Union[str, Sequence[str], None] = '1eb9a81756bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add reading_items table for therapy reading list feature."""
    op.create_table('reading_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('added_by_role', sa.Enum(
            'CLIENT', 'THERAPIST',
            name='addedbyrole'
        ), nullable=False),
        sa.Column('added_by_user_id', sa.UUID(), nullable=False),
        sa.Column('url', sa.String(length=2048), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('source', sa.String(length=255), nullable=True),
        sa.Column('notes_encrypted', sa.LargeBinary(), nullable=True),
        sa.Column('discuss_in_session', sa.Boolean(), nullable=False),
        sa.Column('is_assignment', sa.Boolean(), nullable=False),
        sa.Column('assignment_notes_encrypted', sa.LargeBinary(), nullable=True),
        sa.Column('status', sa.Enum(
            'UNREAD', 'READING', 'COMPLETED', 'DISCUSSED',
            name='readingstatus'
        ), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('reading_items', schema=None) as batch_op:
        batch_op.create_index('ix_reading_items_client_id', ['client_id'], unique=False)
        batch_op.create_index('ix_reading_items_client_discuss', ['client_id', 'discuss_in_session'], unique=False)
        batch_op.create_index('ix_reading_items_client_status', ['client_id', 'status'], unique=False)


def downgrade() -> None:
    """Remove reading_items table."""
    with op.batch_alter_table('reading_items', schema=None) as batch_op:
        batch_op.drop_index('ix_reading_items_client_status')
        batch_op.drop_index('ix_reading_items_client_discuss')
        batch_op.drop_index('ix_reading_items_client_id')

    op.drop_table('reading_items')

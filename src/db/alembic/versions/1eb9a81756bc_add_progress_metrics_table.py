"""add_progress_metrics_table

Revision ID: 1eb9a81756bc
Revises: b1f616ccca62
Create Date: 2026-02-06 22:37:29.922605

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1eb9a81756bc'
down_revision: Union[str, Sequence[str], None] = 'b1f616ccca62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add progress_metrics table for tracking client progress analytics."""
    op.create_table('progress_metrics',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=True),
        sa.Column('metric_type', sa.Enum(
            'SESSION_ENGAGEMENT', 'FRAMEWORK_PROGRESS', 'SPRINT_COMPLETION',
            'RISK_LEVEL', 'HOMEWORK_COMPLETION',
            name='metrictype'
        ), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('measured_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('progress_metrics', schema=None) as batch_op:
        batch_op.create_index('ix_progress_metrics_client_id', ['client_id'], unique=False)
        batch_op.create_index('ix_progress_metrics_client_type', ['client_id', 'metric_type'], unique=False)
        batch_op.create_index('ix_progress_metrics_metric_type', ['metric_type'], unique=False)


def downgrade() -> None:
    """Remove progress_metrics table."""
    with op.batch_alter_table('progress_metrics', schema=None) as batch_op:
        batch_op.drop_index('ix_progress_metrics_metric_type')
        batch_op.drop_index('ix_progress_metrics_client_type')
        batch_op.drop_index('ix_progress_metrics_client_id')

    op.drop_table('progress_metrics')

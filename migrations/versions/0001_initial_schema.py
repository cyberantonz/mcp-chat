"""Initial schema: agents, chats, chat_messages.

Revision ID: 0001
Revises: None
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("key_hash", sa.String(length=72), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_agents"),
        sa.UniqueConstraint("name", name="uq_agents_name"),
    )
    op.create_table(
        "chats",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_id_1", sa.Uuid(), nullable=False),
        sa.Column("agent_id_2", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_chats"),
        sa.ForeignKeyConstraint(["agent_id_1"], ["agents.id"], name="fk_chats_agent_id_1_agents"),
        sa.ForeignKeyConstraint(["agent_id_2"], ["agents.id"], name="fk_chats_agent_id_2_agents"),
        sa.CheckConstraint("agent_id_1 <> agent_id_2", name="ck_chats_no_self_chat"),
    )
    op.create_index("ix_chats_agent_id_1", "chats", ["agent_id_1"])
    op.create_index("ix_chats_agent_id_2", "chats", ["agent_id_2"])
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("chat_id", sa.Uuid(), nullable=False),
        sa.Column("sender_id", sa.Uuid(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_chat_messages"),
        sa.ForeignKeyConstraint(["chat_id"], ["chats.id"], name="fk_chat_messages_chat_id_chats"),
        sa.ForeignKeyConstraint(["sender_id"], ["agents.id"], name="fk_chat_messages_sender_id_agents"),
    )
    op.create_index("ix_chat_messages_chat_id_created_at_id", "chat_messages", ["chat_id", "created_at", "id"])


def downgrade() -> None:
    raise NotImplementedError("No downgrades allowed. Only forward!")

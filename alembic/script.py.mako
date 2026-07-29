"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision if down_revision else "None"}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${up_revision | repr}
down_revision: Union[str, None] = ${down_revision if down_revision else "None"}
branch_labels: Union[str, Sequence[str], None] = ${branch_labels if branch_labels else "None"}
depends_on: Union[str, Sequence[str], None] = ${depends_on if depends_on else "None"}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}

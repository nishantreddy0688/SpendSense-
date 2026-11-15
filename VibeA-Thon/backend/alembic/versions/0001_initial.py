"""Initial SpendSense schema."""
from alembic import op
import sqlalchemy as sa
revision="0001_initial"
down_revision=None
branch_labels=None
depends_on=None
def upgrade():
    op.create_table("users",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("name",sa.String(100),nullable=False),sa.Column("email",sa.String(255),nullable=False),sa.Column("password_hash",sa.String(255),nullable=False),sa.Column("created_at",sa.DateTime(),nullable=False));op.create_index("ix_users_email","users",["email"],unique=True)
    op.create_table("transactions",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("user_id",sa.Integer(),sa.ForeignKey("users.id",ondelete="CASCADE"),nullable=False),sa.Column("date",sa.Date(),nullable=False),sa.Column("amount",sa.Float(),nullable=False),sa.Column("type",sa.String(10),nullable=False),sa.Column("category",sa.String(80),nullable=False),sa.Column("merchant",sa.String(160),nullable=False),sa.Column("description",sa.String(500),nullable=False),sa.Column("payment_method",sa.String(40),nullable=False),sa.Column("created_at",sa.DateTime(),nullable=False));op.create_index("ix_transactions_user_id","transactions",["user_id"]);op.create_index("ix_transaction_user_date","transactions",["user_id","date"])
    op.create_table("budgets",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("user_id",sa.Integer(),sa.ForeignKey("users.id",ondelete="CASCADE"),nullable=False),sa.Column("month",sa.String(7),nullable=False),sa.Column("category",sa.String(80),nullable=False),sa.Column("amount",sa.Float(),nullable=False));op.create_index("ix_budgets_user_id","budgets",["user_id"]);op.create_index("ix_budget_user_month_category","budgets",["user_id","month","category"],unique=True)
    op.create_table("insights",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("user_id",sa.Integer(),sa.ForeignKey("users.id",ondelete="CASCADE"),nullable=False),sa.Column("title",sa.String(180),nullable=False),sa.Column("detail",sa.String(500),nullable=False),sa.Column("kind",sa.String(30),nullable=False),sa.Column("dismissed",sa.Boolean(),nullable=False));op.create_index("ix_insights_user_id","insights",["user_id"])
    op.create_table("categories",sa.Column("id",sa.Integer(),primary_key=True),sa.Column("name",sa.String(80),nullable=False),sa.Column("color",sa.String(9),nullable=False));op.create_index("ix_categories_name","categories",["name"],unique=True)
    op.create_table("user_preferences",sa.Column("user_id",sa.Integer(),sa.ForeignKey("users.id",ondelete="CASCADE"),primary_key=True),sa.Column("currency",sa.String(3),nullable=False),sa.Column("dark_mode",sa.Boolean(),nullable=False),sa.Column("created_at",sa.DateTime(),nullable=False))
def downgrade():
    op.drop_table("user_preferences");op.drop_index("ix_categories_name",table_name="categories");op.drop_table("categories");op.drop_table("insights");op.drop_table("budgets");op.drop_table("transactions");op.drop_index("ix_users_email",table_name="users");op.drop_table("users")

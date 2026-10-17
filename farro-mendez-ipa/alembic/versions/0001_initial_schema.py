"""initial schema farro mendez ipa

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-10-13 22:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Tabla inventario
    op.create_table(
        'inventario',
        sa.Column('codigo', sa.String(length=50), nullable=False),
        sa.Column('nombre', sa.String(length=200), nullable=False),
        sa.Column('precio', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('stock', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('codigo')
    )
    op.create_index(op.f('ix_inventario_codigo'), 'inventario', ['codigo'], unique=False)

    # 2. Tabla pedidos
    op.create_table(
        'pedidos',
        sa.Column('pedido_id', sa.String(length=50), nullable=False),
        sa.Column('telefono', sa.String(length=30), nullable=False),
        sa.Column('producto_id', sa.String(length=50), nullable=False),
        sa.Column('producto_nombre', sa.String(length=200), nullable=False),
        sa.Column('cantidad', sa.Integer(), nullable=False),
        sa.Column('precio_unitario', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('total', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('estado', sa.String(length=50), nullable=False, server_default='Pendiente de pago'),
        sa.Column('idempotency_key', sa.String(length=64), nullable=False),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('pedido_id')
    )
    op.create_index(op.f('ix_pedidos_pedido_id'), 'pedidos', ['pedido_id'], unique=False)
    op.create_index(op.f('ix_pedidos_telefono'), 'pedidos', ['telefono'], unique=False)
    op.create_index(op.f('ix_pedidos_idempotency_key'), 'pedidos', ['idempotency_key'], unique=True)

    # 3. Tabla conversaciones
    op.create_table(
        'conversaciones',
        sa.Column('telefono', sa.String(length=30), nullable=False),
        sa.Column('estado', sa.String(length=50), nullable=False, server_default='consulta'),
        sa.Column('producto_id', sa.String(length=50), nullable=True),
        sa.Column('producto_nombre', sa.String(length=200), nullable=True),
        sa.Column('cantidad', sa.Integer(), nullable=True),
        sa.Column('precio', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('pedido_id', sa.String(length=50), nullable=True),
        sa.Column('intentos', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['producto_id'], ['inventario.codigo'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['pedido_id'], ['pedidos.pedido_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('telefono')
    )
    op.create_index(op.f('ix_conversaciones_telefono'), 'conversaciones', ['telefono'], unique=False)

    # 4. Tabla ventas
    op.create_table(
        'ventas',
        sa.Column('venta_id', sa.String(length=50), nullable=False),
        sa.Column('pedido_id', sa.String(length=50), nullable=False),
        sa.Column('telefono', sa.String(length=30), nullable=False),
        sa.Column('monto', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('operacion', sa.String(length=100), nullable=False),
        sa.Column('estado', sa.String(length=50), nullable=False, server_default='Pagado'),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['pedido_id'], ['pedidos.pedido_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('venta_id')
    )
    op.create_index(op.f('ix_ventas_venta_id'), 'ventas', ['venta_id'], unique=False)
    op.create_index(op.f('ix_ventas_pedido_id'), 'ventas', ['pedido_id'], unique=False)
    op.create_index(op.f('ix_ventas_telefono'), 'ventas', ['telefono'], unique=False)

    # 5. Tabla cola_fallidos
    op.create_table(
        'cola_fallidos',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('telefono', sa.String(length=30), nullable=False),
        sa.Column('mensaje_original', sa.Text(), nullable=True),
        sa.Column('motivo', sa.String(length=100), nullable=False),
        sa.Column('carga_original', sa.JSON(), nullable=True),
        sa.Column('estado', sa.String(length=50), nullable=False, server_default='pendiente'),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cola_fallidos_telefono'), 'cola_fallidos', ['telefono'], unique=False)

    # 6. Tabla casos_escalados
    op.create_table(
        'casos_escalados',
        sa.Column('caso_id', sa.String(length=50), nullable=False),
        sa.Column('telefono', sa.String(length=30), nullable=False),
        sa.Column('pedido_id', sa.String(length=50), nullable=True),
        sa.Column('motivo', sa.String(length=200), nullable=False),
        sa.Column('creado_en', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('caso_id')
    )
    op.create_index(op.f('ix_casos_escalados_caso_id'), 'casos_escalados', ['caso_id'], unique=False)
    op.create_index(op.f('ix_casos_escalados_pedido_id'), 'casos_escalados', ['pedido_id'], unique=False)
    op.create_index(op.f('ix_casos_escalados_telefono'), 'casos_escalados', ['telefono'], unique=False)


def downgrade() -> None:
    op.drop_table('casos_escalados')
    op.drop_table('cola_fallidos')
    op.drop_table('ventas')
    op.drop_table('conversaciones')
    op.drop_table('pedidos')
    op.drop_table('inventario')

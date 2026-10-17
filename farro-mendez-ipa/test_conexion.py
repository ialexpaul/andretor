import asyncio
import sys
from sqlalchemy import text

# Soporte para salida UTF-8 en consolas Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.database import engine

async def test_conexion():
    try:
        async with engine.connect() as conn:
            print("==========================================")
            print("✅ CONEXIÓN EXITOSA A SUPABASE")
            print("==========================================")
            
            # Obtener datos de la base de datos
            res = await conn.execute(text("SELECT current_database(), current_user"))
            db, user = res.fetchone()
            print(f"Base de datos: {db}")
            print(f"Usuario autenticado: {user}")
            
            # Consultar tablas en el esquema public
            res_tables = await conn.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"
            ))
            tables = [r[0] for r in res_tables.fetchall()]
            print(f"\nTablas encontradas en el schema 'public' ({len(tables)} tablas):")
            for t in tables:
                print(f"  📁 {t}")
            print("==========================================")
            await conn.close()
    except Exception as e:
        print("==========================================")
        print(f"❌ Error de conexion: {e}")
        print("==========================================")

if __name__ == "__main__":
    asyncio.run(test_conexion())

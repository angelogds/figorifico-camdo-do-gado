"""Cria usuários iniciais para Manutenção Frigorífico Campo do Gado."""
import asyncio, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))
from backend.server import db, hash_password

USERS = [
    ('Administrador Angelo', 'angelo@campodogado.local', 'angelo@123', 'admin'),
    ('Encarregado de Manutenção', 'encarregado@campodogado.com.br', 'encarregado123', 'encarregado'),
    ('Mecânico Campo do Gado', 'mecanico@campodogado.com.br', 'mecanico123', 'mecanico'),
]
async def main():
    for nome,email,senha,role in USERS:
        await db.users.update_one({'email':email},{'$setOnInsert':{'id':__import__('uuid').uuid4().hex,'nome':nome,'email':email,'senha_hash':hash_password(senha),'role':role,'created_at':__import__('datetime').datetime.now(__import__('datetime').timezone.utc)}},upsert=True)
        print(f'Usuário disponível: {email} ({role})')
if __name__ == '__main__': asyncio.run(main())

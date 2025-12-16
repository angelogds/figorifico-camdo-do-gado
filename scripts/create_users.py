#!/usr/bin/env python3
"""Script to create initial users for RecycleFlow system"""

import asyncio
import sys
import os
sys.path.insert(0, '/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
import bcrypt
from datetime import datetime, timezone
import uuid

# Load environment
ROOT_DIR = Path('/app/backend')
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

async def create_users():
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    users = [
        {
            'id': str(uuid.uuid4()),
            'nome': 'Admin Sistema',
            'email': 'admin@recycleflow.com',
            'senha_hash': hash_password('admin123'),
            'role': 'admin',
            'created_at': datetime.now(timezone.utc).isoformat()
        },
        {
            'id': str(uuid.uuid4()),
            'nome': 'Portaria João',
            'email': 'portaria@recycleflow.com',
            'senha_hash': hash_password('portaria123'),
            'role': 'portaria',
            'created_at': datetime.now(timezone.utc).isoformat()
        },
        {
            'id': str(uuid.uuid4()),
            'nome': 'Operador Carlos',
            'email': 'operador@recycleflow.com',
            'senha_hash': hash_password('operador123'),
            'role': 'operador',
            'created_at': datetime.now(timezone.utc).isoformat()
        }
    ]
    
    for user in users:
        existing = await db.users.find_one({'email': user['email']})
        if existing:
            print(f"✓ Usuário {user['email']} já existe")
        else:
            await db.users.insert_one(user)
            print(f"✓ Usuário {user['email']} criado com sucesso")
    
    client.close()
    print("\n✓ Usuários criados com sucesso!")
    print("\nCredenciais:")
    print("Admin: admin@recycleflow.com / admin123")
    print("Portaria: portaria@recycleflow.com / portaria123")
    print("Operador: operador@recycleflow.com / operador123")

if __name__ == '__main__':
    asyncio.run(create_users())

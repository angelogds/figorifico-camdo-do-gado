#!/usr/bin/env python3
"""Script para criar frotas de exemplo"""

import asyncio
import sys
import os
sys.path.insert(0, '/app/backend')

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime, timezone
import uuid

# Load environment
ROOT_DIR = Path('/app/backend')
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']

async def criar_frotas():
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Get portaria user
    portaria = await db.users.find_one({'role': 'portaria'}, {'_id': 0})
    
    if not portaria:
        print("❌ Usuário da portaria não encontrado")
        return
    
    print("🚛 Criando 10 frotas com 10 toneladas cada...\n")
    
    for i in range(1, 11):
        entry = {
            'id': str(uuid.uuid4()),
            'numero_frota': f'FROTA-{i:03d}',
            'toneladas_declaradas': 10.0,
            'arrival_at': datetime.now(timezone.utc).isoformat(),
            'portaria_user_id': portaria['id'],
            'portaria_user_name': portaria['nome'],
            'status': 'aguardando_descarregamento'
        }
        
        await db.entries.insert_one(entry)
        print(f"✓ {entry['numero_frota']} - 10.0 toneladas")
    
    client.close()
    print(f"\n✅ 10 frotas criadas com sucesso!")
    print(f"📊 Total no pátio: 100.0 toneladas")

if __name__ == '__main__':
    asyncio.run(criar_frotas())

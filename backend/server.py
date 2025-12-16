from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Literal
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Secret
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# ==================== ENUMS ====================
class UserRole(str, Enum):
    PORTARIA = "portaria"
    OPERADOR = "operador"
    ADMIN = "admin"

class DigestorStatus(str, Enum):
    LIVRE = "livre"
    TRITURANDO = "triturando"
    COZINHANDO = "cozinhando"
    PRONTO = "pronto"
    ALERTA = "alerta"
    MANUTENCAO = "manutencao"

class CycleStatus(str, Enum):
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDO = "concluido"
    INTERROMPIDO = "interrompido"

# ==================== MODELS ====================
class UserBase(BaseModel):
    nome: str
    email: EmailStr
    role: UserRole

class UserCreate(UserBase):
    senha: str

class User(UserBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserLogin(BaseModel):
    email: str
    senha: str

class TokenResponse(BaseModel):
    token: str
    user: User

class EntryCreate(BaseModel):
    numero_frota: str
    toneladas_declaradas: float

class Entry(EntryCreate):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    arrival_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    portaria_user_id: str
    portaria_user_name: str
    status: str = "aguardando_descarregamento"

class DescarregamentoCreate(BaseModel):
    entry_id: str
    toneladas_efetivas: float

class Descarregamento(DescarregamentoCreate):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    start_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_at: Optional[datetime] = None
    operador_id: str
    operador_name: str
    tempo_minutos: Optional[float] = None

class TrituracaoCreate(BaseModel):
    descarregamento_id: str
    digestor_id: int
    toneladas: float

class Trituracao(TrituracaoCreate):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    start_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_at: Optional[datetime] = None
    operador_id: str
    operador_name: str
    tempo_minutos: Optional[float] = None

class CozimentoCreate(BaseModel):
    trituracao_id: str
    digestor_id: int

class Cozimento(CozimentoCreate):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    start_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    end_at: Optional[datetime] = None
    operador_id: str
    operador_name: str
    tempo_minutos: Optional[float] = None

class Digestor(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: int
    nome: str
    status: DigestorStatus = DigestorStatus.LIVRE
    current_cycle_id: Optional[str] = None
    current_operation_start: Optional[datetime] = None
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_ciclos: int = 0
    tempo_medio_trituracao: float = 0.0
    tempo_medio_cozimento: float = 0.0

class AlertaCreate(BaseModel):
    digestor_id: int
    tipo: str
    mensagem: str

class Alerta(AlertaCreate):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolvido: bool = False
    resolved_at: Optional[datetime] = None

class ManutencaoCreate(BaseModel):
    digestor_id: int
    descricao: str
    tipo: str

class Manutencao(ManutencaoCreate):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    responsavel_id: str
    responsavel_name: str
    concluida: bool = False
    concluded_at: Optional[datetime] = None

# ==================== AUTH HELPERS ====================
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, role: str) -> str:
    payload = {
        'sub': user_id,
        'role': role,
        'exp': datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get('sub')
        
        user_doc = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user_doc:
            raise HTTPException(status_code=401, detail="Usuário não encontrado")
        
        if isinstance(user_doc.get('created_at'), str):
            user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
            
        return User(**user_doc)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

# ==================== ROUTES ====================

# --- AUTH ---
@api_router.post("/auth/register", response_model=User)
async def register(user_create: UserCreate):
    # Check if user exists
    existing = await db.users.find_one({"email": user_create.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    user = User(**user_create.model_dump(exclude={'senha'}))
    doc = user.model_dump()
    doc['senha_hash'] = hash_password(user_create.senha)
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.users.insert_one(doc)
    return user

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user_doc = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    
    if not verify_password(credentials.senha, user_doc['senha_hash']):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    
    if isinstance(user_doc.get('created_at'), str):
        user_doc['created_at'] = datetime.fromisoformat(user_doc['created_at'])
    
    user = User(**{k: v for k, v in user_doc.items() if k != 'senha_hash'})
    token = create_token(user.id, user.role)
    
    return TokenResponse(token=token, user=user)

@api_router.get("/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# --- ENTRIES (Portaria) ---
@api_router.post("/entries", response_model=Entry)
async def create_entry(entry_create: EntryCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.PORTARIA and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Apenas portaria pode registrar entradas")
    
    entry = Entry(
        **entry_create.model_dump(),
        portaria_user_id=current_user.id,
        portaria_user_name=current_user.nome
    )
    doc = entry.model_dump()
    doc['arrival_at'] = doc['arrival_at'].isoformat()
    
    await db.entries.insert_one(doc)
    return entry

@api_router.get("/entries", response_model=List[Entry])
async def list_entries(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    query = {}
    if status:
        query['status'] = status
    
    entries = await db.entries.find(query, {"_id": 0}).sort("arrival_at", -1).to_list(100)
    
    for entry in entries:
        if isinstance(entry.get('arrival_at'), str):
            entry['arrival_at'] = datetime.fromisoformat(entry['arrival_at'])
    
    return entries

# --- DESCARREGAMENTO (Operador) ---
@api_router.post("/descarregamento/start", response_model=Descarregamento)
async def start_descarregamento(
    data: DescarregamentoCreate,
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.OPERADOR and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Apenas operadores podem descarregar")
    
    # Verify entry exists
    entry = await db.entries.find_one({"id": data.entry_id}, {"_id": 0})
    if not entry:
        raise HTTPException(status_code=404, detail="Entrada não encontrada")
    
    descarregamento = Descarregamento(
        **data.model_dump(),
        operador_id=current_user.id,
        operador_name=current_user.nome
    )
    doc = descarregamento.model_dump()
    doc['start_at'] = doc['start_at'].isoformat()
    
    await db.descarregamentos.insert_one(doc)
    await db.entries.update_one({"id": data.entry_id}, {"$set": {"status": "descarregando"}})
    
    return descarregamento

@api_router.post("/descarregamento/{descarregamento_id}/finish")
async def finish_descarregamento(
    descarregamento_id: str,
    current_user: User = Depends(get_current_user)
):
    descarregamento = await db.descarregamentos.find_one({"id": descarregamento_id}, {"_id": 0})
    if not descarregamento:
        raise HTTPException(status_code=404, detail="Descarregamento não encontrado")
    
    end_at = datetime.now(timezone.utc)
    start_at = datetime.fromisoformat(descarregamento['start_at']) if isinstance(descarregamento['start_at'], str) else descarregamento['start_at']
    tempo_minutos = (end_at - start_at).total_seconds() / 60
    
    await db.descarregamentos.update_one(
        {"id": descarregamento_id},
        {"$set": {
            "end_at": end_at.isoformat(),
            "tempo_minutos": tempo_minutos
        }}
    )
    
    await db.entries.update_one(
        {"id": descarregamento['entry_id']},
        {"$set": {"status": "descarregado"}}
    )
    
    return {"message": "Descarregamento finalizado", "tempo_minutos": tempo_minutos}

@api_router.get("/descarregamento")
async def list_descarregamentos(current_user: User = Depends(get_current_user)):
    descarregamentos = await db.descarregamentos.find({}, {"_id": 0}).sort("start_at", -1).to_list(100)
    
    for desc in descarregamentos:
        if isinstance(desc.get('start_at'), str):
            desc['start_at'] = datetime.fromisoformat(desc['start_at'])
        if desc.get('end_at') and isinstance(desc['end_at'], str):
            desc['end_at'] = datetime.fromisoformat(desc['end_at'])
    
    return descarregamentos

# --- TRITURACAO (Operador) ---
@api_router.post("/trituracao/start", response_model=Trituracao)
async def start_trituracao(
    data: TrituracaoCreate,
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.OPERADOR and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Apenas operadores podem triturar")
    
    # Check if digestor is available
    digestor = await db.digestors.find_one({"id": data.digestor_id}, {"_id": 0})
    if not digestor:
        raise HTTPException(status_code=404, detail="Digestor não encontrado")
    
    if digestor['status'] != DigestorStatus.LIVRE:
        raise HTTPException(status_code=400, detail=f"Digestor {data.digestor_id} não está livre")
    
    trituracao = Trituracao(
        **data.model_dump(),
        operador_id=current_user.id,
        operador_name=current_user.nome
    )
    doc = trituracao.model_dump()
    doc['start_at'] = doc['start_at'].isoformat()
    
    await db.trituracoes.insert_one(doc)
    
    # Update digestor status
    await db.digestors.update_one(
        {"id": data.digestor_id},
        {"$set": {
            "status": DigestorStatus.TRITURANDO,
            "current_cycle_id": trituracao.id,
            "current_operation_start": trituracao.start_at.isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return trituracao

@api_router.post("/trituracao/{trituracao_id}/finish")
async def finish_trituracao(
    trituracao_id: str,
    current_user: User = Depends(get_current_user)
):
    trituracao = await db.trituracoes.find_one({"id": trituracao_id}, {"_id": 0})
    if not trituracao:
        raise HTTPException(status_code=404, detail="Trituração não encontrada")
    
    end_at = datetime.now(timezone.utc)
    start_at = datetime.fromisoformat(trituracao['start_at']) if isinstance(trituracao['start_at'], str) else trituracao['start_at']
    tempo_minutos = (end_at - start_at).total_seconds() / 60
    
    await db.trituracoes.update_one(
        {"id": trituracao_id},
        {"$set": {
            "end_at": end_at.isoformat(),
            "tempo_minutos": tempo_minutos
        }}
    )
    
    return {"message": "Trituração finalizada", "tempo_minutos": tempo_minutos, "trituracao_id": trituracao_id}

# --- COZIMENTO (Operador) ---
@api_router.post("/cozimento/start", response_model=Cozimento)
async def start_cozimento(
    data: CozimentoCreate,
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.OPERADOR and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Apenas operadores podem iniciar cozimento")
    
    cozimento = Cozimento(
        **data.model_dump(),
        operador_id=current_user.id,
        operador_name=current_user.nome
    )
    doc = cozimento.model_dump()
    doc['start_at'] = doc['start_at'].isoformat()
    
    await db.cozimentos.insert_one(doc)
    
    # Update digestor status
    await db.digestors.update_one(
        {"id": data.digestor_id},
        {"$set": {
            "status": DigestorStatus.COZINHANDO,
            "current_operation_start": cozimento.start_at.isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return cozimento

@api_router.get("/cozimentos")
async def list_cozimentos(current_user: User = Depends(get_current_user)):
    cozimentos = await db.cozimentos.find({}, {"_id": 0}).sort("start_at", -1).to_list(100)
    
    for coz in cozimentos:
        if isinstance(coz.get('start_at'), str):
            coz['start_at'] = datetime.fromisoformat(coz['start_at'])
        if coz.get('end_at') and isinstance(coz['end_at'], str):
            coz['end_at'] = datetime.fromisoformat(coz['end_at'])
    
    return cozimentos

@api_router.post("/cozimento/{cozimento_id}/finish")
async def finish_cozimento(
    cozimento_id: str,
    current_user: User = Depends(get_current_user)
):
    cozimento = await db.cozimentos.find_one({"id": cozimento_id}, {"_id": 0})
    if not cozimento:
        raise HTTPException(status_code=404, detail="Cozimento não encontrado")
    
    end_at = datetime.now(timezone.utc)
    start_at = datetime.fromisoformat(cozimento['start_at']) if isinstance(cozimento['start_at'], str) else cozimento['start_at']
    tempo_minutos = (end_at - start_at).total_seconds() / 60
    
    await db.cozimentos.update_one(
        {"id": cozimento_id},
        {"$set": {
            "end_at": end_at.isoformat(),
            "tempo_minutos": tempo_minutos,
            "pronto_para_descarregar_at": end_at.isoformat()
        }}
    )
    
    # Update digestor - mark as ready for unloading
    digestor = await db.digestors.find_one({"id": cozimento['digestor_id']}, {"_id": 0})
    
    # Calculate new average times
    trituracao = await db.trituracoes.find_one({"id": cozimento['trituracao_id']}, {"_id": 0})
    
    total_ciclos = digestor.get('total_ciclos', 0) + 1
    tempo_medio_cozimento_old = digestor.get('tempo_medio_cozimento', 0)
    tempo_medio_trituracao_old = digestor.get('tempo_medio_trituracao', 0)
    
    # New averages
    tempo_medio_cozimento = ((tempo_medio_cozimento_old * (total_ciclos - 1)) + tempo_minutos) / total_ciclos
    
    if trituracao and trituracao.get('tempo_minutos'):
        tempo_medio_trituracao = ((tempo_medio_trituracao_old * (total_ciclos - 1)) + trituracao['tempo_minutos']) / total_ciclos
    else:
        tempo_medio_trituracao = tempo_medio_trituracao_old
    
    await db.digestors.update_one(
        {"id": cozimento['digestor_id']},
        {"$set": {
            "status": DigestorStatus.PRONTO,
            "current_cycle_id": cozimento_id,
            "current_operation_start": end_at.isoformat(),
            "pronto_para_descarregar_at": end_at.isoformat(),
            "last_updated": end_at.isoformat(),
            "total_ciclos": total_ciclos,
            "tempo_medio_cozimento": tempo_medio_cozimento,
            "tempo_medio_trituracao": tempo_medio_trituracao
        }}
    )
    
    return {"message": "Cozimento finalizado", "tempo_minutos": tempo_minutos}

# --- DESCARREGAR DIGESTOR ---
class DescarregarDigestorCreate(BaseModel):
    digestor_id: int
    observacao: Optional[str] = None

@api_router.post("/digestor/descarregar")
async def descarregar_digestor(
    data: DescarregarDigestorCreate,
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.OPERADOR and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Apenas operadores podem descarregar")
    
    digestor = await db.digestors.find_one({"id": data.digestor_id}, {"_id": 0})
    if not digestor:
        raise HTTPException(status_code=404, detail="Digestor não encontrado")
    
    if digestor['status'] != DigestorStatus.PRONTO:
        raise HTTPException(status_code=400, detail="Digestor não está pronto para descarregar")
    
    # Calculate downtime (tempo parado após ficar pronto)
    pronto_at = datetime.fromisoformat(digestor['pronto_para_descarregar_at'])
    descarregado_at = datetime.now(timezone.utc)
    tempo_parado_minutos = (descarregado_at - pronto_at).total_seconds() / 60
    
    # Create descarregamento record
    descarregamento_record = {
        "id": str(uuid.uuid4()),
        "digestor_id": data.digestor_id,
        "pronto_at": pronto_at.isoformat(),
        "descarregado_at": descarregado_at.isoformat(),
        "tempo_parado_minutos": tempo_parado_minutos,
        "operador_id": current_user.id,
        "operador_name": current_user.nome,
        "observacao": data.observacao,
        "cozimento_id": digestor.get('current_cycle_id')
    }
    
    await db.descarregamentos_digestor.insert_one(descarregamento_record)
    
    # Update digestor to LIVRE
    await db.digestors.update_one(
        {"id": data.digestor_id},
        {"$set": {
            "status": DigestorStatus.LIVRE,
            "current_cycle_id": None,
            "current_operation_start": None,
            "pronto_para_descarregar_at": None,
            "last_updated": descarregado_at.isoformat()
        }}
    )
    
    return {
        "message": "Digestor descarregado com sucesso",
        "tempo_parado_minutos": tempo_parado_minutos
    }

# --- DIGESTORS ---
@api_router.get("/digestors", response_model=List[Digestor])
async def list_digestors(current_user: User = Depends(get_current_user)):
    digestors = await db.digestors.find({}, {"_id": 0}).sort("id", 1).to_list(10)
    
    for dig in digestors:
        if isinstance(dig.get('last_updated'), str):
            dig['last_updated'] = datetime.fromisoformat(dig['last_updated'])
        if dig.get('current_operation_start') and isinstance(dig['current_operation_start'], str):
            dig['current_operation_start'] = datetime.fromisoformat(dig['current_operation_start'])
    
    return digestors

@api_router.post("/digestors/init")
async def init_digestors(current_user: User = Depends(get_current_user)):
    """Initialize 4 digestors if they don't exist"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Apenas admin pode inicializar digestores")
    
    existing_count = await db.digestors.count_documents({})
    if existing_count > 0:
        return {"message": f"Já existem {existing_count} digestores"}
    
    digestors = []
    for i in range(1, 5):
        digestor = Digestor(id=i, nome=f"Digestor {i}")
        doc = digestor.model_dump()
        doc['last_updated'] = doc['last_updated'].isoformat()
        digestors.append(doc)
    
    await db.digestors.insert_many(digestors)
    return {"message": "4 digestores criados com sucesso"}

# --- ALERTAS ---
@api_router.post("/alertas", response_model=Alerta)
async def create_alerta(
    alerta_create: AlertaCreate,
    current_user: User = Depends(get_current_user)
):
    alerta = Alerta(**alerta_create.model_dump())
    doc = alerta.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.alertas.insert_one(doc)
    
    # Update digestor status
    await db.digestors.update_one(
        {"id": alerta_create.digestor_id},
        {"$set": {"status": DigestorStatus.ALERTA}}
    )
    
    return alerta

@api_router.get("/alertas", response_model=List[Alerta])
async def list_alertas(
    resolvido: Optional[bool] = None,
    current_user: User = Depends(get_current_user)
):
    query = {}
    if resolvido is not None:
        query['resolvido'] = resolvido
    
    alertas = await db.alertas.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    for alerta in alertas:
        if isinstance(alerta.get('created_at'), str):
            alerta['created_at'] = datetime.fromisoformat(alerta['created_at'])
        if alerta.get('resolved_at') and isinstance(alerta['resolved_at'], str):
            alerta['resolved_at'] = datetime.fromisoformat(alerta['resolved_at'])
    
    return alertas

@api_router.post("/alertas/{alerta_id}/resolver")
async def resolver_alerta(
    alerta_id: str,
    current_user: User = Depends(get_current_user)
):
    alerta = await db.alertas.find_one({"id": alerta_id}, {"_id": 0})
    if not alerta:
        raise HTTPException(status_code=404, detail="Alerta não encontrado")
    
    await db.alertas.update_one(
        {"id": alerta_id},
        {"$set": {
            "resolvido": True,
            "resolved_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Check if digestor has other active alerts
    other_alerts = await db.alertas.count_documents({
        "digestor_id": alerta['digestor_id'],
        "resolvido": False,
        "id": {"$ne": alerta_id}
    })
    
    if other_alerts == 0:
        await db.digestors.update_one(
            {"id": alerta['digestor_id']},
            {"$set": {"status": DigestorStatus.LIVRE}}
        )
    
    return {"message": "Alerta resolvido"}

# --- MANUTENCAO ---
@api_router.post("/manutencao", response_model=Manutencao)
async def create_manutencao(
    manutencao_create: ManutencaoCreate,
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.ADMIN and current_user.role != UserRole.OPERADOR:
        raise HTTPException(status_code=403, detail="Sem permissão")
    
    manutencao = Manutencao(
        **manutencao_create.model_dump(),
        responsavel_id=current_user.id,
        responsavel_name=current_user.nome
    )
    doc = manutencao.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.manutencoes.insert_one(doc)
    
    # Update digestor status
    await db.digestors.update_one(
        {"id": manutencao_create.digestor_id},
        {"$set": {"status": DigestorStatus.MANUTENCAO}}
    )
    
    return manutencao

@api_router.get("/manutencao", response_model=List[Manutencao])
async def list_manutencoes(current_user: User = Depends(get_current_user)):
    manutencoes = await db.manutencoes.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    for man in manutencoes:
        if isinstance(man.get('created_at'), str):
            man['created_at'] = datetime.fromisoformat(man['created_at'])
        if man.get('concluded_at') and isinstance(man['concluded_at'], str):
            man['concluded_at'] = datetime.fromisoformat(man['concluded_at'])
    
    return manutencoes

@api_router.post("/manutencao/{manutencao_id}/concluir")
async def concluir_manutencao(
    manutencao_id: str,
    current_user: User = Depends(get_current_user)
):
    manutencao = await db.manutencoes.find_one({"id": manutencao_id}, {"_id": 0})
    if not manutencao:
        raise HTTPException(status_code=404, detail="Manutenção não encontrada")
    
    await db.manutencoes.update_one(
        {"id": manutencao_id},
        {"$set": {
            "concluida": True,
            "concluded_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Check if digestor has other active maintenances
    other_maintenances = await db.manutencoes.count_documents({
        "digestor_id": manutencao['digestor_id'],
        "concluida": False,
        "id": {"$ne": manutencao_id}
    })
    
    if other_maintenances == 0:
        await db.digestors.update_one(
            {"id": manutencao['digestor_id']},
            {"$set": {"status": DigestorStatus.LIVRE}}
        )
    
    return {"message": "Manutenção concluída"}

# --- STATS & REPORTS ---
@api_router.get("/stats/dashboard")
async def get_dashboard_stats(current_user: User = Depends(get_current_user)):
    # Today's entries
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    total_entries_today = await db.entries.count_documents({
        "arrival_at": {"$gte": today_start.isoformat()}
    })
    
    total_toneladas_hoje = 0
    entries_today = await db.entries.find({
        "arrival_at": {"$gte": today_start.isoformat()}
    }, {"_id": 0}).to_list(1000)
    
    for entry in entries_today:
        total_toneladas_hoje += entry.get('toneladas_declaradas', 0)
    
    # Active cycles
    active_cycles = await db.digestors.count_documents({
        "status": {"$in": [DigestorStatus.TRITURANDO, DigestorStatus.COZINHANDO]}
    })
    
    # Active alerts
    active_alerts = await db.alertas.count_documents({"resolvido": False})
    
    # Digestor efficiency
    digestors = await db.digestors.find({}, {"_id": 0}).to_list(10)
    
    return {
        "total_entradas_hoje": total_entries_today,
        "total_toneladas_hoje": total_toneladas_hoje,
        "ciclos_ativos": active_cycles,
        "alertas_ativos": active_alerts,
        "digestores": digestors
    }

# Include the router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
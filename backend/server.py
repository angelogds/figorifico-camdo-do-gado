from fastapi import FastAPI, APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import Response
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Any, Dict, List, Optional, Literal
from datetime import datetime, timezone, timedelta
from enum import Enum
import bcrypt
import jwt
import os
import uuid

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')
client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
db = client[os.environ.get('DB_NAME', 'campo_do_gado_manutencao')]
JWT_SECRET = os.environ.get('JWT_SECRET', 'change-me-in-production')
JWT_ALGORITHM = 'HS256'

app = FastAPI(title='Manutenção Frigorífico Campo do Gado', version='2.0.0')
api_router = APIRouter(prefix='/api')
security = HTTPBearer()

class UserRole(str, Enum):
    ADMIN = 'admin'
    ENCARREGADO = 'encarregado'
    MECANICO = 'mecanico'

class UserBase(BaseModel):
    nome: str
    email: EmailStr
    role: UserRole

class UserCreate(UserBase):
    senha: str

class User(UserBase):
    model_config = ConfigDict(extra='ignore')
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserLogin(BaseModel):
    email: str
    senha: str

class TokenResponse(BaseModel):
    token: str
    user: User

class EquipamentoCreate(BaseModel):
    codigo: str
    nome: str
    setor: str
    tipo: str
    marca: Optional[str] = None
    modelo: Optional[str] = None
    numero_serie: Optional[str] = None
    localizacao: Optional[str] = None
    status: str = 'operando_normal'
    criticidade: str = 'media'
    foto_url: Optional[str] = None
    observacoes: Optional[str] = None

class VeiculoCreate(BaseModel):
    numero_frota: str
    placa: str
    tipo: str
    marca: Optional[str] = None
    modelo: Optional[str] = None
    ano: Optional[int] = None
    setor: str = 'Frota'
    status: str = 'operando'
    km_atual: float = 0
    tipo_bau: Optional[str] = None
    refrigerado: bool = False
    foto_url: Optional[str] = None
    observacoes: Optional[str] = None

class OrdemServicoCreate(BaseModel):
    origem: Literal['equipamento', 'veiculo']
    equipamento_id: Optional[str] = None
    veiculo_id: Optional[str] = None
    setor: str
    tipo_os: str
    categoria: str
    prioridade: str
    descricao: str
    mecanico_id: Optional[str] = None
    anexos: List[str] = []

class StatusUpdate(BaseModel):
    status: str
    observacao: Optional[str] = None

class AtribuicaoUpdate(BaseModel):
    mecanico_id: str

class AndamentoCreate(BaseModel):
    motivo_andamento: str
    observacao: Optional[str] = None

class FechamentoCreate(BaseModel):
    diagnostico: str
    servico_executado: str
    acao_corretiva: str
    acao_preventiva: Optional[str] = None
    material_utilizado: Optional[str] = None
    situacao_final: str
    anexos: List[str] = []

class PreventivaCreate(BaseModel):
    codigo: str
    origem: Literal['equipamento', 'veiculo']
    equipamento_id: Optional[str] = None
    veiculo_id: Optional[str] = None
    periodicidade: str
    descricao: str
    checklist: List[str] = []
    responsavel_id: Optional[str] = None
    data_programada: datetime
    observacoes: Optional[str] = None

class PreventivaExecucao(BaseModel):
    status: str = 'executada'
    nao_conformidades: Optional[str] = None
    acao_corretiva: Optional[str] = None
    acao_preventiva: Optional[str] = None
    observacoes: Optional[str] = None
    fotos: List[str] = []
    gerar_os: bool = False

class InspecaoCreate(BaseModel):
    origem: Literal['equipamento', 'veiculo']
    equipamento_id: Optional[str] = None
    veiculo_id: Optional[str] = None
    setor: str
    condicao_encontrada: str
    nao_conformidade: Optional[str] = None
    acao_corretiva: Optional[str] = None
    acao_preventiva: Optional[str] = None
    observacoes: Optional[str] = None
    fotos: List[str] = []
    gerar_os: bool = False

class SetorCreate(BaseModel):
    nome: str
    descricao: Optional[str] = None


def now():
    return datetime.now(timezone.utc)

def clean(document):
    if document:
        document.pop('_id', None)
    return document

def hash_password(password: str):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str):
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_token(user_id: str, role: str):
    return jwt.encode({'sub': user_id, 'role': role, 'exp': now() + timedelta(hours=24)}, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def sync_admin_user():
    """Create or update the Railway-configured administrator account."""
    email = os.environ.get('ADMIN_EMAIL', '').strip().lower()
    password = os.environ.get('ADMIN_PASSWORD', '')
    name = os.environ.get('ADMIN_NAME', 'Administrador').strip() or 'Administrador'

    if not email and not password:
        return
    if not email or not password:
        raise RuntimeError('Configure ADMIN_EMAIL e ADMIN_PASSWORD em conjunto')

    admin = User(nome=name, email=email, role=UserRole.ADMIN)
    await db.users.update_one(
        {'email': admin.email},
        {
            '$set': {
                'nome': admin.nome,
                'email': admin.email,
                'role': admin.role.value,
                'senha_hash': hash_password(password),
            },
            '$setOnInsert': {
                'id': admin.id,
                'created_at': admin.created_at,
            },
        },
        upsert=True,
    )
    print(f'Administrador configurado por variável de ambiente: {admin.email}')

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        document = await db.users.find_one({'id': payload['sub']}, {'_id': 0, 'senha_hash': 0})
        if not document:
            raise HTTPException(401, 'Usuário não encontrado')
        return User(**document)
    except jwt.PyJWTError:
        raise HTTPException(401, 'Token inválido ou expirado')

def require_roles(*roles):
    async def dependency(user: User = Depends(get_current_user)):
        if user.role.value not in roles:
            raise HTTPException(403, 'Perfil sem permissão para esta operação')
        return user
    return dependency

async def audit(user: User, acao: str, entidade: str, entidade_id: str, anterior=None, novo=None, observacao=None):
    event = {'id': str(uuid.uuid4()), 'entidade': entidade, 'entidade_id': entidade_id, 'acao': acao,
             'usuario_id': user.id, 'usuario_nome': user.nome, 'perfil': user.role.value, 'status_anterior': anterior,
             'status_novo': novo, 'observacao': observacao, 'created_at': now()}
    await db.historico_tecnico.insert_one(event)
    return event

async def create_os(payload: Dict[str, Any], user: User):
    if payload.get('origem') == 'equipamento' and not payload.get('equipamento_id'):
        raise HTTPException(422, 'Selecione o equipamento relacionado')
    if payload.get('origem') == 'veiculo' and not payload.get('veiculo_id'):
        raise HTTPException(422, 'Selecione o veículo relacionado')
    total = await db.ordens_servico.count_documents({}) + 1
    opened = now()
    document = {**payload, 'id': str(uuid.uuid4()), 'numero_os': f'OS-{opened.year}-{total:05d}', 'status': 'aberta',
                'solicitante_id': user.id, 'solicitante_nome': user.nome, 'perfil_abertura': user.role.value,
                'data_abertura': opened, 'created_at': opened, 'updated_at': opened}
    await db.ordens_servico.insert_one(document)
    await audit(user, 'abertura_os', 'ordem_servico', document['id'], novo='aberta', observacao=document['descricao'])
    return clean(document)

@api_router.post('/auth/register', response_model=User)
async def register(data: UserCreate, current: Optional[User] = Depends(get_current_user)):
    if current.role != UserRole.ADMIN:
        raise HTTPException(403, 'Somente administradores podem cadastrar usuários')
    if await db.users.find_one({'email': data.email.lower()}):
        raise HTTPException(400, 'E-mail já cadastrado')
    document = User(**{**data.model_dump(exclude={'senha'}), 'email': data.email.lower()}).model_dump()
    document['senha_hash'] = hash_password(data.senha)
    await db.users.insert_one(document)
    return clean(document)

@api_router.post('/auth/login', response_model=TokenResponse)
async def login(data: UserLogin):
    document = await db.users.find_one({'email': data.email.lower()})
    if not document or not verify_password(data.senha, document['senha_hash']):
        raise HTTPException(401, 'E-mail ou senha inválidos')
    return TokenResponse(token=create_token(document['id'], document['role']), user=User(**document))

@api_router.get('/auth/me', response_model=User)
async def me(user: User = Depends(get_current_user)):
    return user

async def list_collection(collection: str, query=None):
    return [clean(doc) async for doc in db[collection].find(query or {}, {'_id': 0}).sort('created_at', -1)]

async def update_asset(collection: str, entity: str, entity_id: str, values: Dict[str, Any], user: User):
    existing = await db[collection].find_one({'id': entity_id})
    if not existing: raise HTTPException(404, 'Registro não encontrado')
    values['updated_at'] = now()
    await db[collection].update_one({'id': entity_id}, {'$set': values})
    if 'status' in values and existing.get('status') != values['status']:
        await audit(user, 'alteracao_status', entity, entity_id, existing.get('status'), values['status'])
    return clean(await db[collection].find_one({'id': entity_id}, {'_id': 0}))

@api_router.post('/equipamentos')
async def add_equipamento(data: EquipamentoCreate, user: User = Depends(require_roles('admin', 'encarregado'))):
    document = {**data.model_dump(), 'id': str(uuid.uuid4()), 'cadastrado_por': user.nome, 'created_at': now(), 'updated_at': now()}
    await db.equipamentos.insert_one(document); await audit(user, 'cadastro', 'equipamento', document['id'], novo=document['status'])
    return clean(document)
@api_router.get('/equipamentos')
async def equipamentos(status: Optional[str] = None, setor: Optional[str] = None, user: User = Depends(get_current_user)):
    return await list_collection('equipamentos', {k:v for k,v in {'status':status, 'setor':setor}.items() if v})
@api_router.get('/equipamentos/{entity_id}')
async def equipamento(entity_id: str, user: User = Depends(get_current_user)):
    document=await db.equipamentos.find_one({'id':entity_id},{'_id':0});
    if not document: raise HTTPException(404,'Equipamento não encontrado')
    return document
@api_router.put('/equipamentos/{entity_id}')
async def edit_equipamento(entity_id: str, data: EquipamentoCreate, user: User=Depends(require_roles('admin','encarregado'))): return await update_asset('equipamentos','equipamento',entity_id,data.model_dump(),user)
@api_router.patch('/equipamentos/{entity_id}/status')
async def status_equipamento(entity_id: str, data: StatusUpdate, user: User=Depends(require_roles('admin','encarregado','mecanico'))): return await update_asset('equipamentos','equipamento',entity_id,{'status':data.status},user)
@api_router.get('/equipamentos/{entity_id}/historico')
async def history_equipamento(entity_id: str, user: User=Depends(get_current_user)): return await history('equipamento', entity_id)

@api_router.post('/veiculos')
async def add_veiculo(data: VeiculoCreate, user: User = Depends(require_roles('admin', 'encarregado'))):
    document={**data.model_dump(),'id':str(uuid.uuid4()),'cadastrado_por':user.nome,'created_at':now(),'updated_at':now()}; await db.veiculos.insert_one(document); await audit(user,'cadastro','veiculo',document['id'],novo=document['status']); return clean(document)
@api_router.get('/veiculos')
async def veiculos(status:Optional[str]=None,user:User=Depends(get_current_user)): return await list_collection('veiculos', {'status':status} if status else {})
@api_router.get('/veiculos/{entity_id}')
async def veiculo(entity_id:str,user:User=Depends(get_current_user)):
    document=await db.veiculos.find_one({'id':entity_id},{'_id':0});
    if not document: raise HTTPException(404,'Veículo não encontrado')
    return document
@api_router.put('/veiculos/{entity_id}')
async def edit_veiculo(entity_id:str,data:VeiculoCreate,user:User=Depends(require_roles('admin','encarregado'))): return await update_asset('veiculos','veiculo',entity_id,data.model_dump(),user)
@api_router.patch('/veiculos/{entity_id}/status')
async def status_veiculo(entity_id:str,data:StatusUpdate,user:User=Depends(require_roles('admin','encarregado','mecanico'))): return await update_asset('veiculos','veiculo',entity_id,{'status':data.status},user)
@api_router.get('/veiculos/{entity_id}/historico')
async def history_veiculo(entity_id:str,user:User=Depends(get_current_user)): return await history('veiculo', entity_id)

async def history(entity:str, entity_id:str):
    field = f'{entity}_id'
    return {'ordens_servico': await list_collection('ordens_servico',{field:entity_id}), 'preventivas': await list_collection('preventivas',{field:entity_id}), 'inspecoes': await list_collection('inspecoes',{field:entity_id}), 'rastreabilidade': await list_collection('historico_tecnico',{'entidade_id':entity_id})}

@api_router.post('/ordens-servico')
async def add_ordem(data:OrdemServicoCreate,user:User=Depends(get_current_user)): return await create_os(data.model_dump(),user)
@api_router.get('/ordens-servico')
async def ordens(status:Optional[str]=None,prioridade:Optional[str]=None,setor:Optional[str]=None,user:User=Depends(get_current_user)): return await list_collection('ordens_servico',{k:v for k,v in {'status':status,'prioridade':prioridade,'setor':setor}.items() if v})
@api_router.get('/ordens-servico/{entity_id}')
async def ordem(entity_id:str,user:User=Depends(get_current_user)):
    document=await db.ordens_servico.find_one({'id':entity_id},{'_id':0});
    if not document: raise HTTPException(404,'OS não encontrada')
    document['rastreabilidade']=await list_collection('historico_tecnico',{'entidade_id':entity_id}); return document
@api_router.patch('/ordens-servico/{entity_id}/status')
async def status_ordem(entity_id:str,data:StatusUpdate,user:User=Depends(get_current_user)):
    existing=await db.ordens_servico.find_one({'id':entity_id});
    if not existing: raise HTTPException(404,'OS não encontrada')
    values={'status':data.status,'updated_at':now()}
    if data.status=='em_andamento' and not existing.get('data_inicio'): values['data_inicio']=now()
    await db.ordens_servico.update_one({'id':entity_id},{'$set':values}); await audit(user,'alteracao_status','ordem_servico',entity_id,existing.get('status'),data.status,data.observacao); return clean(await db.ordens_servico.find_one({'id':entity_id},{'_id':0}))
@api_router.patch('/ordens-servico/{entity_id}/atribuir')
async def atribuir(entity_id:str,data:AtribuicaoUpdate,user:User=Depends(require_roles('admin','encarregado'))):
    mecanico=await db.users.find_one({'id':data.mecanico_id,'role':'mecanico'});
    if not mecanico: raise HTTPException(404,'Mecânico não encontrado')
    await db.ordens_servico.update_one({'id':entity_id},{'$set':{'mecanico_id':mecanico['id'],'mecanico_nome':mecanico['nome'],'updated_at':now()}}); await audit(user,'atribuicao_mecanico','ordem_servico',entity_id,novo=mecanico['nome']); return {'message':'Mecânico atribuído com sucesso'}
@api_router.post('/ordens-servico/{entity_id}/andamento')
async def andamento(entity_id:str,data:AndamentoCreate,user:User=Depends(get_current_user)):
    text=f"OS permanece em andamento devido a {data.motivo_andamento.lower()}. A situação foi informada ao encarregado de manutenção para acompanhamento."
    registro={'motivo':data.motivo_andamento,'texto_automatico':text,'observacao':data.observacao,'registrado_por':user.nome,'created_at':now()}
    await db.ordens_servico.update_one({'id':entity_id},{'$set':{'motivo_andamento':data.motivo_andamento,'updated_at':now()},'$push':{'acompanhamentos':registro}}); await audit(user,'registro_andamento','ordem_servico',entity_id,observacao=text); return registro
@api_router.post('/ordens-servico/{entity_id}/fechar')
async def fechar(entity_id:str,data:FechamentoCreate,user:User=Depends(get_current_user)):
    existing=await db.ordens_servico.find_one({'id':entity_id});
    if not existing: raise HTTPException(404,'OS não encontrada')
    finished=now(); values={**data.model_dump(),'status':'finalizada','data_fechamento':finished,'fechado_por':user.nome,'updated_at':finished,'tempo_aberta_horas':round((finished-existing['data_abertura']).total_seconds()/3600,2)}
    await db.ordens_servico.update_one({'id':entity_id},{'$set':values}); await audit(user,'fechamento_os','ordem_servico',entity_id,existing.get('status'),'finalizada',data.situacao_final); return clean(await db.ordens_servico.find_one({'id':entity_id},{'_id':0}))

@api_router.post('/preventivas')
async def add_preventiva(data:PreventivaCreate,user:User=Depends(require_roles('admin','encarregado'))):
    document={**data.model_dump(),'id':str(uuid.uuid4()),'status':'programada','created_at':now(),'updated_at':now()}; await db.preventivas.insert_one(document); await audit(user,'programacao_preventiva','preventiva',document['id'],novo='programada'); return clean(document)
@api_router.get('/preventivas')
async def preventivas(user:User=Depends(get_current_user)): return await list_collection('preventivas')
@api_router.get('/preventivas/atrasadas')
async def preventivas_atrasadas(user:User=Depends(get_current_user)): return await list_collection('preventivas',{'data_programada':{'$lt':now()},'status':{'$in':['programada','em_execucao']}})
@api_router.post('/preventivas/{entity_id}/executar')
async def executar_preventiva(entity_id:str,data:PreventivaExecucao,user:User=Depends(get_current_user)):
    prev=await db.preventivas.find_one({'id':entity_id});
    if not prev: raise HTTPException(404,'Preventiva não encontrada')
    values={**data.model_dump(exclude={'gerar_os'}),'data_executada':now(),'executado_por':user.nome,'updated_at':now()}; await db.preventivas.update_one({'id':entity_id},{'$set':values}); await audit(user,'execucao_preventiva','preventiva',entity_id,prev['status'],data.status)
    if data.gerar_os: values['os_gerada']=await create_os({'origem':prev['origem'],'equipamento_id':prev.get('equipamento_id'),'veiculo_id':prev.get('veiculo_id'),'setor':'Manutenção','tipo_os':'corretiva','categoria':'outros','prioridade':'alta','descricao':data.nao_conformidades or 'Não conformidade identificada em preventiva','anexos':data.fotos},user)
    return values

@api_router.post('/inspecoes')
async def add_inspecao(data:InspecaoCreate,user:User=Depends(get_current_user)):
    document={**data.model_dump(exclude={'gerar_os'}),'id':str(uuid.uuid4()),'responsavel_id':user.id,'responsavel_nome':user.nome,'created_at':now()}; await db.inspecoes.insert_one(document); await audit(user,'registro_inspecao','inspecao',document['id'],observacao=data.condicao_encontrada)
    if data.gerar_os: document['os_gerada']=await create_os({'origem':data.origem,'equipamento_id':data.equipamento_id,'veiculo_id':data.veiculo_id,'setor':data.setor,'tipo_os':'corretiva','categoria':'outros','prioridade':'alta','descricao':data.nao_conformidade or data.condicao_encontrada,'anexos':data.fotos},user)
    return clean(document)
@api_router.get('/inspecoes')
async def inspecoes(user:User=Depends(get_current_user)): return await list_collection('inspecoes')

@api_router.post('/setores')
async def add_setor(data:SetorCreate,user:User=Depends(require_roles('admin'))):
    document={**data.model_dump(),'id':str(uuid.uuid4()),'created_at':now()}; await db.setores.insert_one(document); return clean(document)
@api_router.get('/setores')
async def setores(user:User=Depends(get_current_user)): return await list_collection('setores')

@api_router.get('/dashboard')
async def dashboard(user:User=Depends(get_current_user)):
    today=now().replace(hour=0,minute=0,second=0,microsecond=0)
    count=lambda collection,query: db[collection].count_documents(query)
    return {'os_abertas':await count('ordens_servico',{'status':'aberta'}),'os_em_andamento':await count('ordens_servico',{'status':'em_andamento'}),'os_finalizadas_hoje':await count('ordens_servico',{'status':'finalizada','data_fechamento':{'$gte':today}}),'os_atrasadas':await count('ordens_servico',{'status':{'$nin':['finalizada','cancelada']},'data_abertura':{'$lt':now()-timedelta(days=1)}}),'preventivas_dia':await count('preventivas',{'data_programada':{'$gte':today,'$lt':today+timedelta(days=1)}}),'preventivas_atrasadas':await count('preventivas',{'data_programada':{'$lt':today},'status':{'$in':['programada','em_execucao']}}),'equipamentos_parados':await count('equipamentos',{'status':'parado'}),'veiculos_parados':await count('veiculos',{'status':'parado'}),'equipamentos_observacao':await count('equipamentos',{'status':'em_observacao'}),'frota_manutencao':await count('veiculos',{'status':'em_manutencao'}),'demandas_urgentes':await count('ordens_servico',{'prioridade':{'$in':['urgente','critica']},'status':{'$nin':['finalizada','cancelada']}})}

@api_router.get('/relatorios/ordens-servico')
async def relatorio_os(status:Optional[str]=None,setor:Optional[str]=None,prioridade:Optional[str]=None,user:User=Depends(get_current_user)): return await list_collection('ordens_servico',{k:v for k,v in {'status':status,'setor':setor,'prioridade':prioridade}.items() if v})

def pdf_bytes(lines: List[str]):
    safe=[line.replace('(','[').replace(')',']')[:105] for line in lines]; content='BT /F1 11 Tf 50 790 Td 0 -18 Td '.join(['']+[f'({line}) Tj' for line in safe])+' ET'; objects=['<< /Type /Catalog /Pages 2 0 R >>','<< /Type /Pages /Kids [3 0 R] /Count 1 >>','<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>',f'<< /Length {len(content)} >>\nstream\n{content}\nendstream','<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>']; pdf='%PDF-1.4\n'; offsets=[]
    for idx,obj in enumerate(objects,1): offsets.append(len(pdf)); pdf+=f'{idx} 0 obj\n{obj}\nendobj\n'
    xref=len(pdf); pdf+='xref\n0 6\n0000000000 65535 f \n'+''.join(f'{o:010d} 00000 n \n' for o in offsets)+f'trailer << /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF'; return pdf.encode('latin-1','replace')
@api_router.get('/ordens-servico/{entity_id}/pdf')
async def ordem_pdf(entity_id:str,user:User=Depends(get_current_user)):
    os_doc=await db.ordens_servico.find_one({'id':entity_id},{'_id':0});
    if not os_doc: raise HTTPException(404,'OS não encontrada')
    lines=['CAMPO DO GADO - MANUTENCAO FRIGORIFICO','Controle de Manutencao Industrial e Frota',f"ORDEM DE SERVICO {os_doc['numero_os']}",f"Setor: {os_doc.get('setor','-')}",f"Status: {os_doc.get('status','-')}",f"Demanda: {os_doc.get('descricao','-')}",f"Diagnostico: {os_doc.get('diagnostico','-')}",f"Servico executado: {os_doc.get('servico_executado','-')}",f"Acao corretiva: {os_doc.get('acao_corretiva','-')}",f"Acao preventiva: {os_doc.get('acao_preventiva','-')}",f"Situacao final: {os_doc.get('situacao_final','-')}",f"Gerado em: {now().strftime('%d/%m/%Y %H:%M')} - Pagina 1/1"]
    return Response(pdf_bytes(lines),media_type='application/pdf',headers={'Content-Disposition':f"inline; filename={os_doc['numero_os']}.pdf"})

app.include_router(api_router)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=os.environ.get('CORS_ORIGINS','*').split(','), allow_methods=['*'], allow_headers=['*'])
@app.on_event('startup')
async def startup(): await sync_admin_user()
@app.on_event('shutdown')
async def shutdown(): client.close()

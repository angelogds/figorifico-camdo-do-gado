# Deploy no Railway (Railway-ready)

Este repositório é um monorepo com 2 apps:
- **backend/**: FastAPI (MongoDB)
- **frontend/**: React (build estático)

## Como subir no Railway (recomendado)

Crie **2 services** no mesmo projeto Railway (um para backend e outro para frontend).

### 1) Backend service
- Root Directory: `backend`
- Deploy (Dockerfile já incluso em `backend/Dockerfile`)
- Variables (Settings → Variables):
  - `MONGO_URL` = conexão do Mongo (Railway Mongo ou Atlas)
  - `DB_NAME` = nome do banco
  - `JWT_SECRET` = segredo forte (obrigatório em produção)
  - `CORS_ORIGINS` = URL do frontend (ex: https://seu-frontend.up.railway.app)

### 2) Frontend service

Este repositório está configurado para fazer o deploy do frontend **pela raiz do repositório**:

- deixe `Root Directory` vazio no Railway;
- mantenha o builder Dockerfile configurado pelo arquivo `railway.json` da raiz;
- o `Start Command` seguro versionado em `railway.json` sobrescreve eventuais comandos antigos configurados no painel;
- o `Dockerfile` da raiz compila `frontend/` e inicia o servidor de arquivos estáticos diretamente, sem executar `npm start` no runtime.

Variables:
- `REACT_APP_BACKEND_URL` = URL pública do backend (ex: https://seu-backend.up.railway.app)

> Não misture esta configuração com `Root Directory = frontend`. O comando versionado em `railway.json` inicia o servidor estático diretamente, sem executar npm no runtime, e evita o loop de reinicialização causado por `Could not read package.json: /app/package.json`.

## Seed (criar usuários iniciais)
No Railway, rode um **One-off Command** no backend (ou localmente com env vars setadas):

```bash
python ../scripts/create_users.py
```

> Alternativa: a partir da raiz do repositório, rode `python scripts/create_users.py`.

## Observações
- O frontend usa `REACT_APP_BACKEND_URL` e monta a API em `{BACKEND_URL}/api`.
- O backend exige `MONGO_URL` e `DB_NAME` para inicializar a conexão com o Mongo.

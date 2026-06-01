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

Há duas opções suportadas:

- **Deploy pela raiz do repositório (mais simples):** deixe `Root Directory` vazio. O `package.json` da raiz encaminha instalação, build e start para `frontend/`.
- **Deploy pelo Dockerfile do frontend:** configure `Root Directory` como `frontend`. O Railway usará o Dockerfile já incluso em `frontend/Dockerfile`.

Variables:
- `REACT_APP_BACKEND_URL` = URL pública do backend (ex: https://seu-backend.up.railway.app)

> Se o frontend for iniciado pela raiz sem o `package.json` da raiz, o Railway executará o npm em `/app` e falhará com `Could not read package.json`. Não configure um Start Command manual diferente de `npm start` para a opção de deploy pela raiz.

## Seed (criar usuários iniciais)
No Railway, rode um **One-off Command** no backend (ou localmente com env vars setadas):

```bash
python ../create_users.py
```

> Alternativa: rode o script a partir da raiz do repo. Ele tenta achar `backend/.env` também.

## Observações
- O frontend usa `REACT_APP_BACKEND_URL` e monta a API em `{BACKEND_URL}/api`.
- O backend exige `MONGO_URL` e `DB_NAME` para inicializar a conexão com o Mongo.

# Hotspot Wi-Fi — Clube Albert Scharlé

Sistema de acesso Wi-Fi com coleta de cadastro integrado ao MikroTik RouterOS.

## Como funciona

1. O cliente conecta no Wi-Fi
2. O MikroTik redireciona para a página de login personalizada
3. O cliente preenche: **Nome, CPF, E-mail e Telefone**
4. O backend valida os dados, salva no banco e cria o usuário no MikroTik via API
5. O acesso à internet é liberado automaticamente

---

## Estrutura do projeto

```
hotspot_charle/
├── hotspot/          → Arquivos da página de login (vão para o MikroTik)
│   ├── login.html
│   ├── css/style.css
│   ├── img/
│   └── ...
└── backend/          → API Python (roda em servidor/VM na rede local)
    ├── main.py       → Endpoints da API
    ├── database.py   → Banco de dados SQLite
    ├── mikrotik.py   → Integração com RouterOS API
    ├── requirements.txt
    └── .env.example
```

---

## Requisitos

- MikroTik RouterOS 7.x com Hotspot configurado
- Servidor Linux (Debian/Ubuntu) ou Windows com Python 3.11+
- API do RouterOS habilitada (`/ip service enable api`)

---

## Instalação do Backend

### 1. Clonar o repositório

```bash
git clone https://github.com/seu-usuario/hotspot-charle.git
cd hotspot-charle/backend
```

### 2. Configurar o ambiente

```bash
python3 -m venv venv
source venv/bin/activate          # Linux/Mac
# venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

### 3. Configurar as variáveis de ambiente

```bash
cp .env.example .env
nano .env
```

Preencha o arquivo `.env`:

```env
MIKROTIK_HOST=192.168.1.1       # IP do MikroTik na rede local
MIKROTIK_PORT=8728
MIKROTIK_USER=admin
MIKROTIK_PASSWORD=sua_senha
HOTSPOT_PROFILE=default          # User Profile em IP > Hotspot > User Profiles
SESSION_TIMEOUT=0                # 0 = sem limite
ALLOWED_ORIGINS=*
```

### 4. Iniciar o backend

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Verifique se está rodando:
```
http://IP_DO_SERVIDOR:8000/health
```

---

## Configurar como serviço (Linux)

Para o backend iniciar automaticamente com o servidor:

```bash
cat > /etc/systemd/system/hotspot-api.service << 'EOF'
[Unit]
Description=Hotspot Charle — API Backend
After=network.target

[Service]
WorkingDirectory=/opt/hotspot_charle/backend
ExecStart=/opt/hotspot_charle/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable hotspot-api
systemctl start hotspot-api
systemctl status hotspot-api
```

---

## Configurar o MikroTik

### 1. Habilitar a API do RouterOS

```routeros
/ip service enable api
```

### 2. Subir os arquivos do hotspot via FTP

No terminal do Mac/Linux, dentro da pasta `hotspot/`:

```bash
# Arquivos raiz
for f in alogin.html api.json error.html errors.txt favicon.ico login.html logout.html md5.js radvert.html redirect.html rlogin.html status.html termos.html; do
  curl -s -T "$f" "ftp://IP_DO_MIKROTIK/hotspot/$f" --user "admin:SENHA"
done

# CSS e imagens
curl -s -T css/style.css "ftp://IP_DO_MIKROTIK/hotspot/css/style.css" --user "admin:SENHA"
curl -s -T img/logo.png "ftp://IP_DO_MIKROTIK/hotspot/img/logo.png" --user "admin:SENHA"
curl -s -T img/password.svg "ftp://IP_DO_MIKROTIK/hotspot/img/password.svg" --user "admin:SENHA"
curl -s -T img/user.svg "ftp://IP_DO_MIKROTIK/hotspot/img/user.svg" --user "admin:SENHA"
```

### 3. Configurar o Walled Garden

Libera o acesso ao backend antes da autenticação:

```routeros
/ip hotspot walled-garden ip add dst-address=IP_DO_SERVIDOR action=accept comment="Backend API"
```

### 4. Atualizar a URL da API no login.html

No arquivo `hotspot/login.html`, linha com `API_URL`:

```js
var API_URL = 'http://IP_DO_SERVIDOR:8000/api/register';
```

---

## Atualização do sistema

### Backend

```bash
cd /opt/hotspot_charle
git pull
systemctl restart hotspot-api
```

### Página de login (após alterações no login.html)

```bash
curl -s -T hotspot/login.html "ftp://IP_DO_MIKROTIK/hotspot/login.html" --user "admin:SENHA"
```

---

## API — Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/api/register` | Cadastra cliente e cria usuário no MikroTik |
| `GET` | `/api/leads` | Lista todos os cadastros |
| `GET` | `/health` | Verifica se o backend está rodando |

### Exemplo de cadastro

```bash
curl -X POST http://IP_DO_SERVIDOR:8000/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "João Silva",
    "cpf": "123.456.789-09",
    "email": "joao@email.com",
    "telefone": "(11) 99999-9999"
  }'
```

---

## Banco de dados

Os leads ficam salvos em `backend/leads.db` (SQLite). Para consultar:

```bash
sqlite3 /opt/hotspot_charle/backend/leads.db "SELECT * FROM leads ORDER BY criado_em DESC;"
```

Ou via API:
```
GET http://IP_DO_SERVIDOR:8000/api/leads
```

---

## Suporte

Desenvolvido por **Atica IT**

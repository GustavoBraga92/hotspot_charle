# Hotspot Wi-Fi — Clube Albert Scharlé

Sistema de acesso Wi-Fi com coleta de cadastro integrado ao MikroTik RouterOS.

## Como funciona

1. O cliente conecta no Wi-Fi
2. O MikroTik detecta o captive portal e abre a página de login automaticamente
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
- Servidor Linux (Debian/Ubuntu) com Python 3.11+
- API do RouterOS habilitada (`/ip service enable api`)

---

## Instalação do Backend

### 1. Clonar o repositório

```bash
git clone https://github.com/GustavoBraga92/hotspot_charle.git
cd hotspot_charle/backend
```

### 2. Configurar o ambiente

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configurar as variáveis de ambiente

```bash
cp .env.example .env
nano .env
```

Preencha o arquivo `.env`:

```env
MIKROTIK_HOST=192.168.1.1        # IP do MikroTik na rede local
MIKROTIK_PORT=8728
MIKROTIK_USER=admin
MIKROTIK_PASSWORD=sua_senha
HOTSPOT_PROFILE=default           # User Profile em IP > Hotspot > User Profiles
SESSION_TIMEOUT=0                 # 0 = sem limite de tempo
ALLOWED_ORIGINS=*
API_KEY=gere-uma-chave-forte      # Protege o endpoint /api/leads
```

Para gerar uma chave segura:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
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

Restrinja o acesso à API apenas ao IP da VM:
```routeros
/ip service set api address=IP_DO_SERVIDOR/32
```

### 2. Configurar o Hotspot Server Profile

Para o captive portal abrir automaticamente nos celulares:
```routeros
/ip hotspot profile set NOME_DO_PROFILE dns-name=login.hotspot
```

### 3. Subir os arquivos do hotspot via FTP

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

### 4. Configurar o Walled Garden

Libera o acesso ao backend antes da autenticação:

```routeros
/ip hotspot walled-garden ip add dst-address=IP_DO_SERVIDOR action=accept comment="Backend API"
```

Para liberar AnyDesk (acesso remoto):
```routeros
/ip hotspot walled-garden add server=NOME_DO_HOTSPOT dst-host=*.anydesk.com action=allow comment="AnyDesk"
```

### 5. Atualizar a URL da API no login.html

No arquivo `hotspot/login.html`, linha com `API_URL`:

```js
var API_URL = 'http://IP_DO_SERVIDOR:8000/api/register';
```

---

## Segurança

### Firewall na VM (nftables)

Restringe a porta 8000 apenas para IPs autorizados (MikroTik e máquinas admin):

```bash
nano /etc/nftables.conf
```

```
#!/usr/sbin/nft -f

flush ruleset

table inet filter {
    chain input {
        type filter hook input priority 0; policy accept;

        ip saddr IP_DO_MIKROTIK tcp dport 8000 accept
        ip saddr IP_DO_SERVIDOR tcp dport 8000 accept
        # ip saddr IP_MAQUINA_ADMIN tcp dport 8000 accept
        tcp dport 8000 drop
    }
}
```

```bash
systemctl enable nftables
systemctl start nftables
```

### API Key

O endpoint `/api/leads` exige autenticação via header:

```bash
curl -H "X-API-Key: sua_chave" http://IP_DO_SERVIDOR:8000/api/leads
```

Sem a chave correta retorna `403 Forbidden`.

---

## Atualização do sistema

### Backend

```bash
cd /opt/hotspot_charle
git pull
systemctl restart hotspot-api
```

> **Atenção:** se houver alterações locais no servidor (ex: `login.html` com IP editado direto), use `git checkout -- arquivo` antes do pull.

### Página de login (após alterações no login.html)

```bash
curl -s -T hotspot/login.html "ftp://IP_DO_MIKROTIK/hotspot/login.html" --user "admin:SENHA"
```

---

## API — Endpoints

| Método | Endpoint | Auth | Descrição |
|--------|----------|------|-----------|
| `POST` | `/api/register` | Não | Cadastra cliente e cria usuário no MikroTik |
| `GET` | `/api/leads` | API Key | Lista todos os cadastros |
| `GET` | `/health` | Não | Verifica se o backend está rodando |

### Consultar leads

```bash
curl -H "X-API-Key: sua_chave" http://IP_DO_SERVIDOR:8000/api/leads
```

### Consultar via SSH (sem liberar IP no firewall)

```bash
ssh root@IP_DO_SERVIDOR "curl -s -H 'X-API-Key: sua_chave' http://localhost:8000/api/leads"
```

---

## Banco de dados

Os leads ficam salvos em `backend/leads.db` (SQLite). Para consultar direto na VM:

```bash
sqlite3 /opt/hotspot_charle/backend/leads.db "SELECT * FROM leads ORDER BY criado_em DESC;"
```

---

## Manutenção

### Limpar usuários do MikroTik (para testes)

```routeros
# Remove todos exceto admin e default-trial
/ip hotspot user remove [find where name!="admin" && name!="default-trial"]

# Derruba sessões ativas
/ip hotspot active remove [find]

# Limpa cookies
/ip hotspot cookie remove [find]
```

### Verificar logs do backend

```bash
journalctl -u hotspot-api -f
```

---

## Suporte

Desenvolvido por **Atica IT**

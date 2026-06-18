import os
import secrets
import string
import routeros_api

MIKROTIK_HOST = os.getenv("MIKROTIK_HOST", "192.168.88.1")
MIKROTIK_PORT = int(os.getenv("MIKROTIK_PORT", "8728"))
MIKROTIK_USER = os.getenv("MIKROTIK_USER", "admin")
MIKROTIK_PASSWORD = os.getenv("MIKROTIK_PASSWORD", "")
HOTSPOT_PROFILE = os.getenv("HOTSPOT_PROFILE", "default")
SESSION_TIMEOUT = os.getenv("SESSION_TIMEOUT", "0")


def _connect():
    pool = routeros_api.RouterOsApiPool(
        MIKROTIK_HOST,
        username=MIKROTIK_USER,
        password=MIKROTIK_PASSWORD,
        port=MIKROTIK_PORT,
        plaintext_login=True,
    )
    return pool.get_api()


def _gerar_senha(tamanho: int = 10) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(tamanho))


def criar_usuario_hotspot(cpf: str, nome: str, mac: str | None = None) -> dict:
    """
    Cria ou atualiza usuário no hotspot do MikroTik.
    Username = CPF (apenas dígitos). Retorna {'username': ..., 'password': ...}.
    """
    username = "".join(filter(str.isdigit, cpf))
    password = _gerar_senha()

    api = _connect()
    hotspot_users = api.get_resource("/ip/hotspot/user")

    # Se o CPF já existe, atualiza a senha (re-cadastro)
    all_users = hotspot_users.get()
    existing = [u for u in all_users if u.get("name") == username]
    if existing:
        hotspot_users.set(id=existing[0]["id"], password=password)
    else:
        params = {
            "name": username,
            "password": password,
            "profile": HOTSPOT_PROFILE,
            "comment": nome,
        }
        if mac:
            params["mac-address"] = mac
        if SESSION_TIMEOUT and SESSION_TIMEOUT != "0":
            params["limit-uptime"] = SESSION_TIMEOUT
        hotspot_users.add(**params)

    return {"username": username, "password": password}

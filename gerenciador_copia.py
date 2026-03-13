from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from openpyxl import Workbook

os.system("chcp 65001 > nul")
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

DATA_FILE = "dados.json"
BACKUP_DIR = "backups"
REPORT_DIR = "relatorios"
DATE_FMT = "%d/%m/%Y"
SUPERADMIN_USER = "Bernardo"
SUPERADMIN_MASTER_PASSWORD_SHA256 = "0c61d3c0d8b94357ce1a46eb242fa27356128a1949ce2f67af5fc6d4cdcb8b34"
SUPERADMIN_SECURITY_QUESTION = "Qual e a coisa que esse usuario mais faz?"
SUPERADMIN_SECURITY_ANSWER_SHA256 = "60965168ce762e949600281ba6d01fee136e5b6e8257b1f216f9025ed324474c"
SUPERADMIN_BOOTSTRAP_PIN_HASH = "2781900dd874897daa41266adbf6594c$2d06b0fac5da1cadc180c0cdde83f18b6d7911b8f136bc311ac63076c2643b79"
ADMIN_BOOTSTRAP_PIN_HASH = "e4727247ef61e26583175e500ca847a3$84e87c0d8745e1d840c21437ebad53d04f7f652ab797326eeaee8effe376ae68"
ADMIN_USER = "admin"
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCK_SECONDS = 30

DEFAULT_CATEGORIES = [
    "Higiene pessoal",
    "Alimentacao",
    "Limpeza da casa",
    "Contas basicas",
    "Conectividade",
    "Cartao de credito",
    "Van",
    "Reposicoes obrigatorias",
    "Taxas municipais",
    "Custos de moradia",
    "Outros",
]


def hash_pin(pin: str, salt_hex: str | None = None) -> str:
    if salt_hex is None:
        salt_hex = os.urandom(16).hex()
    digest = hashlib.sha256((salt_hex + pin).encode("utf-8")).hexdigest()
    return f"{salt_hex}${digest}"


def verify_pin(pin: str, stored_hash: str) -> bool:
    try:
        salt_hex, digest = stored_hash.split("$", 1)
    except ValueError:
        return False
    candidate = hashlib.sha256((salt_hex + pin).encode("utf-8")).hexdigest()
    return candidate == digest


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def verify_sha256_secret(plain_value: str, expected_sha256: str) -> bool:
    return hmac.compare_digest(sha256_text(plain_value), expected_sha256)


def validate_password_strength(password: str) -> bool:
    if len(password) < 8:
        return False
    has_upper = any(ch.isupper() for ch in password)
    has_lower = any(ch.islower() for ch in password)
    has_digit = any(ch.isdigit() for ch in password)
    return has_upper and has_lower and has_digit


def parse_date(text: str) -> datetime | None:
    try:
        return datetime.strptime(text, DATE_FMT)
    except Exception:
        return None


def ensure_dirs() -> None:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)


def load_json_file() -> dict:
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        print("Aviso: dados.json invalido/corrompido. Iniciando vazio.")
        return {}


def save_system_data(make_backup: bool = True) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(system_data, f, ensure_ascii=False, indent=2)

    if not make_backup:
        return

    ensure_dirs()
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy(DATA_FILE, os.path.join(BACKUP_DIR, f"dados_backup_{timestamp}.json"))
    except Exception:
        pass


def default_user_data() -> dict:
    return {
        "email": "",
        "nomes": [],
        "cats": [],
        "valores": [],
        "parcelas": [],
        "datas": [],
        "vencimentos": [],
        "orcamento_mensal": 0.0,
        "categorias": DEFAULT_CATEGORIES.copy(),
    }


def normalize_categories(raw_categories: list[str] | None) -> list[str]:
    categories = []
    if isinstance(raw_categories, list):
        for cat in raw_categories:
            if isinstance(cat, str):
                clean = cat.strip()
                if clean and clean not in categories:
                    categories.append(clean)
    for fixed in DEFAULT_CATEGORIES:
        if fixed not in categories:
            categories.append(fixed)
    return categories


def coerce_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def coerce_int(value, default=1):
    try:
        return int(value)
    except Exception:
        return default


def migrate_legacy_if_needed(raw: dict) -> dict:
    if "users" in raw and isinstance(raw.get("users"), dict):
        return raw

    if not raw:
        return {"users": {}}

    # Migra estrutura antiga para uma conta padrao.
    legacy_user = "admin"
    legacy_pin_hash = str(raw.get("pin_hash", "")).strip()
    if not legacy_pin_hash:
        legacy_pin = str(raw.get("pin", "1234"))
        legacy_pin_hash = hash_pin(legacy_pin)

    migrated = {
        "users": {
            legacy_user: {
                "pin_hash": legacy_pin_hash,
                "role": "admin",
                "data": {
                    "nomes": raw.get("nomes", []),
                    "cats": raw.get("cats", []),
                    "valores": raw.get("valores", []),
                    "parcelas": raw.get("parcelas", []),
                    "datas": raw.get("datas", []),
                    "vencimentos": raw.get("vencimentos", []),
                    "orcamento_mensal": raw.get("orcamento_mensal", 0.0),
                    "categorias": raw.get("categorias", DEFAULT_CATEGORIES.copy()),
                },
            }
        }
    }
    return migrated


def validate_username(username: str) -> bool:
    return re.fullmatch(r"[a-zA-Z0-9_]{3,20}", username) is not None


def create_user(username: str, senha: str) -> bool:
    if username in system_data["users"]:
        return False
    system_data["users"][username] = {
        "pin_hash": hash_pin(senha),
        "role": "user",
        "data": default_user_data(),
    }
    save_system_data(make_backup=False)
    return True


def login_user(username: str, senha: str) -> bool:
    rec = system_data["users"].get(username)
    if not isinstance(rec, dict):
        key = find_user_key_case_insensitive(username)
        if key is not None:
            rec = system_data["users"].get(key)
    if not isinstance(rec, dict):
        return False
    stored = str(rec.get("pin_hash", ""))
    return verify_pin(senha, stored)


def get_user_role(username: str) -> str:
    key = find_user_key_case_insensitive(username)
    if key is None:
        return "user"
    rec = system_data["users"].get(key, {})
    role = str(rec.get("role", "user")).strip().lower()
    if role not in {"user", "admin", "superadmin"}:
        return "user"
    return role


def is_admin_or_higher(username: str) -> bool:
    return get_user_role(username) in {"admin", "superadmin"}


def is_superadmin(username: str) -> bool:
    return get_user_role(username) == "superadmin"


def load_user_data(username: str) -> None:
    global nomes, cats, valores, parcelas, datas, vencimentos, orcamento_mensal, categorias
    rec = system_data["users"].get(username, {})
    user_data = rec.get("data", {}) if isinstance(rec, dict) else {}

    nomes = [str(x).strip() for x in user_data.get("nomes", []) if str(x).strip()]
    cats = [str(x).strip() for x in user_data.get("cats", [])]
    valores = [coerce_float(x) for x in user_data.get("valores", [])]
    parcelas = [max(1, coerce_int(x, 1)) for x in user_data.get("parcelas", [])]
    datas = [str(x).strip() for x in user_data.get("datas", [])]
    vencimentos = [str(x).strip() if str(x).strip() else "-" for x in user_data.get("vencimentos", [])]
    orcamento_mensal = coerce_float(user_data.get("orcamento_mensal", 0.0), 0.0)
    categorias = normalize_categories(user_data.get("categorias"))
    sync_lists()


def persist_current_user(make_backup: bool = True) -> None:
    sync_lists()
    if current_user not in system_data["users"]:
        return
    system_data["users"][current_user]["data"] = {
        "nomes": nomes,
        "cats": cats,
        "valores": valores,
        "parcelas": parcelas,
        "datas": datas,
        "vencimentos": vencimentos,
        "orcamento_mensal": orcamento_mensal,
        "categorias": categorias,
    }
    save_system_data(make_backup=make_backup)


def startup_auth() -> str:
    failed_login_attempts = 0
    lockout_until = 0.0

    while True:
        print("\nJa tem conta? (sim/nao)")
        resp = input("Resposta: ").strip().lower()

        if resp == "sim":
            now = time.time()
            if now < lockout_until:
                segundos = int(lockout_until - now)
                print(f"Muitas tentativas falhas. Aguarde {segundos} segundo(s).")
                continue

            usuario = input("Usuario: ").strip()
            senha = input("Senha: ").strip()
            if login_user(usuario, senha):
                print("Login realizado.")
                failed_login_attempts = 0
                key = find_user_key_case_insensitive(usuario)
                return key if key is not None else usuario

            failed_login_attempts += 1
            restantes = MAX_LOGIN_ATTEMPTS - failed_login_attempts
            if restantes > 0:
                print(f"Usuario ou senha incorretos. Tentativas restantes: {restantes}.")
            else:
                lockout_until = time.time() + LOGIN_LOCK_SECONDS
                failed_login_attempts = 0
                print(f"Acesso temporariamente bloqueado por {LOGIN_LOCK_SECONDS} segundos.")

        elif resp == "nao":
            usuario = input("Novo usuario (3-20, letras/numeros/_): ").strip()
            if not validate_username(usuario):
                print("Nome de usuario invalido.")
                continue
            if usuario in system_data["users"]:
                print("Esse usuario ja existe.")
                continue

            senha = input("Nova senha (min. 8, com maiuscula, minuscula e numero): ").strip()
            if not validate_password_strength(senha):
                print("Senha fraca. Use no minimo 8 caracteres com maiuscula, minuscula e numero.")
                continue
            confirmar = input("Confirmar senha: ").strip()
            if senha != confirmar:
                print("Confirmacao nao confere.")
                continue

            create_user(usuario, senha)
            print("Conta criada com sucesso.")
            return usuario
        else:
            print("Digite apenas sim ou nao.")


def switch_account() -> str | None:
    print("\nTrocar conta")
    usuario = input("Usuario destino: ").strip()
    senha = input("Senha do usuario destino: ").strip()
    if login_user(usuario, senha):
        key = find_user_key_case_insensitive(usuario)
        return key if key is not None else usuario
    print("Usuario ou senha incorretos.")
    return None


def sync_lists() -> None:
    global nomes, cats, valores, parcelas, datas, vencimentos
    size = min(len(nomes), len(cats), len(valores), len(parcelas), len(datas), len(vencimentos))
    nomes = nomes[:size]
    cats = cats[:size]
    valores = valores[:size]
    parcelas = parcelas[:size]
    datas = datas[:size]
    vencimentos = vencimentos[:size]


def remove_purchase(index: int) -> None:
    nomes.pop(index)
    cats.pop(index)
    valores.pop(index)
    parcelas.pop(index)
    datas.pop(index)
    vencimentos.pop(index)


def snapshot_purchase(index: int) -> dict | None:
    if not (0 <= index < len(nomes)):
        return None
    return {
        "nome": nomes[index],
        "cat": cats[index],
        "valor": valores[index],
        "parcela": parcelas[index],
        "data": datas[index],
        "vencimento": vencimentos[index],
    }


def restore_purchase(snapshot: dict, index: int | None = None) -> None:
    if snapshot["cat"] not in categorias:
        categorias.append(snapshot["cat"])

    if index is None or index < 0 or index > len(nomes):
        index = len(nomes)

    nomes.insert(index, snapshot["nome"])
    cats.insert(index, snapshot["cat"])
    valores.insert(index, snapshot["valor"])
    parcelas.insert(index, snapshot["parcela"])
    datas.insert(index, snapshot["data"])
    vencimentos.insert(index, snapshot["vencimento"])


def register_deleted_purchase(index: int, snapshot: dict) -> None:
    global last_deleted_action
    last_deleted_action = {
        "type": "purchase",
        "index": index,
        "snapshot": snapshot,
    }


def register_deleted_category(category_name: str, category_index: int, removed_purchases: list[tuple[int, dict]]) -> None:
    global last_deleted_action
    last_deleted_action = {
        "type": "category",
        "category_name": category_name,
        "category_index": category_index,
        "purchases": removed_purchases,
    }


def undo_last_deletion() -> None:
    global last_deleted_action
    if not last_deleted_action:
        print("Nenhuma exclusao para desfazer.")
        return

    action_type = last_deleted_action.get("type")

    if action_type == "purchase":
        snapshot = last_deleted_action.get("snapshot")
        index = int(last_deleted_action.get("index", len(nomes)))
        if not isinstance(snapshot, dict):
            print("Dados da ultima exclusao estao invalidos.")
            return
        restore_purchase(snapshot, index=index)
        persist_current_user()
        last_deleted_action = None
        print("Ultima compra excluida foi restaurada.")
        return

    if action_type == "category":
        category_name = str(last_deleted_action.get("category_name", "")).strip()
        category_index = int(last_deleted_action.get("category_index", len(categorias)))
        purchases = last_deleted_action.get("purchases", [])
        if not category_name or not isinstance(purchases, list):
            print("Dados da ultima exclusao estao invalidos.")
            return

        if category_name not in categorias:
            if 0 <= category_index <= len(categorias):
                categorias.insert(category_index, category_name)
            else:
                categorias.append(category_name)

        for purchase_index, snapshot in sorted(purchases, key=lambda x: x[0]):
            if isinstance(snapshot, dict):
                restore_purchase(snapshot, purchase_index)

        persist_current_user()
        last_deleted_action = None
        print("Ultima categoria excluida foi restaurada com suas compras.")
        return

    print("Tipo de exclusao nao suportado para desfazer.")


def validar_indice_1_based(total: int, texto: str) -> int | None:
    try:
        i = int(input(texto)) - 1
    except ValueError:
        return None
    if 0 <= i < total:
        return i
    return None


def print_purchase(i: int, show_category: bool = True, detailed_installment: bool = False) -> None:
    if not (0 <= i < len(nomes)):
        return

    parts = [i + 1, nomes[i]]
    if show_category:
        parts.append(cats[i])

    if parcelas[i] > 1:
        if detailed_installment:
            valor_txt = f"R$ {valores[i]:.2f} em {parcelas[i]}x de R$ {valores[i] / parcelas[i]:.2f}"
        else:
            valor_txt = f"R$ {valores[i]:.2f} em {parcelas[i]}x"
    else:
        valor_txt = f"R$ {valores[i]:.2f}"

    parts.append(valor_txt)
    parts.append(f"({datas[i]})")
    print(*parts)


def print_purchase_list(
    indices: list[int],
    show_category: bool = True,
    detailed_installment: bool = False,
) -> float:
    total = 0.0
    for i in indices:
        print_purchase(i, show_category=show_category, detailed_installment=detailed_installment)
        total += valores[i]
    return total


def choose_category(prompt: str = "Categoria: ") -> int | None:
    for i, cat in enumerate(categorias, start=1):
        print(i, cat)
    return validar_indice_1_based(len(categorias), prompt)


def limpar_compras_antigas(dias: int = 30) -> int:
    if not datas:
        return 0

    hoje = datetime.now()
    removidos = 0
    i = 0
    while i < len(datas):
        dt = parse_date(datas[i])
        if dt is None:
            i += 1
            continue

        if (hoje - dt).days >= dias:
            remove_purchase(i)
            removidos += 1
        else:
            i += 1

    if removidos:
        persist_current_user()
    return removidos


def limpar_arquivos_antigos(pasta: str = REPORT_DIR, dias: int = 30) -> int:
    if not os.path.exists(pasta):
        return 0

    hoje = datetime.now()
    removidos = 0
    for arquivo in os.listdir(pasta):
        caminho = os.path.join(pasta, arquivo)
        if not os.path.isfile(caminho):
            continue
        try:
            tempo_criacao = datetime.fromtimestamp(os.path.getctime(caminho))
            if (hoje - tempo_criacao).days >= dias:
                os.remove(caminho)
                removidos += 1
        except Exception:
            pass
    return removidos


def verificar_vencimentos() -> list[tuple[str, str, int]]:
    hoje = datetime.now()
    alertas = []
    for i, venc in enumerate(vencimentos):
        if not venc or venc == "-":
            continue
        data_venc = parse_date(venc)
        if data_venc is None:
            continue
        dias_restantes = (data_venc - hoje).days
        if dias_restantes < 7:
            alertas.append((nomes[i], venc, dias_restantes))
    return alertas

def enviar_email(destinatario, produto, data_venc):
    remetente = "seuemail@gmail.com"
    senha = "SENHA_DE_APP"

    assunto = "Aviso de vencimento"

    mensagem = f"""
Olá!

O produto "{produto}" vai vencer em {data_venc}.

Verifique seu gerenciador de compras.
"""

    msg = MIMEText(mensagem)
    msg["Subject"] = assunto
    msg["From"] = remetente
    msg["To"] = destinatario

    try:
        servidor = smtplib.SMTP("smtp.gmail.com", 587)
        servidor.starttls()
        servidor.login(remetente, senha)

        servidor.sendmail(remetente, destinatario, msg.as_string())
        servidor.quit()

        print("Email enviado.")
    except Exception as e:
        print("Erro ao enviar email:", e)
        
def exportar_excel():
    wb = Workbook()
    ws = wb.active
    ws.title = "Gastos"

    ws.append(["Produto", "Categoria", "Valor", "Parcelas", "Data", "Vencimento"])

    for i in range(len(nomes)):
        ws.append([
            nomes[i],
            cats[i],
            valores[i],
            parcelas[i],
            datas[i],
            vencimentos[i]
        ])

    wb.save("planilha_gastos.xlsx")

    print("Planilha criada com sucesso!")


def filtrar_por_categoria(categoria: str) -> list[int]:
    return [i for i, c in enumerate(cats) if c == categoria]


def buscar_produto(nome_busca: str) -> list[int]:
    termo = nome_busca.lower()
    return [i for i, nome in enumerate(nomes) if termo in nome.lower()]


def summarize_month_total(ref: datetime) -> float:
    total = 0.0
    for i, dt_str in enumerate(datas):
        dt = parse_date(dt_str)
        if dt is None:
            continue
        if dt.month == ref.month and dt.year == ref.year:
            total += valores[i]
    return total


def top_categories(limit: int = 3) -> list[tuple[str, float]]:
    totals = {}
    for i, cat in enumerate(cats):
        totals[cat] = totals.get(cat, 0.0) + valores[i]
    ordered = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    return ordered[:limit]


def show_dashboard() -> None:
    hoje = datetime.now()
    total_geral = sum(valores)
    total_mes = summarize_month_total(hoje)
    print("\nDASHBOARD RAPIDO")
    print(f"Usuario: {current_user}")
    print(f"Compras cadastradas: {len(nomes)}")
    print(f"Total geral: R$ {total_geral:.2f}")
    print(f"Total do mes ({hoje.strftime('%m/%Y')}): R$ {total_mes:.2f}")

    ranking = top_categories(3)
    if ranking:
        print("Top categorias:")
        for pos, (cat, valor) in enumerate(ranking, start=1):
            print(f"{pos}. {cat}: R$ {valor:.2f}")
    else:
        print("Top categorias: sem dados.")

    proximos = [a for a in verificar_vencimentos() if a[2] >= 0]
    print(f"Vencimentos nos proximos 7 dias: {len(proximos)}")


def search_advanced() -> list[int]:
    termo = input("Nome contem (enter para ignorar): ").strip().lower()

    categoria = ""
    usar_categoria = input("Filtrar por categoria? (sim/nao): ").strip().lower()
    if usar_categoria == "sim":
        for i, cat in enumerate(categorias, start=1):
            print(i, cat)
        idx_cat = validar_indice_1_based(len(categorias), "Categoria: ")
        if idx_cat is None:
            print("Categoria invalida.")
            return []
        categoria = categorias[idx_cat]

    valor_min = None
    entrada_min = input("Valor minimo (enter para ignorar): ").strip().replace(",", ".")
    if entrada_min:
        try:
            valor_min = float(entrada_min)
        except ValueError:
            print("Valor minimo invalido.")
            return []

    valor_max = None
    entrada_max = input("Valor maximo (enter para ignorar): ").strip().replace(",", ".")
    if entrada_max:
        try:
            valor_max = float(entrada_max)
        except ValueError:
            print("Valor maximo invalido.")
            return []

    data_ini = None
    txt_ini = input("Data inicial DD/MM/YYYY (enter para ignorar): ").strip()
    if txt_ini:
        data_ini = parse_date(txt_ini)
        if data_ini is None:
            print("Data inicial invalida.")
            return []

    data_fim = None
    txt_fim = input("Data final DD/MM/YYYY (enter para ignorar): ").strip()
    if txt_fim:
        data_fim = parse_date(txt_fim)
        if data_fim is None:
            print("Data final invalida.")
            return []

    if data_ini and data_fim and data_ini > data_fim:
        print("Intervalo de data invalido.")
        return []

    indices = []
    for i in range(len(nomes)):
        if termo and termo not in nomes[i].lower():
            continue
        if categoria and cats[i] != categoria:
            continue
        if valor_min is not None and valores[i] < valor_min:
            continue
        if valor_max is not None and valores[i] > valor_max:
            continue
        if data_ini or data_fim:
            dt = parse_date(datas[i])
            if dt is None:
                continue
            if data_ini and dt < data_ini:
                continue
            if data_fim and dt > data_fim:
                continue
        indices.append(i)
    return indices


def admin_panel() -> None:
    if not is_admin_or_higher(current_user):
        print("Acesso negado. Apenas admin/superadmin podem abrir este painel.")
        return

    senha = input("Confirme sua senha: ").strip()
    if not login_user(current_user, senha):
        print("Senha incorreta.")
        return

    print("\nPAINEL ADMIN")
    print(f"Role atual: {get_user_role(current_user)}")
    users = system_data.get("users", {})
    print(f"Total de usuarios: {len(users)}")
    for username, rec in users.items():
        if not isinstance(rec, dict):
            continue
        data = rec.get("data", {})
        nomes_user = data.get("nomes", [])
        valores_user = [coerce_float(v) for v in data.get("valores", [])]
        qtd = min(len(nomes_user), len(valores_user))
        total = sum(valores_user[:qtd])
        print(f"- {username}: {qtd} compra(s), total R$ {total:.2f}")


def find_user_key_case_insensitive(username: str) -> str | None:
    alvo = username.strip().lower()
    for key in system_data.get("users", {}).keys():
        if key.lower() == alvo:
            return key
    return None


def ensure_superadmin_account() -> None:
    key = find_user_key_case_insensitive(SUPERADMIN_USER)
    if key is None:
        system_data.setdefault("users", {})
        system_data["users"][SUPERADMIN_USER] = {
            "pin_hash": SUPERADMIN_BOOTSTRAP_PIN_HASH,
            "role": "superadmin",
            "data": default_user_data(),
        }
        save_system_data(make_backup=False)
        return

    rec = system_data["users"].get(key, {})
    if isinstance(rec, dict):
        rec["role"] = "superadmin"


def ensure_admin_account() -> None:
    key = find_user_key_case_insensitive(ADMIN_USER)
    if key is None:
        system_data.setdefault("users", {})
        system_data["users"][ADMIN_USER] = {
            "pin_hash": ADMIN_BOOTSTRAP_PIN_HASH,
            "role": "admin",
            "data": default_user_data(),
        }
        save_system_data(make_backup=False)
        return

    rec = system_data["users"].get(key, {})
    if isinstance(rec, dict) and rec.get("role") not in {"admin", "superadmin"}:
        rec["role"] = "admin"


def authenticate_superadmin_for_reset() -> bool:
    key = find_user_key_case_insensitive(SUPERADMIN_USER)
    if current_user.lower() != SUPERADMIN_USER.lower():
        print("Acesso negado. Apenas o super admin pode executar restauracao de fabrica.")
        return False

    senha_master = input("Senha mestre do super admin: ").strip()
    if not verify_sha256_secret(senha_master, SUPERADMIN_MASTER_PASSWORD_SHA256):
        print("Senha mestre incorreta.")
        return False

    if key is None:
        print("Conta super admin nao encontrada.")
        return False

    pergunta = input(f"{SUPERADMIN_SECURITY_QUESTION} ").strip().lower()
    if not verify_sha256_secret(pergunta, SUPERADMIN_SECURITY_ANSWER_SHA256):
        print("Resposta de seguranca incorreta.")
        return False

    senha_conta = input("Confirme a senha da conta logada: ").strip()
    if not login_user(key, senha_conta):
        print("Senha da conta incorreta.")
        return False

    confirmar = input("Digite APAGAR TUDO para confirmar: ").strip()
    if confirmar != "APAGAR TUDO":
        print("Confirmacao nao realizada.")
        return False

    return True


def restore_factory() -> None:
    global current_user
    if not authenticate_superadmin_for_reset():
        return

    print("\nTipo de restauracao:")
    print("1 Restaurar apenas a conta atual")
    print("2 Restaurar sistema inteiro (todos os usuarios)")
    escolha = input("Escolha: ").strip()

    if escolha not in {"1", "2"}:
        print("Opcao invalida.")
        return

    save_system_data(make_backup=True)

    if escolha == "1":
        key = find_user_key_case_insensitive(current_user)
        if key is None:
            print("Conta atual nao encontrada.")
            return
        system_data["users"][key]["data"] = default_user_data()
        save_system_data(make_backup=False)
        load_user_data(key)
        print("Conta atual restaurada para padrao com sucesso.")
        show_dashboard()
        return

    super_key = find_user_key_case_insensitive(SUPERADMIN_USER)
    super_hash = ""
    if super_key is not None and isinstance(system_data["users"].get(super_key), dict):
        super_hash = str(system_data["users"][super_key].get("pin_hash", ""))

    if not super_hash:
        super_hash = SUPERADMIN_BOOTSTRAP_PIN_HASH

    system_data.clear()
    system_data["users"] = {
        SUPERADMIN_USER: {
            "pin_hash": super_hash,
            "role": "superadmin",
            "data": default_user_data(),
        }
    }
    save_system_data(make_backup=False)
    current_user = SUPERADMIN_USER
    load_user_data(current_user)
    print("Sistema restaurado para fabrica com sucesso.")
    show_dashboard()


def superadmin_tools() -> None:
    if not is_superadmin(current_user):
        print("Acesso negado. Ferramentas exclusivas do super admin.")
        return

    senha = input("Confirme sua senha de super admin: ").strip()
    if not login_user(current_user, senha):
        print("Senha incorreta.")
        return

    while True:
        print("\nSUPER ADMIN - FERRAMENTAS")
        print("1 Listar usuarios e papeis")
        print("2 Alterar papel de usuario (user/admin)")
        print("3 Resetar senha de usuario")
        print("4 Resetar dados de usuario")
        print("5 Excluir usuario")
        print("0 Voltar")
        escolha = input("Escolha: ").strip()

        if escolha == "0":
            return

        if escolha == "1":
            for uname, rec in system_data.get("users", {}).items():
                if not isinstance(rec, dict):
                    continue
                role = str(rec.get("role", "user"))
                data = rec.get("data", {})
                qtd = len(data.get("nomes", [])) if isinstance(data, dict) else 0
                print(f"- {uname} | role={role} | compras={qtd}")

        elif escolha == "2":
            alvo = input("Usuario alvo: ").strip()
            key = find_user_key_case_insensitive(alvo)
            if key is None:
                print("Usuario nao encontrado.")
                continue
            if key.lower() == SUPERADMIN_USER.lower():
                print("Nao e permitido alterar papel do super admin.")
                continue
            novo_role = input("Novo papel (user/admin): ").strip().lower()
            if novo_role not in {"user", "admin"}:
                print("Papel invalido.")
                continue
            system_data["users"][key]["role"] = novo_role
            save_system_data(make_backup=False)
            print("Papel atualizado.")

        elif escolha == "3":
            alvo = input("Usuario alvo: ").strip()
            key = find_user_key_case_insensitive(alvo)
            if key is None:
                print("Usuario nao encontrado.")
                continue
            nova = input("Nova senha (min. 8, com maiuscula, minuscula e numero): ").strip()
            if not validate_password_strength(nova):
                print("Senha fraca. Use no minimo 8 caracteres com maiuscula, minuscula e numero.")
                continue
            system_data["users"][key]["pin_hash"] = hash_pin(nova)
            save_system_data(make_backup=False)
            print("Senha resetada.")

        elif escolha == "4":
            alvo = input("Usuario alvo: ").strip()
            key = find_user_key_case_insensitive(alvo)
            if key is None:
                print("Usuario nao encontrado.")
                continue
            confirm = input("Digite RESETAR DADOS para confirmar: ").strip()
            if confirm != "RESETAR DADOS":
                print("Confirmacao invalida.")
                continue
            system_data["users"][key]["data"] = default_user_data()
            save_system_data(make_backup=False)
            if key.lower() == current_user.lower():
                load_user_data(key)
            print("Dados do usuario resetados.")

        elif escolha == "5":
            alvo = input("Usuario alvo: ").strip()
            key = find_user_key_case_insensitive(alvo)
            if key is None:
                print("Usuario nao encontrado.")
                continue
            if key.lower() == SUPERADMIN_USER.lower():
                print("Nao e permitido excluir o super admin.")
                continue
            if key.lower() == current_user.lower():
                print("Nao e permitido excluir a propria conta logada.")
                continue
            confirm = input("Digite EXCLUIR USUARIO para confirmar: ").strip()
            if confirm != "EXCLUIR USUARIO":
                print("Confirmacao invalida.")
                continue
            system_data["users"].pop(key, None)
            save_system_data(make_backup=False)
            print("Usuario excluido.")

        else:
            print("Opcao invalida.")

def gerar_pdf() -> str | None:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except Exception:
        print("Erro: biblioteca reportlab nao instalada. Execute: pip install reportlab")
        return None

    ensure_dirs()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    user_safe = re.sub(r"[^a-zA-Z0-9_]", "_", current_user)
    pdf_name = os.path.join(REPORT_DIR, f"relatorio_{user_safe}_{timestamp}.pdf")

    try:
        doc = SimpleDocTemplate(pdf_name, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph(f"<b>RELATORIO DE COMPRAS - {current_user}</b>", styles["Title"]))
        story.append(Paragraph(datetime.now().strftime(DATE_FMT), styles["Normal"]))
        story.append(Spacer(1, 12))

        table_data = [["#", "Produto", "Categoria", "Valor", "Parcelas", "Data", "Vencimento"]]
        for i in range(len(nomes)):
            table_data.append([
                str(i + 1),
                nomes[i],
                cats[i],
                f"R$ {valores[i]:.2f}",
                str(parcelas[i]),
                datas[i],
                vencimentos[i] if vencimentos[i] else "-",
            ])

        table = Table(table_data)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(table)
        story.append(Spacer(1, 12))

        total = sum(valores)
        total_parcelas = sum(v for i, v in enumerate(valores) if parcelas[i] > 1)
        story.append(Paragraph(
            f"<b>Total: R$ {total:.2f}</b><br/><b>Em parcelas: R$ {total_parcelas:.2f}</b><br/><b>Compras: {len(nomes)}</b>",
            styles["Normal"],
        ))

        doc.build(story)
        print(f"PDF gerado: {pdf_name}")
        return pdf_name
    except Exception as e:
        print(f"Erro ao gerar PDF: {e}")
        return None


def editar_compra(indice: int) -> bool:
    if not (0 <= indice < len(nomes)):
        print("Indice invalido.")
        return False

    print(f"\nEditando: {nomes[indice]}")
    print("1 Nome")
    print("2 Valor total")
    print("3 Parcelas")
    print("4 Categoria")
    print("5 Vencimento")
    print("0 Cancelar")

    try:
        escolha = int(input("Opcao: "))
    except ValueError:
        print("Entrada invalida.")
        return False

    if escolha == 1:
        novo_nome = input("Novo nome: ").strip()
        if not novo_nome:
            print("Nome vazio.")
            return False
        nomes[indice] = novo_nome
    elif escolha == 2:
        try:
            novo_valor = float(input("Novo valor total: "))
            if novo_valor < 0:
                print("Valor invalido.")
                return False
            valores[indice] = novo_valor
        except ValueError:
            print("Valor invalido.")
            return False
    elif escolha == 3:
        try:
            novo_parc = int(input("Novas parcelas: "))
            if novo_parc <= 0:
                print("Parcelas invalidas.")
                return False
            parcelas[indice] = novo_parc
        except ValueError:
            print("Parcelas invalidas.")
            return False
    elif escolha == 4:
        for i, cat in enumerate(categorias, start=1):
            print(i, cat)
        idx = validar_indice_1_based(len(categorias), "Nova categoria: ")
        if idx is None:
            print("Categoria invalida.")
            return False
        cats[indice] = categorias[idx]
    elif escolha == 5:
        novo_venc = input("Novo vencimento (DD/MM/YYYY ou -): ").strip()
        if novo_venc != "-" and parse_date(novo_venc) is None:
            print("Data invalida.")
            return False
        vencimentos[indice] = novo_venc
    elif escolha == 0:
        return False
    else:
        print("Opcao invalida.")
        return False

    persist_current_user()
    print("Compra atualizada.")
    return True


def alterar_senha_conta() -> None:
    rec = system_data["users"].get(current_user, {})
    pin_hash = str(rec.get("pin_hash", ""))

    atual = input("Senha atual: ").strip()
    if not verify_pin(atual, pin_hash):
        print("Senha atual incorreta.")
        return

    nova = input("Nova senha (min. 8, com maiuscula, minuscula e numero): ").strip()
    if not validate_password_strength(nova):
        print("Senha fraca. Use no minimo 8 caracteres com maiuscula, minuscula e numero.")
        return

    confirmar = input("Confirme a nova senha: ").strip()
    if nova != confirmar:
        print("Confirmacao nao confere.")
        return

    system_data["users"][current_user]["pin_hash"] = hash_pin(nova)
    save_system_data(make_backup=False)
    print("Senha alterada com sucesso.")


# Estado global do usuario logado
nomes = []
cats = []
valores = []
parcelas = []
datas = []
vencimentos = []
orcamento_mensal = 0.0
categorias = DEFAULT_CATEGORIES.copy()
last_deleted_action = None

raw = load_json_file()
system_data = migrate_legacy_if_needed(raw)
if "users" not in system_data or not isinstance(system_data["users"], dict):
    system_data = {"users": {}}
for _user, _rec in list(system_data["users"].items()):
    if not isinstance(_rec, dict):
        default_role = "admin" if _user.lower() == ADMIN_USER.lower() else "user"
        if _user.lower() == SUPERADMIN_USER.lower():
            default_role = "superadmin"
        system_data["users"][_user] = {"pin_hash": "", "role": default_role, "data": default_user_data()}
        continue
    if "data" not in _rec or not isinstance(_rec["data"], dict):
        _rec["data"] = default_user_data()
    if "role" not in _rec:
        _rec["role"] = "admin" if _user.lower() == ADMIN_USER.lower() else "user"
    if _user.lower() == SUPERADMIN_USER.lower():
        _rec["role"] = "superadmin"
    elif _user.lower() == ADMIN_USER.lower() and _rec.get("role") != "superadmin":
        _rec["role"] = "admin"

ensure_superadmin_account()
ensure_admin_account()
current_user = startup_auth()
load_user_data(current_user)
show_dashboard()

removidos_rel = limpar_arquivos_antigos(REPORT_DIR, 30)
if removidos_rel:
    print(f"{removidos_rel} relatorio(s) antigo(s) apagado(s).")

alertas_inicio = verificar_vencimentos()
if alertas_inicio:
    print("\nALERTAS DE VENCIMENTO:")
    for nome, venc, dias in alertas_inicio:
        if dias < 0:
            print(f"- {nome}: vencido em {venc} (ha {abs(dias)} dia(s))")
        elif dias == 0:
            print(f"- {nome}: vence hoje ({venc})")
        else:
            print(f"- {nome}: vence em {dias} dia(s) ({venc})")

try:
    removidas = limpar_compras_antigas(30)
    if removidas:
        print(f"{removidas} compra(s) com mais de 30 dias removidas automaticamente.")
except Exception:
    pass
email = system_data["users"][current_user]["data"].get("email", "")

for nome, venc, dias in alertas_inicio:
    if dias <= 3 and email:
        enviar_email(email, nome, venc)

while True:
    print(f"\nGERENCIADOR - Usuario: {current_user} ({get_user_role(current_user)})")
    print("1 Adicionar")
    print("2 Mostrar")
    print("3 Total geral")
    print("4 Total por categoria")
    print("5 Nova categoria")
    print("6 Deletar compra")
    print("7 Deletar categoria")
    print("8 Total em parcelas")
    print("9 Filtrar por categoria")
    print("10 Busca avancada")
    print("11 Editar compra")
    print("12 Definir orcamento")
    print("13 Ver orcamento")
    print("14 Gerar PDF")
    print("15 Ver vencimentos")
    print("16 Sobre")
    print("17 Ajuda")
    print("18 Sair")
    print("19 Alterar senha da conta")
    print("20 Trocar conta")
    print("21 Painel admin")
    print("22 Restauracao de fabrica (Super Admin)")
    print("23 Ferramentas Super Admin")
    print("24 Desfazer ultima exclusao")
    print("25 Configurar email")
    print("26 Exportar planilha Excel")

    try:
        op = int(input("Escolha: "))
    except ValueError:
        print("Opcao invalida. Digite um numero.")
        continue

    if op < 1 or op > 26:
        print("Opcao fora do intervalo.")
        continue

    if op == 1:
        nome = input("Produto: ").strip()
        if not nome:
            print("Nome vazio. Operacao cancelada.")
            continue

        try:
            preco = float(input("Preco unitario: "))
            if preco < 0:
                print("Preco invalido.")
                continue
        except ValueError:
            print("Preco invalido.")
            continue

        try:
            qtd = int(input("Quantidade: "))
            if qtd <= 0:
                print("Quantidade deve ser positiva.")
                continue
        except ValueError:
            print("Quantidade invalida.")
            continue

        parc = input("Vai parcelar? (sim/nao): ").strip().lower()
        if parc == "sim":
            try:
                qtdparcela = int(input("Em quantas vezes? "))
                if qtdparcela <= 0:
                    print("Numero de parcelas invalido.")
                    continue
            except ValueError:
                print("Numero de parcelas invalido.")
                continue
        else:
            qtdparcela = 1

        idx_cat = choose_category("Categoria: ")
        if idx_cat is None:
            print("Categoria invalida.")
            continue

        tem_venc = input("Tem data de vencimento? (sim/nao): ").strip().lower()
        if tem_venc == "sim":
            data_venc = input("Data de vencimento (DD/MM/YYYY): ").strip()
            if parse_date(data_venc) is None:
                print("Data invalida. Usando '-'.")
                data_venc = "-"
        else:
            data_venc = "-"

        nomes.append(nome)
        cats.append(categorias[idx_cat])
        valores.append(preco * qtd)
        parcelas.append(qtdparcela)
        datas.append(datetime.now().strftime(DATE_FMT))
        vencimentos.append(data_venc)
        persist_current_user()
        print("Salvo.")

    elif op == 2:
        if not nomes:
            print("Nada salvo.")
            continue
        print_purchase_list(list(range(len(nomes))), show_category=True, detailed_installment=True)

    elif op == 3:
        print(f"Total geral: R$ {sum(valores):.2f}")

    elif op == 4:
        for cat in categorias:
            total = sum(valores[i] for i, c in enumerate(cats) if c == cat)
            print(f"{cat}: R$ {total:.2f}")

    elif op == 5:
        nova = input("Nome da categoria: ").strip()
        if not nova:
            print("Nome vazio.")
        elif nova in categorias:
            print("Categoria ja existe.")
        else:
            categorias.append(nova)
            persist_current_user()
            print("Categoria criada.")

    elif op == 6:
        if not nomes:
            print("Nao ha compras para apagar.")
            continue
        for i, nome in enumerate(nomes, start=1):
            print(i, nome)
        idx = validar_indice_1_based(len(nomes), "Qual compra apagar? ")
        if idx is None:
            print("Indice invalido.")
            continue
        snapshot = snapshot_purchase(idx)
        remove_purchase(idx)
        if isinstance(snapshot, dict):
            register_deleted_purchase(idx, snapshot)
        persist_current_user()
        print("Compra apagada.")

    elif op == 7:
        idx = choose_category("Qual categoria apagar? ")
        if idx is None:
            print("Indice invalido.")
            continue

        cat = categorias[idx]
        if cat in DEFAULT_CATEGORIES:
            print("Categoria fixa nao pode ser apagada.")
            continue

        deleted_purchases = []
        categorias.pop(idx)
        i = 0
        while i < len(cats):
            if cats[i] == cat:
                snapshot = snapshot_purchase(i)
                if isinstance(snapshot, dict):
                    deleted_purchases.append((i, snapshot))
                remove_purchase(i)
            else:
                i += 1
        register_deleted_category(cat, idx, deleted_purchases)
        persist_current_user()
        print("Categoria apagada.")

    elif op == 8:
        total_parcelado = sum(valores[i] for i in range(len(parcelas)) if parcelas[i] > 1)
        print(f"Total em parcelas: R$ {total_parcelado:.2f}")

    elif op == 9:
        print("\nCATEGORIAS:")
        idx = choose_category("Qual categoria? ")
        if idx is None:
            print("Categoria invalida.")
            continue

        categoria = categorias[idx]
        indices = filtrar_por_categoria(categoria)
        if not indices:
            print(f"Nenhuma compra em '{categoria}'.")
            continue

        print(f"\nCOMPRAS EM {categoria}:")
        subtotal = print_purchase_list(indices, show_category=False, detailed_installment=False)
        print(f"Subtotal: R$ {subtotal:.2f}")

    elif op == 10:
        indices = search_advanced()
        if not indices:
            print("Nenhuma compra encontrada.")
            continue

        print(f"\nRESULTADOS ({len(indices)}):")
        total = print_purchase_list(indices, show_category=True, detailed_installment=False)
        print(f"Total: R$ {total:.2f}")

    elif op == 11:
        if not nomes:
            print("Nao ha compras para editar.")
            continue
        print_purchase_list(list(range(len(nomes))), show_category=True, detailed_installment=False)
        idx = validar_indice_1_based(len(nomes), "Qual compra editar? ")
        if idx is None:
            print("Indice invalido.")
            continue
        editar_compra(idx)

    elif op == 12:
        try:
            novo = float(input("Orcamento mensal (R$): "))
            if novo < 0:
                print("Orcamento nao pode ser negativo.")
                continue
            orcamento_mensal = novo
            persist_current_user()
            print(f"Orcamento definido para R$ {orcamento_mensal:.2f}")
        except ValueError:
            print("Valor invalido.")

    elif op == 13:
        total = sum(valores)
        if orcamento_mensal <= 0:
            print("Nenhum orcamento definido.")
            continue
        pct = (total / orcamento_mensal) * 100 if orcamento_mensal else 0
        print("\nORCAMENTO MENSAL")
        print(f"Limite: R$ {orcamento_mensal:.2f}")
        print(f"Gasto: R$ {total:.2f}")
        print(f"Disponivel: R$ {orcamento_mensal - total:.2f}")
        print(f"Utilizado: {pct:.1f}%")
        if pct > 100:
            print(f"ORCAMENTO EXCEDIDO em R$ {total - orcamento_mensal:.2f}")
        elif pct > 80:
            print("Atencao: acima de 80% do orcamento.")

    elif op == 14:
        pdf = gerar_pdf()
        if pdf:
            print(f"Relatorio salvo em: {pdf}")

    elif op == 15:
        alertas = verificar_vencimentos()
        if not alertas:
            print("Nenhuma compra vencida ou proxima de vencer.")
            continue
        print("\nALERTAS DE VENCIMENTO:")
        for nome, venc, dias in alertas:
            if dias < 0:
                print(f"- {nome}: vencido em {venc} (ha {abs(dias)} dia(s))")
            elif dias == 0:
                print(f"- {nome}: vence hoje ({venc})")
            else:
                print(f"- {nome}: vence em {dias} dia(s) ({venc})")

    elif op == 16:
        print("\nSOBRE")
        print("Autor: Bernardo Alves Caetano")
        print("Python | Gerenciador de compras")
        print("Criado em fevereiro de 2026")
        print("Objetivo: organizar compras e gastos mensais por conta de usuario.")

    elif op == 17:
        print("Use o menu digitando o numero da opcao desejada.")

    elif op == 18:
        persist_current_user()
        print("Ate mais.")
        break

    elif op == 19:
        alterar_senha_conta()

    elif op == 20:
        novo_usuario = switch_account()
        if novo_usuario is not None:
            persist_current_user(make_backup=False)
            current_user = novo_usuario
            load_user_data(current_user)
            print(f"Conta trocada. Usuario atual: {current_user}")
            show_dashboard()

    elif op == 21:
        admin_panel()

    elif op == 22:
        restore_factory()

    elif op == 23:
        superadmin_tools()

    elif op == 24:
        undo_last_deletion()
    
    elif op == 25:
        email = input("Digite seu email para receber alertas: ").strip()

        if "@" not in email:
            print("Email invalido.")
        else:
            system_data["users"][current_user]["data"]["email"] = email
            save_system_data()
            print("Email salvo com sucesso.")
            
    elif op == 26:
        exportar_excel()

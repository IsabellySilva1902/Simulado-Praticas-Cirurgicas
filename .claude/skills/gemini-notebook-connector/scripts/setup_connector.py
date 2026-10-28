#!/usr/bin/env python3
"""
Conecta o Claude Code ao Gemini Notebook via MCP, usando os comandos oficiais
do projeto notebooklm-mcp-cli (nlm setup / nlm login / nlm doctor).

ÚNICA finalidade deste script: deixar a conexão pronta. Não lista notebooks,
não consulta conteúdo, não gera slide/podcast/flashcard — isso é feito pelo
usuário depois, conversando normalmente com o Claude Code.

Fluxo:
1. Verifica se o Claude Code está instalado. Se não estiver, para aqui —
   não tenta instalar nada.
2. Verifica quais dependências (uv, notebooklm-mcp-cli) faltam. Se faltar
   algo, só instala com autorização explícita (AUTHORIZE_INSTALL=1).
3. Detecta pacotes legados conflitantes — se encontrar sem CONFIRM_CLEAN=1,
   para (não instala por cima de um conflito conhecido).
4. Configura o MCP no Claude Code via `nlm setup add claude-code`.
5. Executa `nlm login` de verdade — abre o navegador e ESPERA o usuário
   concluir o login manualmente.
6. Depois do login, verifica a autenticação (`nlm login --check`).
7. Só então roda o diagnóstico final (`nlm doctor`).
8. Só informa "conexão pronta" se MCP + autenticação + diagnóstico
   estiverem todos OK. Caso contrário, aponta exatamente qual etapa falhou.

Variáveis de ambiente:
  DRY_RUN=1           mostra o que SERIA feito, sem executar nada de verdade
                       (inclusive não abre navegador nem tenta login real)
  AUTHORIZE_INSTALL=1 autoriza instalar uv/notebooklm-mcp-cli se estiverem
                       faltando (sem isso, o script só reporta e para)
  CONFIRM_CLEAN=1     autoriza remover pacotes legados detectados

Nota sobre Windows: o Claude Code no Windows normalmente depende de WSL ou
Git Bash. Este fluxo não foi validado nesse cenário.

Este script NUNCA grava cookies, tokens ou credenciais em arquivo dentro
desta skill — a autenticação do `nlm login` é gerenciada pelo próprio
notebooklm-mcp-cli fora desta pasta.
"""

import os
import platform
import shutil
import subprocess
import sys

DRY_RUN = os.environ.get("DRY_RUN") == "1"
AUTHORIZE_INSTALL = os.environ.get("AUTHORIZE_INSTALL") == "1"
CONFIRM_CLEAN = os.environ.get("CONFIRM_CLEAN") == "1"

LEGACY_PACKAGE_NAMES = ["notebooklm-mcp-server", "notebooklm-cli"]
CURRENT_PACKAGE = "notebooklm-mcp-cli"

COMMON_UV_DIRS = [
    os.path.expanduser("~/.local/bin"),
    os.path.expanduser("~/.cargo/bin"),
]


def log(msg, level="INFO"):
    icons = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "STEP": "▶️", "ERROR": "❌"}
    print(f"{icons.get(level, '')} {msg}")


def status_line(label, ok):
    icon = "✅" if ok else "❌"
    print(f"{icon} {label}")


def command_exists(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def run(cmd, check=True, allow_in_dry_run=False):
    prefix = "(dry-run, não executado) " if (DRY_RUN and not allow_in_dry_run) else "Executando: "
    log(prefix + " ".join(cmd), "STEP")
    if DRY_RUN and not allow_in_dry_run:
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
    try:
        return subprocess.run(cmd, capture_output=True, text=True, check=check)
    except FileNotFoundError as e:
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr=str(e))


# ---------------------------------------------------------------------------
# 1. Claude Code precisa já estar instalado — este script não instala o
#    Claude Code em si, só a ponte MCP pra ele.
# ---------------------------------------------------------------------------

def ensure_claude_code_installed():
    if command_exists("claude"):
        log("Claude Code encontrado.", "OK")
        return True
    log("Claude Code não encontrado (comando 'claude' ausente do PATH). "
        "Esta skill só serve pra conectar o Claude Code já instalado ao "
        "Gemini Notebook — instale o Claude Code primeiro.", "ERROR")
    return False


# ---------------------------------------------------------------------------
# 2. Dependências (uv, notebooklm-mcp-cli) — só instala com autorização
# ---------------------------------------------------------------------------

def refresh_path():
    current = os.environ.get("PATH", "")
    parts = current.split(os.pathsep)
    changed = False
    for d in COMMON_UV_DIRS:
        if os.path.isdir(d) and d not in parts:
            parts.insert(0, d)
            changed = True
    if changed:
        os.environ["PATH"] = os.pathsep.join(parts)
        log("PATH desta sessão atualizado com diretórios comuns do uv.", "INFO")


def list_missing_dependencies():
    missing = []
    if not command_exists("uv"):
        missing.append("uv")
    if command_exists("uv"):
        result = run(["uv", "tool", "list"], check=False, allow_in_dry_run=True)
        if CURRENT_PACKAGE not in (result.stdout or ""):
            missing.append(CURRENT_PACKAGE)
    elif "uv" not in missing:
        missing.append(CURRENT_PACKAGE)
    return missing


def install_uv():
    if command_exists("uv"):
        return True
    log("Instalando uv...", "STEP")
    system = platform.system()
    if system == "Windows":
        run(["powershell", "-ExecutionPolicy", "ByPass", "-Command",
             "irm https://astral.sh/uv/install.ps1 | iex"], check=False)
    else:
        run(["sh", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"], check=False)
    refresh_path()
    if command_exists("uv"):
        log("uv instalado.", "OK")
        return True
    log("uv foi instalado, mas ainda não está visível nesta sessão (limitação "
        "conhecida de PATH). Feche e abra um terminal/sessão novo do Claude "
        "Code e rode este script de novo.", "ERROR")
    return False


def install_notebooklm_cli():
    result = run(["uv", "tool", "list"], check=False, allow_in_dry_run=True)
    if CURRENT_PACKAGE in (result.stdout or ""):
        log(f"{CURRENT_PACKAGE} já instalado.", "OK")
        return True
    log(f"Instalando {CURRENT_PACKAGE}...", "STEP")
    result = run(["uv", "tool", "install", CURRENT_PACKAGE], check=False)
    if result.returncode != 0:
        log(f"Falha ao instalar {CURRENT_PACKAGE}: {result.stderr}", "ERROR")
        return False
    log(f"{CURRENT_PACKAGE} instalado.", "OK")
    return True


def ensure_dependencies():
    if DRY_RUN:
        missing = list_missing_dependencies()
        if missing:
            log(f"(dry-run) Seria necessário instalar: {', '.join(missing)}.", "INFO")
        else:
            log("(dry-run) Dependências já estariam satisfeitas.", "INFO")
        return True

    missing = list_missing_dependencies()
    if not missing:
        log("Dependências (uv, notebooklm-mcp-cli) já estão instaladas.", "OK")
        return True

    if not AUTHORIZE_INSTALL:
        log(f"As seguintes dependências precisam ser instaladas: {', '.join(missing)}.",
            "WARN")
        log("Nada foi instalado. Confirme com o usuário e rode de novo com "
            "AUTHORIZE_INSTALL=1 para autorizar.", "ERROR")
        return False

    if not install_uv():
        return False
    return install_notebooklm_cli()


# ---------------------------------------------------------------------------
# 3. Pacotes legados — para o setup se encontrar, sem confirmação explícita
# ---------------------------------------------------------------------------

def handle_legacy_packages():
    if DRY_RUN:
        log("(dry-run) verificação de pacotes legados seria feita aqui.", "INFO")
        return True
    result = run(["uv", "tool", "list"], check=False, allow_in_dry_run=True)
    found = [pkg for pkg in LEGACY_PACKAGE_NAMES if pkg in (result.stdout or "")]
    if not found:
        return True
    log(f"Pacote(s) legado(s) encontrado(s): {', '.join(found)}.", "WARN")
    if not CONFIRM_CLEAN:
        log("Setup INTERROMPIDO — não vou instalar por cima de um conflito "
            "conhecido. Confirme com o usuário e rode de novo com "
            "CONFIRM_CLEAN=1.", "ERROR")
        return False
    for pkg in found:
        log(f"Removendo {pkg} (CONFIRM_CLEAN=1)...", "STEP")
        run(["uv", "tool", "uninstall", pkg], check=False)
    log("Reinstalando com --force pra corrigir eventuais symlinks quebrados...", "STEP")
    run(["uv", "tool", "install", "--force", CURRENT_PACKAGE], check=False)
    return True


# ---------------------------------------------------------------------------
# 4. Configurar MCP no Claude Code
# ---------------------------------------------------------------------------

def setup_claude_code_mcp():
    if DRY_RUN:
        log("(dry-run) 'nlm setup add claude-code' seria executado agora.", "INFO")
        return True
    log("Registrando o servidor MCP no Claude Code ('nlm setup add claude-code')...", "STEP")
    result = run(["nlm", "setup", "add", "claude-code"], check=False)
    if result.returncode != 0:
        log(f"'nlm setup add claude-code' falhou: {result.stderr}", "ERROR")
        return False
    log("MCP configurado no Claude Code.", "OK")
    return True


# ---------------------------------------------------------------------------
# 5 e 6. Login real (abre navegador, espera o usuário) + verificação
# ---------------------------------------------------------------------------

def do_login():
    if DRY_RUN:
        log("(dry-run) 'nlm login' seria executado agora, abrindo o navegador.", "INFO")
        return True

    log("Abrindo o navegador para login do Google. Complete o login na janela "
        "que abrir — este script espera até você terminar.", "STEP")
    log("IMPORTANTE: essa autenticação usa cookies da sua sessão Google, não é "
        "OAuth com permissões delimitadas. Trate como credencial sensível.",
        "WARN")

    # Não capturamos stdout/stderr aqui de propósito: 'nlm login' pode
    # precisar exibir uma URL pro usuário copiar manualmente, ou mensagens
    # de status durante a espera — isso precisa aparecer no terminal em
    # tempo real, não ser engolido e só mostrado no final.
    try:
        result = subprocess.run(["nlm", "login"])
    except FileNotFoundError:
        log("Comando 'nlm' não encontrado — a instalação anterior pode ter falhado.", "ERROR")
        return False

    if result.returncode != 0:
        log("O comando 'nlm login' terminou com código de erro. O login pode não "
            "ter sido concluído.", "ERROR")
        return False
    log("Comando de login finalizado.", "OK")
    return True


def verify_authentication():
    if DRY_RUN:
        log("(dry-run) autenticação seria verificada agora ('nlm login --check').", "INFO")
        return True
    log("Verificando autenticação ('nlm login --check')...", "STEP")
    result = run(["nlm", "login", "--check"], check=False, allow_in_dry_run=True)
    ok = result.returncode == 0
    if ok:
        log("Autenticação confirmada.", "OK")
    else:
        log(f"Autenticação NÃO confirmada: {(result.stdout or result.stderr).strip()}",
            "ERROR")
    return ok


# ---------------------------------------------------------------------------
# 7. Diagnóstico final — só depois do login
# ---------------------------------------------------------------------------

def run_doctor():
    if DRY_RUN:
        log("(dry-run) 'nlm doctor' seria executado agora.", "INFO")
        return True
    log("Rodando diagnóstico oficial ('nlm doctor')...", "STEP")
    result = run(["nlm", "doctor"], check=False, allow_in_dry_run=True)
    print(result.stdout or result.stderr)
    return result.returncode == 0


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    log("=== Conectar Claude Code <-> Gemini Notebook (MCP) ===", "STEP")
    if DRY_RUN:
        log("MODO DRY-RUN — nada será executado de verdade, nem login real.", "WARN")

    if not ensure_claude_code_installed():
        sys.exit(1)

    if not ensure_dependencies():
        sys.exit(1)

    if not handle_legacy_packages():
        sys.exit(1)

    mcp_ok = setup_claude_code_mcp()
    if not mcp_ok:
        sys.exit(1)

    login_ok = do_login()
    auth_ok = verify_authentication() if login_ok else False
    doctor_ok = run_doctor()

    print()
    log("=== Resultado final ===", "STEP")
    status_line("MCP configurado no Claude Code", mcp_ok)
    status_line("Login/autenticação Google confirmada", auth_ok)
    status_line("Diagnóstico (nlm doctor) OK", doctor_ok)
    print()

    if mcp_ok and auth_ok and doctor_ok:
        log("CONEXÃO PRONTA. Teste perguntando: 'Liste meus notebooks do Gemini Notebook'", "OK")
    else:
        log("CONEXÃO NÃO ESTÁ COMPLETA — veja acima exatamente qual etapa falhou "
            "antes de prosseguir. Não prometa ao usuário que está tudo pronto.",
            "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()

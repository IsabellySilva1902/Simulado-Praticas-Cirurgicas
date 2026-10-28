#!/usr/bin/env python3
"""
Renova a autenticação do Gemini Notebook e diagnostica as causas conhecidas
de "sessão expirou de novo".

Ordem:
1. Verifica a causa nº1 documentada: a variável de ambiente
   NOTEBOOKLM_COOKIES. Quando ela existe, tem prioridade ABSOLUTA sobre
   auth.json, perfil de browser e `nlm login` — e quando os cookies dela
   vencem, nenhuma re-autenticação resolve, porque o valor velho fica
   preso no processo. Se detectar, o script PARA e explica como remover.
2. Avisa que o Chrome (ou browser da família Chromium) precisa estar
   totalmente fechado antes do login — com o browser aberto a extração
   de cookies fica instável e a sessão cai logo depois.
3. Roda `nlm login` (abre o navegador, espera você concluir).
4. Confirma com `nlm login --check`.

Variáveis de ambiente:
  DRY_RUN=1   mostra o que SERIA feito, sem executar nada
  SKIP_WARN=1 pula a pausa de aviso sobre fechar o browser
"""

import os
import subprocess
import sys
import shutil

DRY_RUN = os.environ.get("DRY_RUN") == "1"
SKIP_WARN = os.environ.get("SKIP_WARN") == "1"


def log(msg, level="INFO"):
    icons = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "STEP": "▶️", "ERROR": "❌"}
    print(f"{icons.get(level, '')} {msg}")


def check_env_cookies():
    """Causa nº1 de expiração recorrente, segundo a doc oficial do projeto."""
    if not os.environ.get("NOTEBOOKLM_COOKIES"):
        log("NOTEBOOKLM_COOKIES não está no ambiente (bom).", "OK")
        return True

    log("NOTEBOOKLM_COOKIES ESTÁ definida no ambiente.", "ERROR")
    print()
    print("  Essa é a causa número 1 documentada de 'sessão expirou de novo'.")
    print("  Quando essa variável existe, ela tem prioridade absoluta sobre")
    print("  todas as outras fontes de autenticação — auth.json, perfil do")
    print("  browser e o próprio `nlm login`. Quando os cookies dela vencem,")
    print("  NENHUMA re-autenticação resolve, porque o valor velho continua")
    print("  travado no processo.")
    print()
    print("  Como resolver:")
    print("   1. Procure NOTEBOOKLM_COOKIES na configuração do seu MCP")
    print("      (ex: claude_desktop_config.json ou config do Claude Code)")
    print("      e REMOVA essa entrada.")
    print("   2. Verifique também seu shell (~/.zshrc, ~/.bashrc) com:")
    print("      grep -r NOTEBOOKLM_COOKIES ~/.zshrc ~/.bashrc ~/.profile")
    print("   3. Feche e reabra o Claude Code, e rode este script de novo.")
    print()
    return False


def warn_close_browser():
    if SKIP_WARN or DRY_RUN:
        return
    print()
    log("ANTES DE CONTINUAR: feche o Chrome (ou Brave/Edge/Arc) por completo.", "WARN")
    print("  No Mac: Cmd+Q na janela do browser — não basta fechar as abas.")
    print("  Com o browser aberto, a extração de cookies fica instável e a")
    print("  sessão costuma cair logo em seguida.")
    print()
    try:
        input("  Quando o browser estiver fechado, aperte ENTER pra continuar... ")
    except EOFError:
        log("Sem terminal interativo — seguindo direto. Confirme que o "
            "browser está fechado.", "WARN")


def do_login():
    if DRY_RUN:
        log("(dry-run) 'nlm login' seria executado agora.", "INFO")
        return True
    if shutil.which("nlm") is None:
        log("Comando 'nlm' não encontrado. Rode scripts/setup_connector.py primeiro.", "ERROR")
        return False
    log("Abrindo o navegador para login. Complete o login na janela que abrir.", "STEP")
    try:
        result = subprocess.run(["nlm", "login"])
    except FileNotFoundError:
        log("Comando 'nlm' não encontrado.", "ERROR")
        return False
    if result.returncode != 0:
        log("'nlm login' terminou com erro. O login pode não ter sido concluído.", "ERROR")
        return False
    log("Login finalizado.", "OK")
    return True


def verify():
    if DRY_RUN:
        log("(dry-run) autenticação seria verificada com 'nlm login --check'.", "INFO")
        return True
    log("Verificando autenticação ('nlm login --check')...", "STEP")
    result = subprocess.run(["nlm", "login", "--check"], capture_output=True, text=True)
    ok = result.returncode == 0
    if ok:
        log("Autenticação confirmada.", "OK")
    else:
        log(f"Autenticação NÃO confirmada: {(result.stdout or result.stderr).strip()}", "ERROR")
    return ok


def main():
    log("=== Renovar autenticação — Gemini Notebook ===", "STEP")
    if DRY_RUN:
        log("MODO DRY-RUN — nada será executado de verdade.", "WARN")

    if not check_env_cookies():
        log("Setup interrompido: remova NOTEBOOKLM_COOKIES antes de continuar. "
            "Sem isso, re-autenticar não vai adiantar.", "ERROR")
        sys.exit(1)

    warn_close_browser()

    if not do_login():
        sys.exit(1)

    if not verify():
        sys.exit(1)

    print()
    log("Autenticação renovada com sucesso.", "OK")
    print()
    print("  Dica pra não ser interrompido durante gravações ou tarefas longas:")
    print("  quando o Claude Code pedir aprovação pra re-autenticar, escolha")
    print("  'Sempre permitir' em vez de 'Permitir uma vez' — assim ele resolve")
    print("  sozinho sem travar o fluxo.")
    print()
    print("  Antes de tarefas longas (áudio/podcast leva de 3 a 15 min), rode")
    print("  'nlm login --check' primeiro — é nessa janela que a sessão costuma cair.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Diagnóstico da conexão Claude Code <-> Gemini Notebook.
Usa o diagnóstico OFICIAL do projeto (`nlm doctor`) como fonte principal,
e complementa com as checagens das causas conhecidas de sessão expirando
com frequência.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path


def check(label, ok, detail=""):
    icon = "✅" if ok else "❌"
    print(f"{icon} {label}" + (f" — {detail}" if detail else ""))
    return ok


def check_env_cookies():
    """Causa nº1 documentada de 'sessão expirou de novo'."""
    present = bool(os.environ.get("NOTEBOOKLM_COOKIES"))
    check("NOTEBOOKLM_COOKIES ausente do ambiente", not present,
          "DEFINIDA — essa é a causa nº1 de expiração recorrente" if present else "")
    if present:
        print("   → Enquanto essa variável existir, ela sobrepõe auth.json, perfil")
        print("     do browser e o próprio 'nlm login'. Re-autenticar NÃO resolve.")
        print("     Remova-a da config do MCP e do shell, reinicie o Claude Code.")
    return not present


def scan_configs_for_cookies():
    """Procura NOTEBOOKLM_COOKIES gravado nos arquivos de config do MCP."""
    candidates = [
        Path.home() / "Library/Application Support/Claude/claude_desktop_config.json",
        Path.home() / ".config/Claude/claude_desktop_config.json",
        Path.home() / ".claude.json",
        Path.home() / ".claude/settings.json",
    ]
    found_in = []
    for p in candidates:
        try:
            if p.exists() and "NOTEBOOKLM_COOKIES" in p.read_text():
                found_in.append(str(p))
        except Exception:
            pass
    check("Nenhuma config do MCP com NOTEBOOKLM_COOKIES embutido", not found_in,
          f"encontrado em: {', '.join(found_in)}" if found_in else "")
    if found_in:
        print("   → Abra esse(s) arquivo(s) e remova a entrada NOTEBOOKLM_COOKIES.")
    return not found_in


def main():
    print("=== Diagnóstico: Claude Code <-> Gemini Notebook ===\n")

    print("--- Instalação ---")
    check("uv instalado", shutil.which("uv") is not None)
    check("notebooklm-mcp-cli instalado (comando nlm encontrado)", shutil.which("nlm") is not None)
    check("Claude Code disponível (comando claude encontrado)", shutil.which("claude") is not None)

    print("\n--- Causas conhecidas de sessão expirando ---")
    check_env_cookies()
    scan_configs_for_cookies()

    print("\n--- Autenticação atual ---")
    if shutil.which("nlm") is None:
        print("❌ Não dá pra checar — comando 'nlm' não encontrado. "
              "Rode scripts/setup_connector.py primeiro.")
        return
    try:
        result = subprocess.run(["nlm", "login", "--check"], capture_output=True,
                                text=True, timeout=30)
        check("Sessão autenticada agora", result.returncode == 0,
              (result.stdout or result.stderr).strip()[:200])
    except Exception as e:
        check("Sessão autenticada agora", False, str(e))

    print("\n--- Diagnóstico oficial do projeto (nlm doctor) ---")
    try:
        result = subprocess.run(["nlm", "doctor"], capture_output=True, text=True, timeout=60)
        print(result.stdout or result.stderr)
    except Exception as e:
        print(f"❌ Erro ao rodar 'nlm doctor': {e}")

    print("\nDependendo do que estiver ❌ acima:")
    print("  - NOTEBOOKLM_COOKIES definida: remova da config/shell — re-autenticar não resolve.")
    print("  - Sessão expirada: rode scripts/refresh_auth.py (feche o browser antes).")
    print("  - Problema de CONFIGURAÇÃO DO MCP: rode scripts/setup_connector.py de novo.")
    print("  - Começou depois de uma atualização do Google: pode ser preciso aguardar")
    print("    uma atualização do próprio notebooklm-mcp-cli.")


if __name__ == "__main__":
    main()

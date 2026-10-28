---
name: gemini-notebook-connector
description: Conecta o Claude Code ao Gemini Notebook (antigo Google NotebookLM) via MCP, usando os comandos oficiais do projeto notebooklm-mcp-cli. Use sempre que o usuário pedir para "conectar Claude ao NotebookLM", "conectar Claude ao Gemini Notebook", "integrar Claude com Google Notebook", ou perguntar por que a conexão parou de funcionar, erros de autenticação com o Google, ou sobre o pacote notebooklm-mcp-cli / notebooklm-mcp-server. Esta skill cuida SÓ da conexão — não executa ações de uso (listar notebooks, gerar slide/podcast/flashcard); essas ações o usuário pede diretamente depois que a conexão estiver pronta.
---

# Gemini Notebook Connector (Claude Code)

Finalidade única desta skill: **deixar o Claude Code conectado ao Gemini Notebook**,
via `notebooklm-mcp-cli` — um projeto aberto de terceiro, não uma integração
oficial da Anthropic nem do Google.

Esta skill **não** lista notebooks, não consulta conteúdo, não gera slide, podcast
ou flashcard. Isso é feito pelo usuário depois, em linguagem natural, conversando
normalmente com o Claude Code — não é parte do script de setup.

## Escopo: só Claude Code

Não configura o Claude Desktop. Se o usuário quiser usar no Desktop, oriente a
baixar a extensão oficial `.mcpb` do projeto `notebooklm-mcp-cli` (nos releases do
GitHub) e instalar com duplo-clique.

## Antes de tudo: explique isso ao usuário

- É uma ponte **não-oficial** (projeto de comunidade), não um recurso lançado em
  conjunto por Google e Anthropic.
- O login (`nlm login`, executado pelo próprio setup) usa **cookies da sessão do
  Google**, não OAuth com escopo delimitado. Recomende conta secundária para
  testes e evitar documentos confidenciais numa primeira configuração.
- Se o Google alterar algo por trás do Gemini Notebook, a conexão pode parar de
  funcionar — rodar o setup de novo **não garante** o conserto; pode ser preciso
  aguardar atualização do próprio `notebooklm-mcp-cli`.
- No **Windows**, o Claude Code normalmente depende de WSL ou Git Bash — esse
  fluxo não foi validado nesse cenário.

## Como rodar

1. Diagnóstico inicial (opcional, mas recomendado):
   ```
   python3 scripts/check_connection.py
   ```

2. Setup:
   ```
   python3 scripts/setup_connector.py
   ```
   Ordem de execução do script, sem pular etapas:
   1. Verifica se o **Claude Code está instalado** — se não estiver, para aqui,
      sem tentar instalar nada.
   2. Verifica quais dependências faltam (`uv`, `notebooklm-mcp-cli`). Se faltar
      algo, **só instala com autorização explícita**: rode de novo com
      `AUTHORIZE_INSTALL=1` depois de confirmar com o usuário.
   3. Detecta pacotes legados conflitantes (`notebooklm-mcp-server`,
      `notebooklm-cli`) — se encontrar, **para** e só remove com
      `CONFIRM_CLEAN=1`.
   4. Configura o MCP no Claude Code via `nlm setup add claude-code`.
   5. **Executa o login de verdade** (`nlm login`) — abre o navegador e
      **espera o usuário concluir o login manualmente**. Isso precisa de
      interação humana; o Claude não pode logar por você.
   6. Depois do login, verifica a autenticação (`nlm login --check`).
   7. Só então roda o diagnóstico final (`nlm doctor`).
   8. Só informa **"CONEXÃO PRONTA"** se MCP + autenticação + diagnóstico
      estiverem todos OK. Caso contrário, mostra exatamente qual das três
      etapas falhou — não dê a conexão como certa se o script terminou com erro.

Para ver o que **seria feito**, sem executar nada de verdade (nem abrir
navegador, nem tentar login real):
```
DRY_RUN=1 python3 scripts/setup_connector.py
```

## ⚠️ Sobre instalar esta própria skill via `.skill`

Peça ao usuário pra confirmar, testando ao vivo, que o comando de instalação
("instale a skill gemini-notebook-connector.skill que está na minha pasta de
downloads") realmente funciona no ambiente dele **antes** de qualquer
demonstração ao vivo — esse comportamento não deve ser dado como garantido
sem esse teste.

## Depois de conectado

A partir daqui, a skill encerrou seu papel. O usuário pode pedir diretamente ao
Claude Code, em linguagem natural, coisas como "liste meus notebooks", "gere um
podcast sobre X", "crie um notebook com esse PDF" — essas ações usam as
ferramentas MCP já registradas, sem precisar rodar nenhum script desta skill de
novo.

## Sessão expirando com frequência (leia antes de re-autenticar)

Se o usuário reclamar que a sessão cai o tempo todo — "sessão expirou de novo",
re-autenticação em loop, interrupção no meio de uma geração — **não fique só
rodando `nlm login` de novo**. Existem causas conhecidas, em ordem de
probabilidade:

**1. `NOTEBOOKLM_COOKIES` definida como variável de ambiente.** Essa é a causa
número 1 documentada. Quando essa variável existe (na config do MCP ou no
shell), ela tem **prioridade absoluta** sobre `auth.json`, perfil de browser e
o próprio `nlm login`. Quando aqueles cookies vencem, **nenhuma
re-autenticação resolve**, porque o valor velho fica travado no processo.
Rode `scripts/check_connection.py` — ele detecta isso automaticamente, tanto no
ambiente quanto nos arquivos de config. Se aparecer, oriente o usuário a
remover a entrada e reiniciar o Claude Code.

**2. Browser aberto durante o `nlm login`.** A autenticação extrai cookies de
uma sessão do Chrome (ou Brave/Edge/Arc). Se o browser estiver aberto na hora
do login, a extração fica instável e a sessão cai logo depois. O browser precisa
estar **totalmente fechado** (Cmd+Q no Mac, não só fechar as abas).
`scripts/refresh_auth.py` avisa sobre isso antes de rodar o login.

**3. Operação longa consumindo a sessão no meio.** Geração de áudio/podcast é
assíncrona e leva de 3 a 15 minutos — é exatamente a janela onde a sessão
costuma vencer. **Regra: antes de disparar qualquer geração longa, rode
`nlm login --check` primeiro.** Se a sessão estiver perto de vencer, renove
antes de começar, não no meio.

### Renovar a autenticação
```
python3 scripts/refresh_auth.py
```
Esse script checa a causa nº1 antes de qualquer coisa (e para, se encontrar),
avisa pra fechar o browser, roda o login e confirma o resultado.

### Dica para gravações e tarefas longas
Quando o Claude Code pedir aprovação para re-autenticar, o usuário pode escolher
**"Sempre permitir"** em vez de "Permitir uma vez" — assim a renovação acontece
sozinha, sem travar o fluxo com um popup de aprovação a cada vez. Vale sugerir
isso quando o usuário estiver gravando tela ou rodando algo demorado.

## Troubleshooting

- **Claude Code não encontrado**: instale o Claude Code primeiro — esta skill
  não faz isso por você.
- **"uv instalado mas comando não encontrado"**: feche e abra um terminal/sessão
  novo do Claude Code e rode `scripts/setup_connector.py` de novo.
- **Autenticação falhou na verificação**: rode `scripts/refresh_auth.py` — não
  só `nlm login`, porque o script checa antes as causas que fazem a
  re-autenticação não colar.
- **Sessão expirando repetidamente / desconectando o tempo todo**: veja a seção
  "Sessão expirando com frequência" acima. Quase sempre é `NOTEBOOKLM_COOKIES`
  na config ou browser aberto durante o login — nesses casos, re-autenticar em
  loop não resolve.
- **Depois de uma atualização do Google, a conexão parou**: pode ser necessário
  aguardar o mantenedor do projeto atualizar — rodar de novo não garante conserto.
- **Pacotes legados detectados**: o setup para de propósito. Confirme com o
  usuário e rode de novo com `CONFIRM_CLEAN=1`.
- **Quer usar no Claude Desktop também**: baixe a extensão `.mcpb` oficial do
  projeto — não editar config manualmente.

## Segurança e limites

- **Não é OAuth com escopo delimitado.** O `nlm login` extrai cookies da sessão
  Google autenticada no navegador. Trate como credencial sensível; recomende
  conta secundária para testes.
- **Este pacote (SKILL.md + scripts) nunca grava cookies, tokens, credenciais,
  logs ou arquivos temporários dentro de si mesmo.** A autenticação é gerenciada
  inteiramente pelo `notebooklm-mcp-cli`, fora desta pasta. O `.skill`
  distribuído contém só o `SKILL.md` e os dois scripts Python.
- É uma ferramenta de terceiro, sem SLA ou garantia de manutenção.

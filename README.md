# Gerenciador de Compras (CLI)

Sistema em Python para controle de compras, categorias, orçamento e contas de usuários, com suporte a múltiplos perfis (`user`, `admin`, `superadmin`).

## Objetivo
Organizar compras e gastos mensais por conta de usuário, mantendo os dados separados entre contas.

## Funcionalidades
- Cadastro e login de usuários.
- Múltiplas contas com dados isolados.
- Adição, edição e exclusão de compras.
- Categorias fixas e categorias personalizadas.
- Busca avançada com filtros.
- Controle de orçamento mensal.
- Alertas de vencimento.
- Geração de relatório em PDF.
- Backup automático de dados.
- Painel administrativo.
- Ferramentas de super admin.
- Restauração de fábrica com validações de segurança.

## Perfis e Permissões
### `user`
- Pode usar funções normais da própria conta.
- Não acessa painel admin nem ferramentas super admin.

### `admin`
- Pode abrir o painel admin.
- Não pode usar restauração de fábrica nem ferramentas exclusivas de super admin.

### `superadmin`
- Pode tudo que `admin` faz.
- Pode usar restauração de fábrica.
- Pode usar ferramentas avançadas de super admin.

## Nomes das Contas Administrativas
- **Admin principal:** `admin`
- **Super admin:** `Bernardo`

Observação: por segurança, este README **não mostra senhas**.

## Requisitos
- Python 3.10+
- Biblioteca `reportlab` (para geração de PDF)

## Instalação
No terminal (PowerShell):

```powershell
cd d:\python\pythonprojects
python -m pip install reportlab
```

## Como Executar
```powershell
cd d:\python\pythonprojects
python gerenciador_copia.py
```

## Primeiro Uso
Ao iniciar, o sistema pergunta:
- `Ja tem conta? (sim/nao)`

### Se responder `nao`
- Cria novo usuário e senha.
- Conta é criada com papel `user`.

### Se responder `sim`
- Informa usuário e senha para entrar.

## Estrutura de Dados
Arquivo principal: `dados.json`

Estrutura resumida:
- `users`
  - `<nome_usuario>`
    - `pin_hash` (senha com hash)
    - `role` (`user`, `admin`, `superadmin`)
    - `data`
      - `nomes`, `cats`, `valores`, `parcelas`, `datas`, `vencimentos`
      - `orcamento_mensal`
      - `categorias`

## Pastas Criadas Automaticamente
- `backups/` -> cópias de segurança do `dados.json`.
- `relatorios/` -> PDFs gerados.

## Menu de Opções
### Funções gerais
1. Adicionar
2. Mostrar
3. Total geral
4. Total por categoria
5. Nova categoria
6. Deletar compra
7. Deletar categoria
8. Total em parcelas
9. Filtrar por categoria
10. Busca avançada
11. Editar compra
12. Definir orçamento
13. Ver orçamento
14. Gerar PDF
15. Ver vencimentos
16. Sobre
17. Ajuda
18. Sair
19. Alterar senha da conta
20. Trocar conta

### Funções administrativas
21. Painel admin (`admin` e `superadmin`)
22. Restauração de fábrica (somente `superadmin`)
23. Ferramentas super admin (somente `superadmin`)
24. Desfazer última exclusão

## Busca Avançada (Opção 10)
Permite filtrar compras por:
- Nome (contém)
- Categoria
- Valor mínimo/máximo
- Data inicial/final

## Painel Admin (Opção 21)
Mostra:
- Total de usuários
- Quantidade de compras por usuário
- Total gasto por usuário

## Ferramentas Super Admin (Opção 23)
- Listar usuários e papéis
- Alterar papel de usuário (`user`/`admin`)
- Resetar senha de usuário
- Resetar dados de usuário
- Excluir usuário (com proteções)

## Restauração de Fábrica (Opção 22)
Disponível somente para super admin e com múltiplas validações.

Modos:
- Restaurar apenas conta atual
- Restaurar sistema inteiro (todos os usuários)

Antes de apagar, o sistema cria backup automaticamente.

## Desfazer Última Exclusão (Opção 24)
- Restaura a última compra excluída.
- Também restaura a última categoria excluída com as compras que foram removidas junto.
- Funciona para a conta atualmente logada.

## Roteiro de Apresentação (2-3 minutos)
1. Login em uma conta comum e mostrar o dashboard inicial.
2. Adicionar 2 compras em categorias diferentes.
3. Mostrar total geral e filtro por categoria.
4. Executar busca avançada com um filtro de valor.
5. Excluir uma compra e usar `24` para desfazer.
6. Entrar como `admin` e abrir painel admin (opção 21).
7. Entrar como `superadmin` e mostrar que existem funções exclusivas (opções 22 e 23), sem executar restauração real.

## Segurança
- Senhas não são salvas em texto puro (`pin_hash`).
- Dados são separados por usuário.
- Validações de confirmação para ações críticas.

## Boas Práticas
- Faça backup manual periódico de `dados.json` e pasta `backups/`.
- Não compartilhe credenciais de contas administrativas.
- Evite editar `dados.json` manualmente sem necessidade.

## Solução de Problemas
### 1) Erro ao gerar PDF
Instale dependência:
```powershell
python -m pip install reportlab
```

### 2) Caracteres estranhos no terminal
No Windows, use PowerShell com UTF-8 e mantenha o script como UTF-8.

### 3) Não consigo acessar recursos administrativos
Verifique se está logado em conta com papel adequado:
- `admin` para painel admin
- `superadmin` para restauração/ferramentas avançadas

## Arquivos principais do projeto
- `gerenciador_copia.py` -> aplicação principal
- `dados.json` -> base de dados local
- `README.md` -> documentação de uso

---
Projeto CLI em Python para organização de gastos mensais com múltiplos usuários.

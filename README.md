Gerenciador de Compras
Descrição

O Gerenciador de Compras é um aplicativo desenvolvido em Python para registrar, organizar e analisar compras e gastos pessoais.

O sistema permite gerenciar produtos, categorias, parcelas, vencimentos e orçamentos mensais, além de oferecer recursos avançados como:

múltiplos usuários

níveis de permissão (user, admin e superadmin)

alertas de vencimento

envio de e-mail

geração de relatórios

exportação para Excel e PDF

backups automáticos

Autor: Bernardo Alves Caetano

Funcionalidades
Gestão de compras

adicionar compras

editar compras

excluir compras

desfazer última exclusão

categorizar produtos

parcelamento de compras

controle de datas e vencimentos

Sistema de usuários

criação de contas

login com senha segura

múltiplos usuários

troca de conta

alteração de senha

Níveis de acesso

User → acesso normal

Admin → painel administrativo

Super Admin → controle total do sistema

Controle financeiro

total geral de gastos

total por categoria

total de compras parceladas

orçamento mensal

aviso quando orçamento está perto do limite

Alertas

alerta de produtos vencidos

alerta de produtos próximos de vencer

envio automático de e-mail

Relatórios

geração de PDF

exportação de planilha Excel

limpeza automática de relatórios antigos

Segurança

senhas com hash SHA-256

PIN com salt

limite de tentativas de login

bloqueio temporário após erros

autenticação especial para super admin

Administração do sistema

painel de usuários

alteração de permissões

reset de senha

reset de dados de usuário

exclusão de contas

restauração de fábrica do sistema

Tecnologias usadas

Python

JSON para armazenamento de dados

OpenPyXL para exportação de planilhas

ReportLab para geração de relatórios

PyInstaller para gerar executável .exe

Estrutura de arquivos
gerenciador/
│
├── gerenciador.py
├── dados.json
│
├── backups/
│   └── backups automáticos dos dados
│
├── relatorios/
│   └── relatórios PDF gerados
│
└── planilha_gastos.xlsx
Instalação
Requisitos

Python 3.10 ou superior.

Instalar dependências:

pip install openpyxl
pip install reportlab
Executar o programa

No terminal:

python gerenciador.py
Gerar executável (.exe)

Para transformar o programa em aplicativo Windows:

pip install pyinstaller

Depois:

pyinstaller --onefile gerenciador.py

O executável será criado na pasta:

dist/
Sistema de dados

O programa salva todas as informações no arquivo:

dados.json

Esse arquivo contém:

usuários

compras

categorias

orçamento

configurações

Backups automáticos são salvos na pasta:

backups/
Recursos automáticos

O programa possui vários sistemas automáticos:

backup automático dos dados

limpeza de compras antigas

limpeza de relatórios antigos

alerta de vencimentos

envio de email automático

dashboard inicial de estatísticas

Autor

Bernardo Alves Caetano

Projeto desenvolvido em Python para organização de compras e gastos.

Criado em 2026.

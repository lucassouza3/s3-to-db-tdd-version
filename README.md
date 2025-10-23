MITRA NIST - Visao Geral
========================

Projeto de ingestao de arquivos NIST em ambiente MinIO (S3) com persistencia em PostgreSQL. A arquitetura segue ports and adapters, separando regras de negocio (use cases) dos adaptadores de infraestrutura.

Requisitos
----------
- Python 3.13.x
- Acesso a um bucket MinIO/S3 e banco PostgreSQL (opcional para testes locais)

Preparacao Rapida
-----------------
1. Criar e ativar o ambiente virtual:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
2. Atualizar pip e instalar dependencias basicas:
   ```powershell
   pip install -U pip
   pip install -U pytest minio psycopg
   ```
3. Duplicar `.env.example` para `.env` e ajustar credenciais de S3/PostgreSQL.

Executar Testes
---------------
```powershell
.\.venv\Scripts\python.exe -m pytest
```

Principais Arquivos
-------------------
- `project/config.py` - carrega variaveis do `.env`.
- `project/logging_config.py` - define configuracao de logging.
- `project/application/ports/s3_port.py` - contrato de acesso ao S3.
- `project/application/ports/repository_port.py` - contrato de persistencia/logs.
- `project/application/services/nist_parser_service.py` - parsing de arquivos NIST.
- `project/application/services/checksum_service.py` - calculo de hash MD5.
- `project/application/usecases/upload_nist_usecase.py` - upload de arquivos locais.
- `project/application/usecases/move_processed_usecase.py` - movimenta objetos processados.
- `project/application/usecases/process_nist_usecase.py` - orquestra o processamento e persistencia.
- `project/infra/s3/miniosdk.py` - fabrica de cliente MinIO.
- `project/infra/s3/s3_manager.py` - adaptador S3 (MinioS3Adapter) e utilitarios de parsing.
- `project/infra/db/orm_db.py` - gerencia conexoes PostgreSQL.
- `project/infra/db/person_repository.py` - implementacao concreta do RepositoryPort.
- `project/infra/sanitizers.py` - funcoes de normalizacao (texto, datas, sexo).
- `project/cli/nist_manager.py` - CLI oficial com comandos de upload/processamento.
- `docs/TUTORIAL.md` - guia detalhado da arquitetura, configuracao e exemplos.
- `tests/unit/` - testes unitarios cobrindo servicos, use cases e adaptadores.

Uso da CLI
----------
```powershell
# Ajuda geral
python -m project.cli.nist_manager --help

# Upload de um arquivo .nst
python -m project.cli.nist_manager upload caminho\para\arquivo.nst

# Upload em lote (diretorio)
python -m project.cli.nist_manager upload-batch nists --recursive

# Processamento e persistencia
python -m project.cli.nist_manager process

# Remover objetos (por chave, prefixo ou todos)
python -m project.cli.nist_manager delete --key nist/BR/TSE/arquivo.nst
python -m project.cli.nist_manager delete --prefix nist/BR/TSE/
python -m project.cli.nist_manager delete --all

# Checar conexoes com MinIO e PostgreSQL
python -m project.cli.nist_manager check-connections
```

Configuracao
------------
Exemplo de `.env`:
```
S3_ENDPOINT=http://127.0.0.1:9000
S3_BUCKET=teste
S3_ACCESS=minio
S3_SECRET=minio123
S3_SECURE=false

DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=mitra
DB_USER=postgres
DB_PASSWORD=postgres

LOG_LEVEL=INFO
```

Documentacao Adicional
----------------------
Consulte `docs/TUTORIAL.md` para uma descricao completa da arquitetura, fluxo de dados e exemplos passo a passo (upload, processamento e operacoes via API/arquivo).

Context7 MCP
------------
- O arquivo `.cursor/mcp.json` ativa o servidor MCP do Context7 via `npx -y @upstash/context7-mcp` quando o projeto é aberto em clientes compatíveis (Cursor, Claude Code, VS Code MCP, etc.).
- Caso possua chave da plataforma, defina a variável de ambiente `CONTEXT7_API_KEY` antes de iniciar o cliente para liberar cota adicional; sem a chave o serviço funciona com limite reduzido.
- É possível validar o servidor localmente com `npx -y @modelcontextprotocol/inspector npx @upstash/context7-mcp`.
- Para consulta rápida de opções, execute `npx -y @upstash/context7-mcp --help`.

Proximos Passos Sugeridos
-------------------------
- Ajustar os adaptadores para lidar com ambientes de producao (timeouts, retries, observabilidade).
- Adicionar testes de integracao utilizando instancias locais de MinIO e PostgreSQL.
- Expandir o parser NIST para extrair campos adicionais conforme a necessidade do PRD.
- Configurar pipeline de CI com `pytest` e cobertura.

﻿# Tutorial do Projeto MITRA NIST

## VisÃ£o Geral
Este tutorial apresenta a arquitetura do MITRA NIST, descrevendo as responsabilidades de cada componente e detalhando os fluxos principais da aplicaÃ§Ã£o: upload de arquivos `.nst` para o S3/MinIO e consumo desses arquivos para persistÃªncia no banco PostgreSQL.

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚          UsuÃ¡rios           â”‚
â”‚  (CLI / scripts / jobs)     â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
              â”‚
              v
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚        Camada de App        â”‚
â”‚  (Use cases + Services)     â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
              â”‚
              v
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚       Portas (Ports)        â”‚
â”‚   Interfaces de contrato    â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
              â”‚
              v
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚     Adaptadores de Infra     â”‚
â”‚  (S3/MinIO, PostgreSQL etc) â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
              â”‚
              v
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚   ServiÃ§os Externos Reais    â”‚
â”‚ (MinIO, Banco, Sistema de    â”‚
â”‚  Arquivos, HTTP APIs, etc.) â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

### Onde configurar S3 e Banco?
- `./.env`: arquivo central para apontar o endpoint do S3/MinIO (`S3_ENDPOINT`, `S3_BUCKET`, `S3_SECURE`) e as configurações do banco (`DB_HOST`, `DB_PORT`, `DB_NAME`). Credenciais sensíveis (`S3_ACCESS`, `S3_SECRET`, `DB_USER`, `DB_PASSWORD`) são solicitadas interativamente sempre que a CLI é executada; defina-as apenas se precisar de execução automatizada (CI/CD). Também define o `LOG_LEVEL`.
- `project/config.py`: converte valores do `.env` em um objeto `Config`. Qualquer ajuste de variÃ¡veis ou valores padrÃ£o deve ser feito aqui.
- `project/infra/s3/miniosdk.py`: usa `Config` para construir o cliente MinIO com timeouts e parÃ¢metros de seguranÃ§a.
- `project/infra/db/orm_db.py`: utiliza `Config` para abrir conexÃµes PostgreSQL com `psycopg`.

## Estrutura de Pastas e Arquitetura

```
project/
â”œâ”€â”€ application/
â”‚   â”œâ”€â”€ ports/
â”‚   â”œâ”€â”€ services/
â”‚   â””â”€â”€ usecases/
â”œâ”€â”€ infra/
â”‚   â”œâ”€â”€ db/
â”‚   â””â”€â”€ s3/
â”œâ”€â”€ cli/
â”œâ”€â”€ config.py
â”œâ”€â”€ logging_config.py
â””â”€â”€ __init__.py
tests/
â”œâ”€â”€ unit/
â””â”€â”€ conftest.py
```

### Camada de ConfiguraÃ§Ã£o e Utilidades
- `project/config.py`: LÃª o `.env`, encapsula em `Config`, converte tipos e dÃ¡ suporte a mÃºltiplos nomes de variÃ¡veis. `_load_env_file` injeta valores no ambiente.
- `project/logging_config.py`: Configura logging global (nÃ­vel via `.env`).
- `project/__init__.py`: Marca o pacote principal.
- `nistuploader.py`: Script auxiliar legado; referencia operaÃ§Ãµes diretas de upload (a CLI oficial estÃ¡ em `project/cli`).

### Camada de AplicaÃ§Ã£o (`project/application`)
#### Ports (`project/application/ports`)
- `s3_port.py`: Define o contrato S3 (`list_nists`, `read_bytes`, `move_processed`, `upload_bytes`, `object_exists`, `delete_object`, `delete_prefix`).
- `repository_port.py`: Contrato para persistÃªncia/log (`upsert_person_from_nist`, `log`).

#### Services (`project/application/services`)
- `checksum_service.py`: ServiÃ§o para cÃ¡lculo de hash MD5 (`ChecksumService.md5_bytes`).
- `nist_parser_service.py`: Parser heurÃ­stico de NIST. ExpÃµe:
  - Entidades `Person` e `OriginBase`.
  - `parse`: extrai dados (principalmente origem 1:008) e sanitiza texto.
  - `compose_key_for_upload`: gera chave `nist/<origem>/<arquivo>`.
  - `destination_key_for_processed`: chave `nist-lidos/<origem>/<arquivo>`.

#### Use Cases (`project/application/usecases`)
- `upload_nist_usecase.py`: LÃª arquivo local, gera chave via parser e envia bytes para S3.
- `move_processed_usecase.py`: Calcula chave de destino e move objeto processado.
- `delete_nist_usecase.py`: Remove objetos individuais, por prefixo ou todo o bucket.
- `process_nist_usecase.py`: Fluxo principal:
  1. Lista chaves `nist/`.
  2. Baixa bytes, calcula MD5 e parseia dados.
  3. Anexa `s3_key` ao objeto de origem.
  4. Persiste via `repository.upsert_person_from_nist`.
  5. Move arquivo para `nist-lidos/`.
  6. Registra logs de sucesso e falha por item.

### Camada de Infraestrutura (`project/infra`)
#### S3 (`project/infra/s3`)
- `s3_manager.py`:
  - `_field_1_008`: extrai o campo 1:008 aceitando variaÃ§Ãµes (1:008, 1.08, 1.0008 etc.).
  - `MinioS3Adapter`: implementa??o de `S3Port` usando `minio.Minio`, cobrindo listagem, leitura, upload, movimenta??o e remo??o (chave/prefixo).
- `miniosdk.py`: `MinioFactory` monta cliente MinIO configurado.

#### Banco de Dados (`project/infra/db`)
- `orm_db.py`: `PgManager` centraliza conexÃµes PostgreSQL e oferece `test_connection`.
- `person_repository.py`: `PgPersonRepository` implementa `RepositoryPort`.
  - `_ensure_schema`: cria schema `findface` e tabelas (`tb_nist_ingest`, `tb_log`) com colunas essenciais.
  - `upsert_person_from_nist`: `INSERT ... ON CONFLICT` por `md5_hash`.
  - `log`: Persiste logs em `findface.tb_log`.

#### SanitizaÃ§Ã£o (`project/infra`)
- `sanitizers.py`: FunÃ§Ãµes utilitÃ¡rias:
  - `sanitize_text`: remove acentos, normaliza espaÃ§os e uppercase.
  - `parse_date`: interpreta datas em mÃºltiplos formatos.
  - `normalize_sex`: converte cÃ³digos de sexo em `M`, `F` ou `U`.

### Camada de Interface (`project/cli`)
- `nist_manager.py`: CLI principal com subcomandos:
  - `process` â€” processa NISTs pendentes.
  - `upload` â€” upload de arquivo local.
  - `upload-batch` â€” upload mÃºltiplo (arquivos/diretÃ³rios).
  - `upload-url` â€” baixa e envia `.nst` por URL.
  - `upload-url-index` â€” consome Ã­ndice JSON/TXT de URLs.
  - `sample` â€” coleta amostras do S3.
  - `sample-local` â€” processa `./nists`.
  - `db-sample` â€” consulta tabelas do schema `findface`.
  - `check-connections` â€” valida MinIO e PostgreSQL.
- Instancia adaptadores reais (`MinioS3Adapter`, `PgPersonRepository`) e serviÃ§os (`NistParserService`, `ChecksumService`, `ProcessNistUseCase`).

### Testes (`tests/`)
- `tests/unit/test_*.py`: Cobrem sanitizaÃ§Ã£o, serviÃ§os, use cases e adaptadores.
- `tests/conftest.py`: ConfiguraÃ§Ãµes comuns.

## Como o CÃ³digo Funciona

1. **Configuração**: `load_config` lê `.env`, solicita interativamente as credenciais sensíveis (senhas aparecem mascaradas) e devolve um objeto `Config` consumido pela CLI e pelos serviços.
2. **Ports e Use Cases**: Regras de negÃ³cio dependem apenas das interfaces (`S3Port`, `RepositoryPort`), permitindo trocar adaptadores.
3. **Upload**:
   - `UploadNistUseCase` recebe caminho local.
   - Parser compÃµe a chave `nist/<origem>/<arquivo>`.
   - Caso de uso envia bytes ao S3.
4. **Processamento/PersistÃªncia**:
   - `ProcessNistUseCase` itera chaves `nist/`.
   - `read_bytes` â†’ `md5` â†’ `parse`.
   - Anexa `s3_key`, chama `upsert_person_from_nist`.
   - Move objeto para `nist-lidos/` e loga sucesso.
   - Em exceÃ§Ãµes, loga erro e continua (resiliÃªncia).
5. **Infraestrutura**:
   - `MinioS3Adapter` conecta use cases ao MinIO.
   - `PgPersonRepository` cuida da persistÃªncia e logs.
6. **CLI**: Oferece comandos scriptÃ¡veis; ideal para cron/pipelines.

## Fluxo Arquitetural (High-Level)

1. UsuÃ¡rio interage via CLI/automation.
2. `nist_manager.py` carrega `Config` e instÃ¢ncias concretas.
3. Use case apropriado (upload/process) Ã© executado.
4. InteraÃ§Ãµes com MinIO e PostgreSQL ocorrem via adaptadores.
5. Logs e persistÃªncia garantem rastreabilidade e consistÃªncia.

## Exemplos PrÃ¡ticos

### PreparaÃ§Ã£o
```powershell
# Ativar virtualenv (Windows)
.\.venv\Scripts\Activate.ps1

# Definir variÃ¡veis de ambiente (opcional se jÃ¡ ajustadas no .env)
$env:S3_ENDPOINT="http://127.0.0.1:9000"
$env:S3_BUCKET="teste"
```

### 1. Upload de NISTs

**Sistema de Arquivos**
```powershell
# Arquivo Ãºnico
python -m project.cli.nist_manager upload "nists\TSE\116908146.nst"

# DiretÃ³rio (recursivo)
python -m project.cli.nist_manager upload-batch nists --recursive
```

**URLs HTTP**
```powershell
# URL direta
python -m project.cli.nist_manager upload-url https://servidor/arq.nst

# Ãndice JSON/TXT
python -m project.cli.nist_manager upload-url-index https://servidor/indice.json --format json
python -m project.cli.nist_manager upload-url-index https://servidor/lista.txt --format txt
```

**Script Python**
```python
from project.application.services.nist_parser_service import NistParserService
from project.application.usecases.upload_nist_usecase import UploadNistUseCase
from project.config import load_config
from project.infra.s3.miniosdk import MinioFactory
from project.infra.s3.s3_manager import MinioS3Adapter

cfg = load_config()
client = MinioFactory(cfg).build()
s3 = MinioS3Adapter(client=client, bucket=cfg.s3_bucket)
parser = NistParserService()

usecase = UploadNistUseCase(s3=s3, nist_tools=parser)
key = usecase.execute("nists/TSE/116908146.nst")
print("Upload concluÃ­do:", key)
```

### 2. Processamento e PersistÃªncia

**Via CLI**
```powershell
# Processar pendentes
python -m project.cli.nist_manager process

# Processar NISTs locais
python -m project.cli.nist_manager sample-local --limit 5

# Amostragem diretamente do S3
python -m project.cli.nist_manager sample --limit 3
```

**Script Python**
```python
from project.application.services.checksum_service import ChecksumService
from project.application.services.nist_parser_service import NistParserService
from project.application.usecases.process_nist_usecase import ProcessNistUseCase
from project.config import load_config
from project.infra.db.person_repository import PgPersonRepository
from project.infra.s3.miniosdk import MinioFactory
from project.infra.s3.s3_manager import MinioS3Adapter

cfg = load_config()
client = MinioFactory(cfg).build()
s3 = MinioS3Adapter(client=client, bucket=cfg.s3_bucket)
repository = PgPersonRepository(cfg)
parser = NistParserService()
checksum = ChecksumService()

usecase = ProcessNistUseCase(s3=s3, repository=repository, parser=parser, checksum=checksum)
print("Processados:", usecase.execute())
```

### 3. Remo??o de Objetos

**Via CLI**
```powershell
# Remover um objeto espec??fico
python -m project.cli.nist_manager delete --key nist/BR/TSE/arquivo.nst

# Remover por prefixo
python -m project.cli.nist_manager delete --prefix nist/BR/TSE/

# Remover todos os objetos do bucket
python -m project.cli.nist_manager delete --all
```

**Uso program??tico**
```python
from project.application.usecases.delete_nist_usecase import DeleteNistUseCase
from project.config import load_config
from project.infra.s3.miniosdk import MinioFactory
from project.infra.s3.s3_manager import MinioS3Adapter

cfg = load_config()
client = MinioFactory(cfg).build()
s3 = MinioS3Adapter(client=client, bucket=cfg.s3_bucket)
usecase = DeleteNistUseCase(s3=s3)

# Remover por chave
usecase.delete_by_key("nist/BR/TSE/arquivo.nst")

# Remover por prefixo
usecase.delete_by_prefix("nist/BR/TSE/")

# Remover todo o bucket
usecase.delete_all()
```

### 4. PersistÃªncia no Banco

- `md5_hash`: calculado por `ChecksumService.md5_bytes`.
- `origin`: derivada de `_field_1_008` e sanitizada.
- `s3_key`: adicionada ao objeto `OriginBase` antes do upsert.
- `PgPersonRepository` armazena em `findface.tb_nist_ingest` e logs em `findface.tb_log`.

### 5. DiagnÃ³sticos e Testes

```powershell
# Testar conexÃµes
python -m project.cli.nist_manager check-connections

# Rodar testes
pytest
```

### 6. InterpretaÃ§Ã£o do Parser NIST

- `_field_1_008`: LÃª o campo 1:008 com tolerÃ¢ncia a variaÃ§Ãµes. Se nÃ£o encontrado, retorna `unknown`.
- `sanitize_text`: Normaliza origem (upper sem acentos).
- `destination_key_for_processed`: Reaproveita nome do arquivo, apenas trocando o prefixo.

## Boas PrÃ¡ticas e ExtensÃµes

- **SOLID**: Ports/use cases isolam regras de negÃ³cio; adaptadores mantÃªm responsabilidades separadas.
- **DDD**: Entidades (`Person`, `OriginBase`) representam conceitos de domÃ­nio.
- **DRY**: FunÃ§Ãµes auxiliares (ex.: `_extract_field`) evitam repetiÃ§Ã£o.
- **TDD**: Tests em `tests/unit` cobrem fluxos principais.
- **Code Smells**: Manter atenÃ§Ã£o ao tratamento genÃ©rico de exceÃ§Ãµes (atualmente utilitÃ¡rio para resiliÃªncia).

## PrÃ³ximos Passos

1. Expandir o parser para extrair campos adicionais (tipo 2 e outros).
2. Adicionar testes de integraÃ§Ã£o com MinIO/postgres reais (ex.: `docker-compose`).
3. Implementar monitoramento/observabilidade (mÃ©tricas, rastreamento, logs estruturados).
4. Automatizar em CI/CD (lint, pytest, cobertura).
5. Revisar `_field_1_008` conforme novos formatos de arquivos.


  - `delete` ? remove objetos (chave, prefixo ou todos).

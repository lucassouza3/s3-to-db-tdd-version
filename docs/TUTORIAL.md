# Tutorial do Projeto MITRA NIST

## Visão Geral
Este tutorial apresenta a arquitetura do MITRA NIST, descrevendo as responsabilidades de cada componente e detalhando os fluxos principais da aplicação: upload de arquivos `.nst` para o S3/MinIO e consumo desses arquivos para persistência no banco PostgreSQL.

```
┌─────────────────────────────┐
│          Usuários           │
│  (CLI / scripts / jobs)     │
└─────────────┬───────────────┘
              │
              v
┌─────────────────────────────┐
│        Camada de App        │
│  (Use cases + Services)     │
└─────────────┬───────────────┘
              │
              v
┌─────────────────────────────┐
│       Portas (Ports)        │
│   Interfaces de contrato    │
└─────────────┬───────────────┘
              │
              v
┌─────────────────────────────┐
│     Adaptadores de Infra     │
│  (S3/MinIO, PostgreSQL etc) │
└─────────────┬───────────────┘
              │
              v
┌─────────────────────────────┐
│   Serviços Externos Reais    │
│ (MinIO, Banco, Sistema de    │
│  Arquivos, HTTP APIs, etc.) │
└─────────────────────────────┘
```

### Onde configurar S3 e Banco?
- `./.env`: arquivo central para apontar o endpoint do S3/MinIO (`S3_ENDPOINT`, `S3_BUCKET`, `S3_SECURE`) e as configura��es do banco (`DB_HOST`, `DB_PORT`, `DB_NAME`). Credenciais sens�veis (`S3_ACCESS`, `S3_SECRET`, `DB_USER`, `DB_PASSWORD`) s�o solicitadas interativamente sempre que a CLI � executada; defina-as apenas se precisar de execu��o automatizada (CI/CD). Tamb�m define o `LOG_LEVEL`.
- `project/config.py`: converte valores do `.env` em um objeto `Config`. Qualquer ajuste de variáveis ou valores padrão deve ser feito aqui.
- `project/infra/s3/miniosdk.py`: usa `Config` para construir o cliente MinIO com timeouts e parâmetros de segurança.
- `project/infra/db/orm_db.py`: utiliza `Config` para abrir conexões PostgreSQL com `psycopg`.

## Estrutura de Pastas e Arquitetura

```
project/
├── application/
│   ├── ports/
│   ├── services/
│   └── usecases/
├── infra/
│   ├── db/
│   └── s3/
├── cli/
├── config.py
├── logging_config.py
└── __init__.py
tests/
├── unit/
└── conftest.py
```

### Camada de Configuração e Utilidades
- `project/config.py`: Lê o `.env`, encapsula em `Config`, converte tipos e dá suporte a múltiplos nomes de variáveis. `_load_env_file` injeta valores no ambiente.
- `project/logging_config.py`: Configura logging global (nível via `.env`).
- `project/__init__.py`: Marca o pacote principal.
- `nistuploader.py`: Script auxiliar legado; referencia operações diretas de upload (a CLI oficial está em `project/cli`).

### Camada de Aplicação (`project/application`)
#### Ports (`project/application/ports`)
- `s3_port.py`: Define o contrato S3 (`list_nists`, `read_bytes`, `move_processed`, `upload_bytes`, `object_exists`, `delete_object`, `delete_prefix`).
- `repository_port.py`: Contrato para persistência/log (`upsert_person_from_nist`, `log`).

#### Services (`project/application/services`)
- `checksum_service.py`: Serviço para cálculo de hash MD5 (`ChecksumService.md5_bytes`).
- `nist_parser_service.py`: Parser heurístico de NIST. Expõe:
  - Entidades `Person` e `OriginBase`.
  - `parse`: extrai dados (principalmente origem 1:008) e sanitiza texto.
  - `compose_key_for_upload`: gera chave `nist/<origem>/<arquivo>`.
  - `destination_key_for_processed`: chave `nist-lidos/<origem>/<arquivo>`.

#### Use Cases (`project/application/usecases`)
- `upload_nist_usecase.py`: Lê arquivo local, gera chave via parser e envia bytes para S3.
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
  - `_field_1_008`: extrai o campo 1:008 aceitando variações (1:008, 1.08, 1.0008 etc.).
  - `MinioS3Adapter`: implementa??o de `S3Port` usando `minio.Minio`, cobrindo listagem, leitura, upload, movimenta??o e remo??o (chave/prefixo).
- `miniosdk.py`: `MinioFactory` monta cliente MinIO configurado.

#### Banco de Dados (`project/infra/db`)
- `orm_db.py`: `PgManager` centraliza conexões PostgreSQL e oferece `test_connection`.
- `person_repository.py`: `PgPersonRepository` implementa `RepositoryPort`.
  - `_ensure_schema`: cria schema `findface` e tabelas (`tb_nist_ingest`, `tb_log`) com colunas essenciais.
  - `upsert_person_from_nist`: `INSERT ... ON CONFLICT` por `md5_hash`.
  - `log`: Persiste logs em `findface.tb_log`.

#### Sanitização (`project/infra`)
- `sanitizers.py`: Funções utilitárias:
  - `sanitize_text`: remove acentos, normaliza espaços e uppercase.
  - `parse_date`: interpreta datas em múltiplos formatos.
  - `normalize_sex`: converte códigos de sexo em `M`, `F` ou `U`.

### Camada de Interface (`project/cli`)
- `nist_manager.py`: CLI principal com subcomandos:
  - `process` — processa NISTs pendentes.
  - `upload` — upload de arquivo local.
  - `upload-batch` — upload múltiplo (arquivos/diretórios).
  - `upload-url` — baixa e envia `.nst` por URL.
  - `upload-url-index` — consome índice JSON/TXT de URLs.
  - `sample` — coleta amostras do S3.
  - `sample-local` — processa `./nists`.
  - `db-sample` — consulta tabelas do schema `findface`.
  - `check-connections` — valida MinIO e PostgreSQL.
- Instancia adaptadores reais (`MinioS3Adapter`, `PgPersonRepository`) e serviços (`NistParserService`, `ChecksumService`, `ProcessNistUseCase`).

### Testes (`tests/`)
- `tests/unit/test_*.py`: Cobrem sanitização, serviços, use cases e adaptadores.
- `tests/conftest.py`: Configurações comuns.

## Como o Código Funciona

1. **Configura��o**: `load_config` l� `.env`, solicita interativamente as credenciais sens�veis (senhas aparecem mascaradas) e devolve um objeto `Config` consumido pela CLI e pelos servi�os.
2. **Ports e Use Cases**: Regras de negócio dependem apenas das interfaces (`S3Port`, `RepositoryPort`), permitindo trocar adaptadores.
3. **Upload**:
   - `UploadNistUseCase` recebe caminho local.
   - Parser compõe a chave `nist/<origem>/<arquivo>`.
   - Caso de uso envia bytes ao S3.
4. **Processamento/Persistência**:
   - `ProcessNistUseCase` itera chaves `nist/`.
   - `read_bytes` → `md5` → `parse`.
   - Anexa `s3_key`, chama `upsert_person_from_nist`.
   - Move objeto para `nist-lidos/` e loga sucesso.
   - Em exceções, loga erro e continua (resiliência).
5. **Infraestrutura**:
   - `MinioS3Adapter` conecta use cases ao MinIO.
   - `PgPersonRepository` cuida da persistência e logs.
6. **CLI**: Oferece comandos scriptáveis; ideal para cron/pipelines.

## Fluxo Arquitetural (High-Level)

1. Usuário interage via CLI/automation.
2. `nist_manager.py` carrega `Config` e instâncias concretas.
3. Use case apropriado (upload/process) é executado.
4. Interações com MinIO e PostgreSQL ocorrem via adaptadores.
5. Logs e persistência garantem rastreabilidade e consistência.

## Exemplos Práticos

### Preparação
```powershell
# Ativar virtualenv (Windows)
.\.venv\Scripts\Activate.ps1

# Definir variáveis de ambiente (opcional se já ajustadas no .env)
$env:S3_ENDPOINT="http://127.0.0.1:9000"
$env:S3_BUCKET="teste"
```

### 1. Upload de NISTs

**Sistema de Arquivos**
```powershell
# Arquivo único
python -m project.cli.nist_manager upload "nists\TSE\116908146.nst"

# Diretório (recursivo)
python -m project.cli.nist_manager upload-batch nists --recursive
```

**URLs HTTP**
```powershell
# URL direta
python -m project.cli.nist_manager upload-url https://servidor/arq.nst

# Índice JSON/TXT
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
print("Upload concluído:", key)
```

### 2. Processamento e Persistência

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

### 4. Persistência no Banco

- `md5_hash`: calculado por `ChecksumService.md5_bytes`.
- `origin`: derivada de `_field_1_008` e sanitizada.
- `s3_key`: adicionada ao objeto `OriginBase` antes do upsert.
- `PgPersonRepository` armazena em `findface.tb_nist_ingest` e logs em `findface.tb_log`.

### 5. Diagnósticos e Testes

```powershell
# Testar conexões
python -m project.cli.nist_manager check-connections

# Rodar testes
pytest
```

### 6. Interpretação do Parser NIST

- `_field_1_008`: Lê o campo 1:008 com tolerância a variações. Se não encontrado, retorna `unknown`.
- `sanitize_text`: Normaliza origem (upper sem acentos).
- `destination_key_for_processed`: Reaproveita nome do arquivo, apenas trocando o prefixo.

## Boas Práticas e Extensões

- **SOLID**: Ports/use cases isolam regras de negócio; adaptadores mantêm responsabilidades separadas.
- **DDD**: Entidades (`Person`, `OriginBase`) representam conceitos de domínio.
- **DRY**: Funções auxiliares (ex.: `_extract_field`) evitam repetição.
- **TDD**: Tests em `tests/unit` cobrem fluxos principais.
- **Code Smells**: Manter atenção ao tratamento genérico de exceções (atualmente utilitário para resiliência).

## Próximos Passos

1. Expandir o parser para extrair campos adicionais (tipo 2 e outros).
2. Adicionar testes de integração com MinIO/postgres reais (ex.: `docker-compose`).
3. Implementar monitoramento/observabilidade (métricas, rastreamento, logs estruturados).
4. Automatizar em CI/CD (lint, pytest, cobertura).
5. Revisar `_field_1_008` conforme novos formatos de arquivos.


  - `delete` ? remove objetos (chave, prefixo ou todos).


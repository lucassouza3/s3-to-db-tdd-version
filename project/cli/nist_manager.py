from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
import json

from project.application.services.checksum_service import ChecksumService
from project.application.services.nist_parser_service import NistParserService
from project.application.usecases.delete_nist_usecase import DeleteNistUseCase
from project.application.usecases.process_nist_usecase import ProcessNistUseCase
from project.config import load_config
from project.logging_config import setup_logging
from project.infra.s3.miniosdk import MinioFactory
from project.infra.s3.s3_manager import MinioS3Adapter
from project.infra.db.orm_db import PgManager
from project.infra.db.person_repository import PgPersonRepository


# Adaptadores dummy (infra real deve substituir)
@dataclass
class _DummyS3:
    def list_nists(self):
        return []

    def read_bytes(self, key: str) -> bytes:
        raise NotImplementedError

    def move_processed(self, key: str, dest_key: str) -> None:
        pass

    def upload_bytes(self, key: str, raw: bytes) -> None:
        pass


@dataclass
class _DummyRepo:
    def upsert_person_from_nist(self, person, base, md5_hash: str) -> None:
        pass

    def log(self, level: str, message: str) -> None:
        print(f"[{level}] {message}")


def main(argv: list[str] | None = None) -> int:
    """Ponto de entrada da CLI MITRA NIST.

    Exemplos
    - Testar conexões: `python -m project.cli.nist_manager check-connections`
    - Upload de um arquivo: `python -m project.cli.nist_manager upload path\arquivo.nst`
    - Upload recursivo: `python -m project.cli.nist_manager upload-batch nists --recursive`
    - Sample do S3: `python -m project.cli.nist_manager sample --limit 3`
    - Sample local: `python -m project.cli.nist_manager sample-local --limit 3`
    - Upload por URL: `python -m project.cli.nist_manager upload-url https://exemplo/arquivo.nst`
    """
    parser = argparse.ArgumentParser(description="MITRA NIST Manager (CLI)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("process", help="Processa NISTs pendentes do bucket")

    upload = sub.add_parser("upload", help="Faz upload de um arquivo .nst")
    upload.add_argument("path", help="Caminho do arquivo .nst")

    sub.add_parser("check-connections", help="Testa conexões com S3 (MinIO) e PostgreSQL")

    sample = sub.add_parser("sample", help="Busca N NISTs do S3, mostra dados e persiste")
    sample.add_argument("--limit", type=int, default=3, help="Quantidade de NISTs a coletar (padrão: 3)")

    sample_local = sub.add_parser("sample-local", help="Lê NISTs da pasta local 'nists/' e persiste no DB")
    sample_local.add_argument("--limit", type=int, default=3, help="Quantidade de NISTs locais (padrão: 3)")
    sample_local.add_argument("--files", nargs="*", help="Lista de arquivos .nst específicos para processar")

    dbsample = sub.add_parser("db-sample", help="Consulta o banco e retorna amostras de tabelas do schema findface")
    dbsample.add_argument("--limit", type=int, default=5, help="Quantidade de linhas por tabela (padrão: 5)")
    dbsample.add_argument("--tables", nargs="*", help="Lista de tabelas para amostrar (ex.: tb_nist_ingest tb_nist tb_log)")

    upbatch = sub.add_parser("upload-batch", help="Faz upload de múltiplos .nst (arquivos e/ou diretórios)")
    upbatch.add_argument("paths", nargs="+", help="Arquivos ou diretórios contendo .nst")
    upbatch.add_argument("--recursive", action="store_true", help="Varre diretórios recursivamente")

    upurl = sub.add_parser("upload-url", help="Baixa .nst de uma URL/API e envia ao S3")
    upurl.add_argument("urls", nargs="+", help="URLs HTTP(s) para baixar o .nst")
    upurl.add_argument("--filename", help="Nome do arquivo para compor a chave S3 (opcional)")

    upidx = sub.add_parser("upload-url-index", help="Carrega uma lista de URLs de .nst a partir de um índice (JSON ou texto)")
    upidx.add_argument("index", help="URL do índice contendo os links de .nst")
    upidx.add_argument("--format", choices=["json", "txt"], default="json", help="Formato do índice (json: array de URLs/objetos; txt: 1 URL por linha)")

    args = parser.parse_args(argv)

    cfg = load_config()
    setup_logging(cfg.log_level)

    parser_service = NistParserService()
    checksum = ChecksumService()

    # Adaptadores reais (S3/DB)
    s3_client = MinioFactory(cfg).build()
    s3 = MinioS3Adapter(client=s3_client, bucket=cfg.s3_bucket)
    repo = PgPersonRepository(cfg)

    if args.command == "process":
        usecase = ProcessNistUseCase(s3=s3, repository=repo, parser=parser_service, checksum=checksum)
        count = usecase.execute()
        print(f"Processados: {count}")
        return 0

    if args.command == "upload":
        # leitura local para calcular chave e evitar duplicação
        from pathlib import Path
        raw = Path(args.path).read_bytes()
        base_key = parser_service.compose_key_for_upload(Path(args.path).name, raw)
        read_key = parser_service.destination_key_for_processed(base_key, raw)
        if s3.object_exists(base_key) or s3.object_exists(read_key):
            print(f"SKIP (exists): {base_key} or {read_key}")
            return 0
        s3.upload_bytes(base_key, raw)
        print(base_key)
        return 0

    if args.command == "delete":

        delete_usecase = DeleteNistUseCase(s3=s3)

        if args.key:

            delete_usecase.delete_by_key(args.key)

            print(f"Removido: {args.key}")

            return 0

        if args.prefix:

            removed = delete_usecase.delete_by_prefix(args.prefix)

            print(f"Removidos {removed} objetos com prefixo '{args.prefix}'")

            return 0

        if args.all:

            removed = delete_usecase.delete_all()

            print(f"Removidos {removed} objetos do bucket '{cfg.s3_bucket}'")

            return 0



    if args.command == "sample":
        limit = max(1, int(args.limit))
        checksum = ChecksumService()
        collected = []
        keys = s3.list_nists()
        for key in keys[:limit]:
            raw = s3.read_bytes(key)
            md5_hash = checksum.md5_bytes(raw)
            person, base = parser_service.parse(raw)
            setattr(base, "s3_key", key)
            repo.upsert_person_from_nist(person, base, md5_hash)
            item = {
                "key": key,
                "md5": md5_hash,
                "origem": getattr(base, "origem", None),
                "size": len(raw),
            }
            collected.append(item)
        print(json.dumps(collected, ensure_ascii=False, indent=2))
        return 0

    if args.command == "sample-local":
        from pathlib import Path
        limit = max(1, int(args.limit))
        checksum = ChecksumService()
        parser_service = NistParserService()
        root = Path("nists")
        if args.files:
            from pathlib import Path as _P
            files = [ _P(x) for x in args.files ]
        else:
            files = list(root.rglob("*.nst"))
        if not files:
            print("Nenhum arquivo .nst encontrado em 'nists/'.")
            return 1
        collected = []
        for fp in files[:limit]:
            raw = fp.read_bytes()
            md5_hash = checksum.md5_bytes(raw)
            person, base = parser_service.parse(raw)
            # usa um pseudo s3_key com prefixo local
            setattr(base, "s3_key", f"local/{fp.name}")
            repo.upsert_person_from_nist(person, base, md5_hash)
            item = {
                "key": f"local/{fp.name}",
                "md5": md5_hash,
                "origem": getattr(base, "origem", None),
                "size": len(raw),
            }
            collected.append(item)
        print(json.dumps(collected, ensure_ascii=False, indent=2))
        return 0

    if args.command == "db-sample":
        import psycopg
        limit = max(1, int(args.limit))
        with psycopg.connect(host=cfg.db_host, port=cfg.db_port, dbname=cfg.db_name, user=cfg.db_user, password=cfg.db_password) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='findface' AND table_type='BASE TABLE' ORDER BY table_name;")
                existing = [r[0] for r in cur.fetchall()]
                wanted = args.tables if args.tables else ["tb_nist_ingest", "tb_nist", "tb_log"]
                chosen = [t for t in wanted if t in existing]
                if not chosen and existing:
                    chosen = existing[:3]
                result = {"db": cfg.db_name, "schema": "findface", "tables": existing, "samples": {}}
                for t in chosen:
                    cur.execute(f"SELECT * FROM findface.{t} LIMIT %s", (limit,))
                    rows = cur.fetchall()
                    cols = [desc.name for desc in cur.description]
                    result["samples"][t] = {"columns": cols, "rows": rows}
        print(json.dumps(result, ensure_ascii=False, default=str, indent=2))
        return 0

    if args.command == "upload-batch":
        from pathlib import Path
        sent = []
        for p in args.paths:
            pth = Path(p)
            files = []
            if pth.is_dir():
                files = list(pth.rglob("*.nst")) if args.recursive else list(pth.glob("*.nst"))
            elif pth.is_file():
                files = [pth]
            else:
                continue
            for fp in files:
                try:
                    raw = fp.read_bytes()
                    base_key = parser_service.compose_key_for_upload(fp.name, raw)
                    read_key = parser_service.destination_key_for_processed(base_key, raw)
                    if s3.object_exists(base_key) or s3.object_exists(read_key):
                        sent.append({"file": str(fp), "status": "skipped_exists", "key": base_key})
                        continue
                    s3.upload_bytes(base_key, raw)
                    sent.append({"file": str(fp), "status": "uploaded", "key": base_key})
                except Exception as exc:
                    sent.append({"file": str(fp), "status": "error", "error": str(exc)})
        print(json.dumps(sent, ensure_ascii=False, indent=2))
        return 0

    if args.command == "upload-url-index":
        import urllib.request
        import json as _json
        import urllib.parse
        try:
            with urllib.request.urlopen(args.index, timeout=30) as resp:
                payload = resp.read().decode("utf-8", errors="ignore")
        except Exception as exc:
            print(_safe(f"Falha ao baixar índice: {exc}"))
            return 1

        urls: list[tuple[str, str | None]] = []
        if args.format == "txt":
            for line in payload.splitlines():
                u = line.strip()
                if not u:
                    continue
                urls.append((u, None))
        else:
            try:
                data = _json.loads(payload)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, str):
                            urls.append((item, None))
                        elif isinstance(item, dict) and "url" in item:
                            urls.append((str(item["url"]), item.get("filename")))
                else:
                    print("Índice JSON inválido: esperado array")
                    return 1
            except Exception as exc:
                print(_safe(f"Falha ao parsear índice JSON: {exc}"))
                return 1

        # Reutiliza fluxo do upload-url (com dedupe por existência)
        import urllib.request
        import urllib.parse
        sent = []
        for url, forced_name in urls:
            try:
                with urllib.request.urlopen(url, timeout=30) as resp:
                    raw = resp.read()
                fname = (forced_name or urllib.parse.unquote(urllib.parse.urlparse(url).path.split('/')[-1] or 'download.nst'))
                if not fname.endswith('.nst'):
                    fname = fname + '.nst'
                base_key = parser_service.compose_key_for_upload(fname, raw)
                read_key = parser_service.destination_key_for_processed(base_key, raw)
                if s3.object_exists(base_key) or s3.object_exists(read_key):
                    sent.append({"url": url, "status": "skipped_exists", "key": base_key})
                    continue
                s3.upload_bytes(base_key, raw)
                sent.append({"url": url, "status": "uploaded", "key": base_key, "size": len(raw)})
            except Exception as exc:
                sent.append({"url": url, "status": "error", "error": str(exc)})
        print(json.dumps(sent, ensure_ascii=False, indent=2))
        return 0

    if args.command == "upload-url":
        import urllib.request
        import urllib.parse
        sent = []
        for url in args.urls:
            try:
                with urllib.request.urlopen(url, timeout=30) as resp:
                    raw = resp.read()
                fname = args.filename or urllib.parse.unquote(urllib.parse.urlparse(url).path.split('/')[-1] or 'download.nst')
                if not fname.endswith('.nst'):
                    fname = fname + '.nst'
                base_key = parser_service.compose_key_for_upload(fname, raw)
                read_key = parser_service.destination_key_for_processed(base_key, raw)
                if s3.object_exists(base_key) or s3.object_exists(read_key):
                    sent.append({"url": url, "status": "skipped_exists", "key": base_key})
                    continue
                s3.upload_bytes(base_key, raw)
                sent.append({"url": url, "status": "uploaded", "key": base_key, "size": len(raw)})
            except Exception as exc:
                sent.append({"url": url, "status": "error", "error": str(exc)})
        print(json.dumps(sent, ensure_ascii=False, indent=2))
        return 0

    if args.command == "check-connections":
        def _safe(msg: object) -> str:
            try:
                return str(msg)
            except Exception:
                try:
                    return repr(msg)
                except Exception:
                    return "<unprintable>"
        # Teste S3
        try:
            # apenas itera 1 item para validar permissão/listagem
            keys = s3.list_nists()
            print(f"S3 OK - bucket='{cfg.s3_bucket}', objetos_nist={len(keys)}")
        except Exception as exc:
            print("S3 ERROR - " + _safe(exc).encode('cp1252', 'ignore').decode('cp1252'))

        # Teste PostgreSQL
        try:
            version = PgManager(cfg).test_connection()
            print("PostgreSQL OK - " + _safe(version).encode('cp1252', 'ignore').decode('cp1252'))
        except Exception as exc:
            print("PostgreSQL ERROR - " + _safe(exc).encode('cp1252', 'ignore').decode('cp1252'))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())


    delete_cmd = sub.add_parser("delete", help="Remove objetos do bucket S3")

    delete_group = delete_cmd.add_mutually_exclusive_group(required=True)

    delete_group.add_argument("--key", help="Chave completa do objeto a remover")

    delete_group.add_argument("--prefix", help="Prefixo dos objetos a remover")

    delete_group.add_argument("--all", action="store_true", help="Remove todos os objetos do bucket")
"""
mitra_minio_pipeline_upload_nist.py

Fluxo MITRA ajustado:
  1) Upload de até 200 NISTs (red + yellow) para o bucket "teste"
     Estrutura final no S3:
        nist/<campo_1:008>/<nome_arquivo>.nst
  2) Após "processar", mover cada objeto do bucket "teste" para "teste-lidos",
     preservando metadados e tags.

Observações:
  - Extrai campo 1:008 de cada NIST (nome de origem).
  - Normaliza endpoint :9001 → :9000 para API S3.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple, Optional, Literal, Dict
import re

from minio import Minio
from minio.error import S3Error
from minio.commonconfig import CopySource, Tags
from zoneinfo import ZoneInfo
from datetime import datetime
import unicodedata

# >>> CONSOLIDAÇÃO: Importar as funções canônicas de extração do campo 1:008
try:
    from minio_manager import _campo_1_008 # type: ignore
except ImportError:
    print("[FATAL] Não foi possível importar _campo_1_008 de minio_manager. Assegure que os dois arquivos estejam acessíveis um ao outro.")
    exit(1)


# ==============================
# Config
# ==============================

RED_DIR = Path(r"C:\Users\lucas\OneDrive\Documents\Programas\nist\rednotices")
YELLOW_DIR = Path(r"C:\Users\lucas\OneDrive\Documents\Programas\nist\yellownotices")
TSE_DIR = Path(r"C:\Users\lucas\OneDrive\Documents\Programas\nist\amostras\nists\tse")
SISMIGRA_DIR = Path(r"C:\Users\lucas\OneDrive\Documents\Programas\nist\amostras\nists\sismigra")
SINPA_DIR = Path(r"C:\Users\lucas\OneDrive\Documents\Programas\nist\amostras\nists\sinpa")
OUTROS_DIR = Path(r"C:\Users\lucas\OneDrive\Documents\Programas\nist\amostras\nists\outros")


SOURCE_BUCKET = "teste"
PROCESSED_BUCKET = "teste-lidos"

NIST_EXTS = (".nst", ".nist", ".an2", ".dat")
CollisionPolicy = Literal["overwrite", "suffix_timestamp_on_collision"]

# ==============================
# Utils (REDUNDÂNCIA REMOVIDA)
# ==============================

def now_iso_brt() -> str:
    return datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat(timespec="seconds")

def is_nist_file(p: Path) -> bool:
    return p.suffix.lower() in NIST_EXTS

# ==============================
# MinIO
# ==============================

@dataclass
class MinioSettings:
    endpoint: str = "http://10.95.4.61:9001"
    access_key: str = "teste"
    secret_key: str = "Nv30R1Yt"
    secure: bool = False
    source_bucket: str = SOURCE_BUCKET
    processed_bucket: str = PROCESSED_BUCKET
    collision_policy: CollisionPolicy = "overwrite"

    def normalized_endpoint_for_sdk(self) -> str:
        ep = re.sub(r"^https?://", "", self.endpoint.strip(), flags=re.IGNORECASE)
        host, sep, port = ep.partition(":")
        if sep and port == "9001":
            port = "9000"
        if not sep:
            port = "9000"
        return f"{host}:{port}"

def build_minio_client(cfg: MinioSettings) -> Minio:
    endpoint = cfg.normalized_endpoint_for_sdk()
    return Minio(endpoint, access_key=cfg.access_key, secret_key=cfg.secret_key, secure=cfg.secure)

# ==============================
# Upload
# ==============================

def list_local_nists(base_dir: Path, limit: Optional[int] = None) -> List[Path]:
    if not base_dir.exists() or not base_dir.is_dir():
        return []
    files = [p.resolve() for p in base_dir.iterdir() if p.is_file() and is_nist_file(p)]
    files.sort(key=lambda x: x.name)
    return files[:limit]

def upload_files_with_1_008(
    client: Minio,
    bucket: str,
    files: Iterable[Path],
    collision_policy: CollisionPolicy = "overwrite",
) -> List[str]:
    keys: List[str] = []
    for f in files:
        dados = f.read_bytes()
        campo = _campo_1_008(dados)
        desired_key = f"nist/{campo}/{f.name}"
        object_name = desired_key

        client.fput_object(
            bucket_name=bucket,
            object_name=object_name,
            file_path=str(f),
            content_type="application/octet-stream",
        )
        print(f"[UP] s3://{bucket}/{object_name}")
        keys.append(object_name)
    return keys

def upload_all(cfg: MinioSettings) -> List[str]:
    client = build_minio_client(cfg)
    red_files = list_local_nists(RED_DIR, limit=None) #coloque aqui o limite de arquivos que quer subir
    yellow_files = list_local_nists(YELLOW_DIR, limit=None) #coloque aqui o limite de arquivos que quer subir
    sismigra = list_local_nists(SISMIGRA_DIR, limit=None)
    sinpa = list_local_nists(SINPA_DIR, limit=None)
    tse = list_local_nists(TSE_DIR, limit=None)
    outros = list_local_nists(OUTROS_DIR, limit=None)
    keys = []
    #keys += upload_files_with_1_008(client, cfg.source_bucket, red_files, cfg.collision_policy)
    #keys += upload_files_with_1_008(client, cfg.source_bucket, yellow_files, cfg.collision_policy)
    keys += upload_files_with_1_008(client, cfg.source_bucket, sismigra, cfg.collision_policy)
    keys += upload_files_with_1_008(client, cfg.source_bucket, sinpa, cfg.collision_policy)
    keys += upload_files_with_1_008(client, cfg.source_bucket, tse, cfg.collision_policy)
    keys += upload_files_with_1_008(client, cfg.source_bucket, outros, cfg.collision_policy)
    return keys

# ==============================
# Execução
# ==============================

if __name__ == "__main__":
    cfg = MinioSettings()
    try:
        uploaded = upload_all(cfg)
        print(f"[OK] Uploads concluídos: {len(uploaded)} arquivos.")
    except Exception as e:
        print(f"[ERRO] Upload: {e}")
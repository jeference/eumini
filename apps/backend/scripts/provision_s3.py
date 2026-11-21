"""Cria e mantém a infraestrutura S3 do EuMini. Pode rodar de novo sem efeitos colaterais.

Usa a sessão do AWS CLI (`aws login`), que precisa poder administrar S3 e IAM.

    python scripts/provision_s3.py                                    # buckets e usuários IAM
    python scripts/provision_s3.py --create-key dev --env-file .env   # chave da aplicação
    python scripts/provision_s3.py --upload-local dev                 # envia o _media/ local

A secret da chave vai direto para o arquivo indicado e nunca aparece no terminal.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
import shutil
import subprocess
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

REGION = "sa-east-1"
ENVIRONMENTS = ("dev", "prod")
NONCURRENT_VERSION_DAYS = 7
LOCAL_MEDIA_FOLDERS = ("photo", "image")
BACKEND_DIR = Path(__file__).resolve().parent.parent
AWS_CLI_WINDOWS = Path(r"C:\Program Files\Amazon\AWSCLIV2\aws.exe")


class ProvisionError(Exception):
    """Situação que precisa de decisão humana antes de continuar."""


def bucket_name(env: str) -> str:
    return f"eumini-media-{env}"


def user_name(env: str) -> str:
    return f"eumini-app-{env}"


def admin_session() -> boto3.Session:
    """O boto3 só lê a sessão do `aws login` com um extra; o CLI entrega credenciais temporárias."""
    aws = shutil.which("aws") or str(AWS_CLI_WINDOWS)
    result = subprocess.run(
        [aws, "configure", "export-credentials", "--format", "process"],
        check=True,
        capture_output=True,
        text=True,
    )
    credentials = json.loads(result.stdout)
    return boto3.Session(
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials.get("SessionToken"),
        region_name=REGION,
    )


def tls_only_policy(bucket: str) -> dict:
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "DenyInsecureTransport",
                "Effect": "Deny",
                "Principal": "*",
                "Action": "s3:*",
                "Resource": [f"arn:aws:s3:::{bucket}", f"arn:aws:s3:::{bucket}/*"],
                "Condition": {"Bool": {"aws:SecureTransport": "false"}},
            }
        ],
    }


def app_policy(bucket: str) -> dict:
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ObjectsInEuMiniBucket",
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
                "Resource": f"arn:aws:s3:::{bucket}/*",
            },
            {
                # Sem esta permissão, um objeto inexistente volta 403 em vez de NoSuchKey.
                "Sid": "MissingObjectsReturnNotFound",
                "Effect": "Allow",
                "Action": "s3:ListBucket",
                "Resource": f"arn:aws:s3:::{bucket}",
            },
        ],
    }


def ensure_bucket(s3, bucket: str) -> None:
    try:
        s3.create_bucket(
            Bucket=bucket,
            CreateBucketConfiguration={"LocationConstraint": REGION},
            ObjectOwnership="BucketOwnerEnforced",
        )
        s3.get_waiter("bucket_exists").wait(Bucket=bucket)
    except s3.exceptions.BucketAlreadyOwnedByYou:
        pass

    s3.put_public_access_block(
        Bucket=bucket,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )
    s3.put_bucket_ownership_controls(
        Bucket=bucket,
        OwnershipControls={"Rules": [{"ObjectOwnership": "BucketOwnerEnforced"}]},
    )
    s3.put_bucket_encryption(
        Bucket=bucket,
        ServerSideEncryptionConfiguration={
            "Rules": [
                {
                    "ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"},
                    "BlockedEncryptionTypes": {"EncryptionType": ["SSE-C"]},
                }
            ]
        },
    )
    s3.put_bucket_policy(Bucket=bucket, Policy=json.dumps(tls_only_policy(bucket)))
    s3.put_bucket_versioning(Bucket=bucket, VersioningConfiguration={"Status": "Enabled"})
    s3.put_bucket_lifecycle_configuration(
        Bucket=bucket,
        LifecycleConfiguration={
            "Rules": [
                {
                    "ID": "expire-old-versions",
                    "Status": "Enabled",
                    "Filter": {},
                    "NoncurrentVersionExpiration": {"NoncurrentDays": NONCURRENT_VERSION_DAYS},
                    "Expiration": {"ExpiredObjectDeleteMarker": True},
                    "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 1},
                }
            ]
        },
    )
    print(f"Bucket {bucket}: configurado em {REGION}.")


def ensure_app_user(iam, env: str) -> None:
    user = user_name(env)
    try:
        iam.create_user(UserName=user, Tags=[{"Key": "project", "Value": "eumini"}])
    except iam.exceptions.EntityAlreadyExistsException:
        pass
    iam.put_user_policy(
        UserName=user,
        PolicyName=f"{user}-s3",
        PolicyDocument=json.dumps(app_policy(bucket_name(env))),
    )
    print(f"Usuário IAM {user}: acesso restrito a {bucket_name(env)}.")


def read_env_value(env_file: Path, name: str) -> str:
    if not env_file.exists():
        return ""
    match = re.search(rf"^{name}=(.*)$", env_file.read_text(encoding="utf-8"), re.MULTILINE)
    return match.group(1).strip() if match else ""


def write_env_values(env_file: Path, values: dict[str, str]) -> None:
    content = env_file.read_bytes().decode("utf-8") if env_file.exists() else ""
    newline = "\r\n" if "\r\n" in content else "\n"
    for name, value in values.items():
        line = f"{name}={value}"
        pattern = re.compile(rf"^{name}=[^\r\n]*", re.MULTILINE)
        if pattern.search(content):
            content = pattern.sub(line.replace("\\", r"\\"), content)
        else:
            content = f"{content.rstrip()}{newline}{line}{newline}"
    env_file.write_bytes(content.encode("utf-8"))


def create_app_key(iam, env: str, env_file: Path) -> None:
    user = user_name(env)
    existing = iam.list_access_keys(UserName=user)["AccessKeyMetadata"]
    current = read_env_value(env_file, "AWS_ACCESS_KEY_ID")
    if any(key["AccessKeyId"] == current for key in existing):
        print(f"Chave de {user}: já está em {env_file.name}.")
        return
    if existing:
        raise ProvisionError(
            f"{user} já tem uma chave que não está em {env_file.name}. "
            "Revogue a chave antiga antes de criar outra."
        )
    key = iam.create_access_key(UserName=user)["AccessKey"]
    write_env_values(
        env_file,
        {
            "MEDIA_STORAGE_ADAPTER": "integrations.adapters.media_s3.S3MediaAdapter",
            "AWS_ACCESS_KEY_ID": key["AccessKeyId"],
            "AWS_SECRET_ACCESS_KEY": key["SecretAccessKey"],
            "AWS_S3_REGION_NAME": REGION,
            "AWS_STORAGE_BUCKET_NAME": bucket_name(env),
        },
    )
    print(f"Chave de {user}: gravada em {env_file.name}.")


def upload_local_media(s3, env: str) -> None:
    root = BACKEND_DIR / "_media"
    bucket = bucket_name(env)
    sent = 0
    for folder in LOCAL_MEDIA_FOLDERS:
        for path in sorted((root / folder).rglob("*")):
            if not path.is_file():
                continue
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            s3.upload_file(
                str(path),
                bucket,
                path.relative_to(root).as_posix(),
                ExtraArgs={"ContentType": content_type},
            )
            sent += 1
    print(f"Mídias locais: {sent} arquivos enviados para {bucket}.")


def provision(args: argparse.Namespace) -> None:
    session = admin_session()
    s3 = session.client("s3")
    iam = session.client("iam")
    for env in ENVIRONMENTS:
        ensure_bucket(s3, bucket_name(env))
        ensure_app_user(iam, env)
    if args.create_key:
        create_app_key(iam, args.create_key, args.env_file)
    if args.upload_local:
        upload_local_media(s3, args.upload_local)


def main() -> int:
    parser = argparse.ArgumentParser(description="Provisiona o S3 do EuMini.")
    parser.add_argument("--create-key", choices=ENVIRONMENTS, help="cria a chave da aplicação")
    parser.add_argument("--env-file", type=Path, help="arquivo que recebe a chave")
    parser.add_argument("--upload-local", choices=ENVIRONMENTS, help="envia o _media/ local")
    args = parser.parse_args()
    if args.create_key and not args.env_file:
        parser.error("--create-key exige --env-file")

    try:
        provision(args)
    except (ClientError, ProvisionError, subprocess.CalledProcessError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

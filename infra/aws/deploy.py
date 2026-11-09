"""Deploy the inference service to AWS, or take it down.

    python infra/aws/deploy.py --cors-origin https://your-site.vercel.app
    python infra/aws/deploy.py --destroy

In order: the base stack (bucket, repository, logs, roles), the model to S3, the image to ECR, then the Express Mode
service. Uses the AWS CLI and Docker on PATH, with the CLI's current profile and region.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE_STACK = "doodleverse-base"
SERVICE_STACK = "doodleverse-api"


def run(
    *command: str, stdin: str | None = None, check: bool = True, env: dict | None = None
) -> subprocess.CompletedProcess:
    completed = subprocess.run(
        list(command), cwd=ROOT, input=stdin, env=env, capture_output=True, encoding="utf-8", errors="replace"
    )
    if check and completed.returncode != 0:
        raise RuntimeError(f"{' '.join(command[:3])} failed:\n{completed.stderr.strip()[-3000:]}")
    return completed


def aws(*args: str) -> str:
    return run("aws", *args).stdout.strip()


def aws_json(*args: str):
    return json.loads(aws(*args, "--output", "json"))


def failed_events(stack: str) -> list[str]:
    events = aws_json("cloudformation", "describe-stack-events", "--stack-name", stack, "--max-items", "40")
    return [
        f"{event['LogicalResourceId']}: {event.get('ResourceStatusReason', '')}"
        for event in events["StackEvents"]
        if event["ResourceStatus"].endswith("FAILED")
    ]


def deploy_stack(name: str, template: str, **parameters: str) -> dict:
    command = ["cloudformation", "deploy", "--stack-name", name, "--template-file", str(HERE / template)]
    command += ["--capabilities", "CAPABILITY_NAMED_IAM", "--no-fail-on-empty-changeset"]
    if parameters:
        command += ["--parameter-overrides", *(f"{key}={value}" for key, value in parameters.items())]
    print(f"stack {name}: deploying", flush=True)
    try:
        aws(*command)
    except RuntimeError as error:
        reasons = "\n".join(failed_events(name)) or "no failed events"
        raise RuntimeError(f"{error}\n{reasons}") from error
    outputs = aws_json("cloudformation", "describe-stacks", "--stack-name", name, "--query", "Stacks[0].Outputs")
    return {item["OutputKey"]: item["OutputValue"] for item in outputs or []}


def upload_model(bucket: str, model_dir: Path) -> str:
    """Put sidecar.json and the model under models/<variant>-<sha12>, once. Versioning keeps every overwrite."""

    sidecar = json.loads((model_dir / "sidecar.json").read_text(encoding="utf-8"))
    prefix = f"models/{sidecar['variant']}-{sidecar['sha256'][:12]}"
    for name in ("sidecar.json", sidecar["model_file"]):
        key = f"{prefix}/{name}"
        head = run("aws", "s3api", "head-object", "--bucket", bucket, "--key", key, "--output", "json", check=False)
        if head.returncode == 0 and json.loads(head.stdout)["Metadata"].get("model-sha256") == sidecar["sha256"]:
            print(f"s3://{bucket}/{key}: already there", flush=True)
            continue
        put = aws_json(
            "s3api", "put-object", "--bucket", bucket, "--key", key, "--body", str(model_dir / name),
            "--metadata", f"model-sha256={sidecar['sha256']}",
        )
        print(f"s3://{bucket}/{key}: uploaded, version {put['VersionId']}", flush=True)
    return f"s3://{bucket}/{prefix}"


def push_image(repository_uri: str, allow_dirty: bool) -> str:
    """Build the inference image, tag it with the commit, and push it unless ECR already has that tag."""

    commit = run("git", "rev-parse", "--short=12", "HEAD").stdout.strip()
    dirty = bool(run("git", "status", "--porcelain").stdout.strip())
    if dirty and not allow_dirty:
        raise RuntimeError("Commit first: images are tagged with the commit they were built from.")
    tag = f"{commit}-dirty-{int(time.time())}" if dirty else commit
    image = f"{repository_uri}:{tag}"
    registry, repository = repository_uri.split("/", 1)
    known = run("aws", "ecr", "describe-images", "--repository-name", repository, "--image-ids", f"imageTag={tag}",
                check=False)
    if known.returncode == 0:
        print(f"{image}: already in ECR", flush=True)
        return image
    print(f"{image}: building", flush=True)
    run("docker", "build", "--file", "infra/inference.Dockerfile", "--tag", image, ".")
    engine = run("docker", "context", "inspect", "--format", "{{.Endpoints.docker.Host}}").stdout.strip()
    with tempfile.TemporaryDirectory() as config:
        # An ECR token is longer than Windows Credential Manager will store. An empty helper for this one
        # registry keeps the login in this throwaway config instead, removed once the push is done.
        Path(config, "config.json").write_text(json.dumps({"credHelpers": {registry: ""}}), encoding="utf-8")
        env = {**os.environ, "DOCKER_CONFIG": config, "DOCKER_HOST": engine}
        token = aws("ecr", "get-login-password")
        run("docker", "login", "--username", "AWS", "--password-stdin", registry, stdin=token, env=env)
        print(f"{image}: pushing", flush=True)
        run("docker", "push", image, env=env)
    return image


def wait_until_healthy(endpoint: str, timeout_s: float = 900) -> str:
    url = endpoint if endpoint.startswith("http") else f"https://{endpoint}"
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/health", timeout=10) as response:
                if response.status == 200:
                    return url
        except OSError:
            pass
        time.sleep(10)
    raise RuntimeError(f"{url}/health did not answer within {timeout_s / 60:.0f} minutes.")


def deploy(args: argparse.Namespace) -> None:
    base = deploy_stack(BASE_STACK, "base.yml")
    model_uri = upload_model(base["ModelBucketName"], args.model_dir)
    image = push_image(base["ImageRepositoryUri"], args.allow_dirty)
    service = deploy_stack(
        SERVICE_STACK,
        "service.yml",
        BaseStack=BASE_STACK,
        ImageUri=image,
        ModelUri=model_uri,
        CorsOrigins=",".join(args.cors_origin),
        Cpu=args.cpu,
        Memory=args.memory,
    )
    print("waiting for /health", flush=True)
    url = wait_until_healthy(service["Endpoint"])
    print(f"\napi    {url}\nimage  {image}\nmodel  {model_uri}\ncors   {', '.join(args.cors_origin)}")


def destroy() -> None:
    for stack in (SERVICE_STACK, BASE_STACK):
        print(f"stack {stack}: deleting", flush=True)
        aws("cloudformation", "delete-stack", "--stack-name", stack)
        aws("cloudformation", "wait", "stack-delete-complete", "--stack-name", stack)
    print("The model bucket stays, with every version in it. Empty and delete it in the S3 console to remove it.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy the Doodleverse inference service to AWS.")
    parser.add_argument("--cors-origin", action="append", default=[], help="the web app's origin; repeatable")
    parser.add_argument("--model-dir", type=Path, default=ROOT / "artifacts" / "model")
    parser.add_argument("--cpu", default="512", help="Fargate CPU units: 512 is half a vCPU")
    parser.add_argument("--memory", default="1024", help="Fargate memory in MiB")
    parser.add_argument("--allow-dirty", action="store_true", help="build from uncommitted changes")
    parser.add_argument("--destroy", action="store_true", help="delete both stacks")
    args = parser.parse_args()
    if args.destroy:
        destroy()
        return
    if not args.cors_origin:
        parser.error("--cors-origin is required: the API only answers browsers on that origin.")
    deploy(args)


if __name__ == "__main__":
    main()

# Deploy

Live since November 9, 2026:

- Web: [doodleverse-alpha.vercel.app](https://doodleverse-alpha.vercel.app)
- API: [do-9dc5f019ec4b438da6034795dff16196.ecs.us-east-2.on.aws](https://do-9dc5f019ec4b438da6034795dff16196.ecs.us-east-2.on.aws/health)

A sun drawn on the live site with a real mouse came back from that API as `sun`, score 1.000, not uncertain, model `gap-1ce366c1a170`, and was placed in the world. Preflights from either Vercel origin get `Access-Control-Allow-Origin`; a preflight from any other origin gets a 400 without it.

## What runs where

| piece | where | settings |
| --- | --- | --- |
| web | Vercel project `doodleverse` | Next.js from `apps/web`, Node 24.x, `NEXT_PUBLIC_API_URL` set for production |
| API | ECS Express Mode service `doodleverse-inference`, us-east-2 | Fargate, 512 CPU units (half a vCPU), 1024 MiB, one task, container port 8000 |
| health check | the Express Mode load balancer | `GET /health`, HTTPS on the domain AWS assigns, with its ACM certificate |
| model | `s3://doodleverse-models-<account id>-us-east-2/models/gap-1ce366c1a170/` | versioned, private, TLS only, SSE-S3 |
| image | ECR `doodleverse-inference:8fad913ccd64` | tags are commits and cannot be overwritten; scanned on push; the five newest kept |
| logs | CloudWatch `/doodleverse/inference` | 14 days |

The model objects are `sidecar.json` (version `2dh.BAIEhbCXm9ZF8ttfd3IFXrLZLr3q`) and `model.keras` (version `526y.U6J9xGrQd.veHeERscQ4.yPbdNw`, 433,944 bytes). At startup the task copies both into `/tmp/model` because `DOODLEVERSE_MODEL_URI` points at that prefix, then checks the model's SHA-256 against the sidecar before it answers anything. Its first start logged `load_ms=7793`: importing TensorFlow, the copy from S3, and loading, on half a vCPU.

## Permissions

Each role can do one job:

- `doodleverse-inference-task`, the code's own role: `s3:GetObject` on `models/*` in the model bucket. Nothing else.
- `doodleverse-inference-execution`, used by ECS to start the task: pull from the one image repository, write to the one log group.
- `doodleverse-ecs-infrastructure`, used by Express Mode: the AWS-managed `AmazonECSInfrastructureRoleforExpressGatewayServices`, for the load balancer, certificate, security groups, and scaling.

There are no secrets to store. The API holds no keys: the task role hands it short-lived credentials. The web app's one setting, `NEXT_PUBLIC_API_URL`, is public by design and lives in Vercel's environment settings.

## Deploy or redeploy

[`infra/aws/base.yml`](../infra/aws/base.yml) holds what outlives a deploy: the bucket, the repository, the log group, and the roles. [`infra/aws/service.yml`](../infra/aws/service.yml) is the Express Mode service. [`infra/aws/deploy.py`](../infra/aws/deploy.py) runs them in order:

```bash
aws login --profile doodleverse      # browser sign-in, good for up to 12 hours
export AWS_PROFILE=doodleverse       # PowerShell: $env:AWS_PROFILE = "doodleverse"
python infra/aws/deploy.py \
  --cors-origin https://doodleverse-alpha.vercel.app \
  --cors-origin https://doodleverse-sanats-projects-f399757a.vercel.app
```

It creates the service-linked roles a new account lacks, deploys the base stack, uploads the model under `models/<variant>-<sha12>/` unless it is already there, builds and pushes the image tagged with the commit unless ECR already has it, deploys the service, and waits for `/health`. It refuses to build from uncommitted changes.

The web app:

```bash
cd apps/web
vercel env add NEXT_PUBLIC_API_URL production --value <the api url>   # only when the API URL changes
vercel deploy --prod
```

`NEXT_PUBLIC_API_URL` is baked into the bundle at build time, so changing it needs a new deploy. The Vercel project is linked to the GitHub repository with Git deployments turned off. Pushing does not deploy. To deploy on push instead, set the project's Root Directory to `apps/web` and turn Git deployments on; after that, run `vercel deploy` from the repository root, not from `apps/web`.

## Roll back

- API: rerun the service stack with an earlier image tag, from ECR or `git log`.
- Model: a new model gets its own prefix, and the old prefix stays. An overwritten object keeps its earlier versions.
- Web: `vercel rollback`, or promote an earlier deployment in the dashboard.

## Take it down

```bash
python infra/aws/deploy.py --destroy
```

That deletes the service, its load balancer and certificate, the image repository, the roles, and the log group. The model bucket stays, with every version in it, until it is emptied and deleted by hand.

## Cost

Not a bill: an estimate from AWS's list prices for us-east-2. One half-vCPU, 1 GB Fargate task running all month is about $18. The load balancer is about $16 plus a little for traffic. Each public IPv4 address, one per load balancer zone and one for the task, is about $3.65. Together that is roughly $50 a month while it runs. Images, model files, and logs add cents.

This AWS account is on the free plan: $100 in credits, ending on May 9, 2027 or when the credits run out, whichever comes first. At about $50 a month the credits cover roughly two months, so take the API down between demos. Vercel's Hobby plan costs nothing.

## Without AWS

Docker Compose runs the same two images on one machine:

```bash
docker compose -f infra/docker-compose.yml up --build
```

| service | port | health check | CPU and memory |
| --- | --- | --- | --- |
| inference | 8000 | `GET /health` every 10 s, 30 s to start | no limit set; measured in [benchmark-results.md](benchmark-results.md) |
| web | 3000 | starts once inference is healthy | no limit set |

The inference container mounts `artifacts/model` read-only and keeps its filesystem read-only apart from a `/tmp` tmpfs. Nothing in the Compose path needs an AWS or Vercel account.

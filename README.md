# AI inference platform lab

A staged platform engineering lab: FastAPI gateway → internal Ollama Service →
`qwen2.5:0.5b`, with persistent model storage in Kubernetes.

## Baseline inspection — 17 November 2026

Repository:

- `main.py`: `/generate`, `/health/live`, and `/health/ready`; prompt length
  validation, configurable Ollama URL/model, non-streaming inference, and HTTP
  error handling. Readiness checks that the configured model is installed.
- `Dockerfile`: Python 3.12 slim image, dependency installation, non-root user,
  and Uvicorn entrypoint.
- `ollama.yaml`: one replica, Recreate strategy, resource requests/limits,
  5 GiB ReadWriteOnce PVC mounted at `/root/.ollama`, and internal Service.
- `gateway.yaml`: two replicas, resources, liveness/readiness probes,
  Ollama configuration, and ClusterIP Service.
- `app/`, `tests/`, `k8s/`, and `monitoring/` exist but contain no files.
- No namespace manifest, automated model provisioning, NetworkPolicies, tests,
  application metrics, or monitoring configuration is present in this repository.
- Existing uncommitted changes to `main.py` and `Dockerfile`, and untracked
  `gateway.yaml` and `image.png`, were preserved during inspection.

Observed environment (a snapshot, not a deployment guarantee):

- Docker client/server reachable; approximately 8 CPUs and 15.6 GiB RAM.
- Active Kubernetes context: `docker-desktop`; two Ready nodes on v1.31.1.
- In `ai-platform`: gateway 2/2 available, Ollama 1/1 available, both internal
  Services have endpoints, and `ollama-models` is Bound with 5 GiB storage.
- Gateway liveness/readiness returned HTTP 200 through a temporary port-forward.
  Ollama `/api/tags` reported `qwen2.5:0.5b`. Generation was not exercised.
- No NetworkPolicies or Jobs were found in `ai-platform`.
- Prometheus and Grafana deployments exist in `monitoring`; scrape configuration
  and gateway coverage have not been inspected.
- Default storage uses `rancher.io/local-path`, with reclaim policy `Delete`.
  This is local node storage, not highly available storage or a backup.
- Network agent image: `kindest/kindnetd:v20241007-36f62932`. NetworkPolicy
  enforcement must be established and tested before claiming isolation.
- Host virtualenv uses Python 3.10; container uses 3.12. `pytest` and
  `prometheus-client` are absent from the existing virtualenv.

## Implementation sequence

Complete and validate one stage before proceeding to the next.

1. **Repository and build baseline.** Move the gateway into `app/`, manifests
   into `k8s/`, align Docker imports, and exclude virtualenvs, Git data, and
   caches from the Docker build context. Validate the image starts as non-root.
2. **Gateway resilience and tests.** Reuse an HTTPX client through FastAPI's
   lifespan; handle timeouts and malformed backend responses; validate inputs
   and outputs. Add pytest/httpx tests with a mocked backend, covering success,
   missing model, backend errors, and dependency-independent liveness.
3. **Reproducible Kubernetes deployment.** Add namespace ownership, pin images,
   retain the PVC, add Ollama startup/liveness/readiness probes, and provision
   the model with an explicit repeatable workflow. Validate two gateway replicas,
   inference, and persistence across an Ollama pod replacement.
4. **Isolation and hardening.** Establish a policy-enforcing network environment;
   add default-deny policies and explicit DNS, gateway-to-Ollama, monitoring,
   and model-download allowances. Test allowed and denied connections.
   Add appropriate pod/container security settings.
5. **Observability.** Inspect existing Prometheus/Grafana configuration before
   choosing integration. Add bounded-label HTTP and backend metrics, scrape
   configuration, a versioned dashboard, and useful alerts. Validate that a real
   inference request appears in metrics and Grafana.
6. **EKS/vLLM preparation.** Separate the public gateway contract from backend
   adapters: Ollama's native API and vLLM's OpenAI-compatible API differ.
   Document GPU scheduling, device support, model format compatibility, storage,
   IAM, image distribution, and cost controls; keep cloud configuration separate
   from the local baseline. Do not deploy cloud resources during this stage.

Design principles: liveness checks the gateway process; readiness checks its
ability to serve the configured model. Two gateway replicas provide gateway
redundancy; one Ollama replica remains a backend availability limit. A PVC keeps
model files across pod replacement but does not provide backend high availability.
NetworkPolicy objects require a supporting implementation and connectivity tests:
[Kubernetes NetworkPolicies](https://kubernetes.io/docs/concepts/services-networking/network-policies/).

## First exercise: repository layout

Target layout:

```text
app/
  __init__.py
  main.py
tests/
k8s/
  ollama.yaml
  gateway.yaml
monitoring/
Dockerfile
.dockerignore
requirements.txt
README.md
```

Move `main.py` to `app/main.py`, create `app/__init__.py`, and move the two YAML
files into `k8s/`. Update the Dockerfile to `COPY app/ ./app/` and start
`uvicorn app.main:app`. Add `.dockerignore` entries for `.git/`, `.venv*/`,
`__pycache__/`, `*.py[cod]`, and `.pytest_cache/`.

Build and test a new image without replacing the running deployment:

```bash
docker build -t ai-gateway:stage1 .
docker run --rm ai-gateway:stage1 id
docker run --rm -p 127.0.0.1:18000:8000 ai-gateway:stage1
```

In another terminal:

```bash
curl -i http://127.0.0.1:18000/health/live
```

Acceptance: image builds, `id` reports a non-zero UID, and liveness returns HTTP
200 with `{"status":"alive"}`. Stop the test container with Ctrl+C. This standalone
container does not have Kubernetes Service DNS access; readiness is expected to
return 503 with its default Ollama URL. No Kubernetes apply is needed for stage 1.

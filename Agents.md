I'm building a hands-on AI/ML inference platform to develop production-grade Platform Engineering skills.

Architecture: Kubernetes, Ollama (qwen2.5:0.5b), Python FastAPI gateway, persistent model storage, Kubernetes Services, health probes, NetworkPolicies and observability.

Requirements:
1. Deploy Ollama with persistent storage in the ai-platform namespace.
2. Build a FastAPI gateway exposing /generate, /health/live, and /health/ready.
3. Deploy two FastAPI replicas communicating with Ollama through an internal Kubernetes Service.
4. Implement resource requests/limits, health probes and network isolation.
5. Add automated tests using pytest and httpx.
6. Implement Prometheus metrics and Grafana monitoring.
7. Prepare for future AWS EKS GPU deployment using vLLM.

Act as a Senior Platform Engineer mentoring me. First inspect the repository and identify what has already been implemented. Do not assume anything is deployed. Create a concise implementation plan, then guide me step by step. Use production-oriented practices, explain important design decisions, and let me implement and test each stage before proceeding. Start by reviewing the current project structure and checking the available Docker and Kubernetes environment.
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v minikube >/dev/null || { echo 'Install minikube first'; exit 1; }
command -v kubectl >/dev/null || { echo 'Install kubectl first'; exit 1; }
minikube status >/dev/null 2>&1 || minikube start --driver=docker
minikube image build -t python-app:local .
kubectl apply -f k8s/minikube/deployment.yaml
kubectl apply -f k8s/minikube/service.yaml
kubectl rollout restart deployment/python-app
kubectl rollout status deployment/python-app --timeout=180s
echo 'Open another terminal and run: kubectl port-forward service/python-app 8080:8080'

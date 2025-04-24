import pytest
from unittest.mock import MagicMock
from dell_ai.snippets import get_deployment_snippet, SnippetRequest, SnippetResponse
from dell_ai.exceptions import DellAIError, ValidationError

# Real-world example snippets
LLAMA_MAVERICK_DOCKER_SNIPPET = """docker run \\
    -it \\
    -p 80:80 \\
    --security-opt seccomp=unconfined \\
    --device=/dev/kfd \\
    --device=/dev/dri \\
    --group-add video \\
    --ipc=host \\
    --shm-size 256g \\
    -e NUM_SHARD=8 \\
    -e MAX_BATCH_PREFILL_TOKENS=16484 \\
    -e MAX_TOTAL_TOKENS=16384 \\
    -e MAX_INPUT_TOKENS=16383 \\
    registry.dell.huggingface.co/enterprise-dell-inference-meta-llama-llama-4-maverick-17b-128e-instruct-amd"""

LLAMA_MAVERICK_K8S_SNIPPET = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: tgi-deployment
spec:
  replicas: 1
  selector:
    matchLabels:
      app: tgi-server
  template:
    metadata:
      labels:
        app: tgi-server
        hf.co/model: meta-llama--Llama-4-Maverick-17B-128E-Instruct
        hf.co/task: text-generation
    spec:
      containers:
        - name: tgi-container
          image: registry.dell.huggingface.co/enterprise-dell-inference-meta-llama-llama-4-maverick-17b-128e-instruct-amd
          securityContext:
            seccompProfile:
              type: Unconfined
          resources:
            limits:
              amd.com/gpu: 8
          env: 
            - name: NUM_SHARD
              value: "8"
            - name: MAX_BATCH_PREFILL_TOKENS
              value: "16484"
            - name: MAX_TOTAL_TOKENS
              value: "16384"
            - name: MAX_INPUT_TOKENS
              value: "16383"
          volumeMounts:
            - mountPath: /dev/shm
              name: dshm
            - name: dev-kfd
              mountPath: /dev/kfd
            - name: dev-dri
              mountPath: /dev/dri
      volumes:
        - name: dshm
          emptyDir:
            medium: Memory
            sizeLimit: 256Gi
        - name: dev-kfd
          hostPath:
            path: /dev/kfd
        - name: dev-dri
          hostPath:
            path: /dev/dri"""


@pytest.fixture
def mock_client():
    client = MagicMock()
    return client


def test_get_deployment_snippet_docker(mock_client):
    """Test successful retrieval of Docker deployment snippet with real-world example"""
    # Mock the model response
    mock_client._make_request.side_effect = [
        {
            "repoName": "meta-llama/Llama-4-Maverick-17B-128E-Instruct",
            "configsDeploy": {
                "xe9680-amd-mi300x": [
                    {
                        "max_batch_prefill_tokens": 16484,
                        "max_input_tokens": 16383,
                        "max_total_tokens": 16384,
                        "num_gpus": 8,
                    }
                ]
            },
        },
        {
            "snippet": LLAMA_MAVERICK_DOCKER_SNIPPET,
            "engine": "docker",
        },
    ]

    result = get_deployment_snippet(
        client=mock_client,
        model_id="meta-llama/Llama-4-Maverick-17B-128E-Instruct",
        sku_id="xe9680-amd-mi300x",
        engine="docker",
        num_gpus=8,
        num_replicas=1,
    )

    assert isinstance(result, str)
    assert result == LLAMA_MAVERICK_DOCKER_SNIPPET
    assert mock_client._make_request.call_count == 2


def test_get_deployment_snippet_kubernetes(mock_client):
    """Test successful retrieval of Kubernetes deployment snippet with real-world example"""
    # Mock the model response
    mock_client._make_request.side_effect = [
        {
            "repoName": "meta-llama/Llama-4-Maverick-17B-128E-Instruct",
            "configsDeploy": {
                "xe9680-amd-mi300x": [
                    {
                        "max_batch_prefill_tokens": 16484,
                        "max_input_tokens": 16383,
                        "max_total_tokens": 16384,
                        "num_gpus": 8,
                    }
                ]
            },
        },
        {
            "snippet": LLAMA_MAVERICK_K8S_SNIPPET,
            "engine": "kubernetes",
        },
    ]

    result = get_deployment_snippet(
        client=mock_client,
        model_id="meta-llama/Llama-4-Maverick-17B-128E-Instruct",
        sku_id="xe9680-amd-mi300x",
        engine="kubernetes",
        num_gpus=8,
        num_replicas=1,
    )

    assert isinstance(result, str)
    assert result == LLAMA_MAVERICK_K8S_SNIPPET
    assert mock_client._make_request.call_count == 2


def test_get_deployment_snippet_error_handling(mock_client):
    """Test error handling in get_deployment_snippet"""
    # Test API error
    mock_client._make_request.side_effect = DellAIError("API Error")
    with pytest.raises(DellAIError):
        get_deployment_snippet(
            client=mock_client,
            model_id="meta-llama/Llama-4-Maverick-17B-128E-Instruct",
            sku_id="xe9680-amd-mi300x",
            engine="docker",
            num_gpus=8,
            num_replicas=1,
        )

    # Test invalid model_id format
    with pytest.raises(ValidationError):
        get_deployment_snippet(
            client=mock_client,
            model_id="invalid-model-id",
            sku_id="xe9680-amd-mi300x",
            engine="docker",
            num_gpus=8,
            num_replicas=1,
        )


def test_snippet_request_validation():
    """Test SnippetRequest validation with real-world values"""
    # Test valid request
    request = SnippetRequest(
        model_id="meta-llama/Llama-4-Maverick-17B-128E-Instruct",
        sku_id="xe9680-amd-mi300x",
        engine="docker",
        num_gpus=8,
        num_replicas=1,
    )
    assert request.model_id == "meta-llama/Llama-4-Maverick-17B-128E-Instruct"
    assert request.num_gpus == 8

    # Test invalid values
    with pytest.raises(ValueError):
        SnippetRequest(
            model_id="meta-llama/Llama-4-Maverick-17B-128E-Instruct",
            sku_id="xe9680-amd-mi300x",
            engine="invalid",
            num_gpus=8,
            num_replicas=1,
        )

    with pytest.raises(ValueError):
        SnippetRequest(
            model_id="meta-llama/Llama-4-Maverick-17B-128E-Instruct",
            sku_id="xe9680-amd-mi300x",
            engine="docker",
            num_gpus=0,
            num_replicas=1,
        )


def test_snippet_response_validation():
    """Test SnippetResponse validation with real-world example"""
    response = SnippetResponse(snippet=LLAMA_MAVERICK_DOCKER_SNIPPET)
    assert response.snippet == LLAMA_MAVERICK_DOCKER_SNIPPET

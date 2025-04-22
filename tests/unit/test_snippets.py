import pytest
from unittest.mock import MagicMock
from dell_ai.snippets import get_deployment_snippet, SnippetRequest, SnippetResponse
from dell_ai.exceptions import DellAIError, ValidationError

# Mock API responses
MOCK_DOCKER_SNIPPET = """docker run -d \\
    --gpus all \\
    -p 8000:8000 \\
    dell/llama2-7b:latest"""

MOCK_K8S_SNIPPET = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: llama2-7b
spec:
  replicas: 1
  selector:
    matchLabels:
      app: llama2-7b
  template:
    metadata:
      labels:
        app: llama2-7b
    spec:
      containers:
      - name: llama2-7b
        image: dell/llama2-7b:latest
        resources:
          limits:
            nvidia.com/gpu: 1"""


@pytest.fixture
def mock_client():
    client = MagicMock()
    return client


def test_get_deployment_snippet_docker(mock_client):
    """Test successful retrieval of Docker deployment snippet"""
    mock_client._make_request.return_value = {
        "snippet": MOCK_DOCKER_SNIPPET,
        "container_type": "docker",
    }

    result = get_deployment_snippet(
        client=mock_client,
        model_id="dell/llama2-7b",
        sku_id="dell-xe9640",
        container_type="docker",
        num_gpus=1,
        num_replicas=1,
    )

    assert isinstance(result, str)
    assert result == MOCK_DOCKER_SNIPPET
    mock_client._make_request.assert_called_once()


def test_get_deployment_snippet_kubernetes(mock_client):
    """Test successful retrieval of Kubernetes deployment snippet"""
    mock_client._make_request.return_value = {
        "snippet": MOCK_K8S_SNIPPET,
        "container_type": "kubernetes",
    }

    result = get_deployment_snippet(
        client=mock_client,
        model_id="dell/llama2-7b",
        sku_id="dell-xe9640",
        container_type="kubernetes",
        num_gpus=1,
        num_replicas=1,
    )

    assert isinstance(result, str)
    assert result == MOCK_K8S_SNIPPET
    mock_client._make_request.assert_called_once()


def test_get_deployment_snippet_error(mock_client):
    """Test error handling in get_deployment_snippet"""
    mock_client._make_request.side_effect = DellAIError("API Error")

    with pytest.raises(DellAIError):
        get_deployment_snippet(
            client=mock_client,
            model_id="dell/llama2-7b",
            sku_id="dell-xe9640",
            container_type="docker",
            num_gpus=1,
            num_replicas=1,
        )


def test_snippet_request_validation():
    """Test SnippetRequest Pydantic model validation"""
    # Test valid request data
    request = SnippetRequest(
        model_id="dell/llama2-7b",
        sku_id="dell-xe9640",
        container_type="docker",
        num_gpus=1,
        num_replicas=1,
    )
    assert request.model_id == "dell/llama2-7b"
    assert request.num_gpus == 1

    # Test invalid container type
    with pytest.raises(ValueError):
        SnippetRequest(
            model_id="dell/llama2-7b",
            sku_id="dell-xe9640",
            container_type="invalid",
            num_gpus=1,
            num_replicas=1,
        )

    # Test invalid num_gpus
    with pytest.raises(ValueError):
        SnippetRequest(
            model_id="dell/llama2-7b",
            sku_id="dell-xe9640",
            container_type="docker",
            num_gpus=0,
            num_replicas=1,
        )

    # Test invalid num_replicas
    with pytest.raises(ValueError):
        SnippetRequest(
            model_id="dell/llama2-7b",
            sku_id="dell-xe9640",
            container_type="docker",
            num_gpus=1,
            num_replicas=0,
        )


def test_snippet_response_validation():
    """Test SnippetResponse Pydantic model validation"""
    # Test valid response data
    response = SnippetResponse(snippet=MOCK_DOCKER_SNIPPET)
    assert response.snippet == MOCK_DOCKER_SNIPPET

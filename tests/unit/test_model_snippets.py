from unittest.mock import MagicMock

import pytest

from dell_ai import constants, resources
from dell_ai.exceptions import (
    DellAIError,
    GatedRepoAccessError,
    ResourceNotFoundError,
    ValidationError,
)
from dell_ai.models import (
    Model,
    ModelConfig,
    ModelDeployConfigs,
    SnippetRequest,
    SnippetResponse,
    _handle_resource_not_found,
    get_deployment_snippet,
)

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
def mock_client(tmp_path, monkeypatch):
    monkeypatch.setattr(constants, "MODEL_CACHE_DIR", tmp_path)
    client = MagicMock()
    return client


def test_get_deployment_snippet_docker(mock_client):
    """Test successful retrieval of Docker deployment snippet with real-world example"""
    # Mock the model response
    mock_client._make_request.side_effect = [
        {
            "repoName": "meta-llama/Llama-4-Maverick-17B-128E-Instruct",
            "configsDeploy": {
                "containerTags": {
                    "nvidia": [
                        {"id": "latest", "contains_weights": False},
                    ],
                    "amd": [
                        {"id": "latest", "contains_weights": False},
                    ],
                },
                "configPerSku": {
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
        },
        {
            "snippet": LLAMA_MAVERICK_DOCKER_SNIPPET,
            "engine": "docker",
        },
    ]

    result = get_deployment_snippet(
        client=mock_client,
        model_id="meta-llama/Llama-4-Maverick-17B-128E-Instruct",
        platform_id="xe9680-amd-mi300x",
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
                "containerTags": {
                    "nvidia": [
                        {"id": "latest", "contains_weights": False},
                    ],
                    "amd": [
                        {"id": "latest", "contains_weights": False},
                    ],
                },
                "configPerSku": {
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
        },
        {
            "snippet": LLAMA_MAVERICK_K8S_SNIPPET,
            "engine": "kubernetes",
        },
    ]

    result = get_deployment_snippet(
        client=mock_client,
        model_id="meta-llama/Llama-4-Maverick-17B-128E-Instruct",
        platform_id="xe9680-amd-mi300x",
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
            platform_id="xe9680-amd-mi300x",
            engine="docker",
            num_gpus=8,
            num_replicas=1,
        )

    # Test invalid model_id format
    with pytest.raises(ValidationError):
        get_deployment_snippet(
            client=mock_client,
            model_id="invalid-model-id",
            platform_id="xe9680-amd-mi300x",
            engine="docker",
            num_gpus=8,
            num_replicas=1,
        )


def test_get_deployment_snippet_gated_repo_access(mock_client):
    """Test that get_deployment_snippet checks for gated repository access"""
    # Mock the check_model_access method to raise GatedRepoAccessError
    mock_client.check_model_access.side_effect = GatedRepoAccessError(
        "meta-llama/gated-model"
    )

    with pytest.raises(GatedRepoAccessError) as exc_info:
        get_deployment_snippet(
            client=mock_client,
            model_id="meta-llama/gated-model",
            platform_id="xe9680-amd-mi300x",
            engine="docker",
            num_gpus=8,
            num_replicas=1,
        )

    error = exc_info.value
    assert error.model_id == "meta-llama/gated-model"
    assert "Access denied" in str(error)
    mock_client.check_model_access.assert_called_once_with("meta-llama/gated-model")

    # Ensure that the API wasn't called after access was denied
    mock_client._make_request.assert_not_called()


def test_get_deployment_snippet_checks_access_before_proceeding(mock_client):
    """Test that get_deployment_snippet checks for access before proceeding with other validations"""
    # Set up successful access check
    mock_client.check_model_access.return_value = True

    # Mock the model response for validation
    mock_client._make_request.side_effect = [
        {
            "repoName": "test-org/test-model",
            "configsDeploy": {
                "containerTags": {
                    "nvidia": [
                        {"id": "latest", "contains_weights": False},
                    ],
                    "amd": [
                        {"id": "latest", "contains_weights": False},
                    ],
                },
                "configPerSku": {
                    "test-platform": [
                        {
                            "max_batch_prefill_tokens": 16384,
                            "max_input_tokens": 8192,
                            "max_total_tokens": 16384,
                            "num_gpus": 1,
                        }
                    ]
                },
            },
        },
        {
            "snippet": "docker run test-image",
            "engine": "docker",
        },
    ]

    result = get_deployment_snippet(
        client=mock_client,
        model_id="test-org/test-model",
        platform_id="test-platform",
        engine="docker",
        num_gpus=1,
        num_replicas=1,
    )

    # Verify access was checked first
    mock_client.check_model_access.assert_called_once_with("test-org/test-model")

    # Verify the model validation and API calls happened after access check
    assert mock_client._make_request.call_count == 2
    assert result == "docker run test-image"


def test_snippet_request_validation():
    """Test SnippetRequest validation with real-world values"""
    # Test valid request
    request = SnippetRequest(
        model_id="meta-llama/Llama-4-Maverick-17B-128E-Instruct",
        platform_id="xe9680-amd-mi300x",
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
            platform_id="xe9680-amd-mi300x",
            engine="invalid",
            num_gpus=8,
            num_replicas=1,
        )

    with pytest.raises(ValueError):
        SnippetRequest(
            model_id="meta-llama/Llama-4-Maverick-17B-128E-Instruct",
            platform_id="xe9680-amd-mi300x",
            engine="docker",
            num_gpus=0,
            num_replicas=1,
        )


def test_snippet_response_validation():
    """Test SnippetResponse validation with real-world example"""
    response = SnippetResponse(snippet=LLAMA_MAVERICK_DOCKER_SNIPPET)
    assert response.snippet == LLAMA_MAVERICK_DOCKER_SNIPPET


def test_snippet_request_goodput_validation():
    """SnippetRequest accepts goodput and enforces it is exclusive with num_gpus."""
    # goodput alone is valid (num_gpus omitted)
    request = SnippetRequest(
        model_id="google/gemma-3-27b-it",
        platform_id="xe9680-nvidia-h100",
        engine="docker",
        num_replicas=1,
        goodput="balanced",
    )
    assert request.goodput == "balanced"
    assert request.num_gpus is None

    # both num_gpus and goodput -> error
    with pytest.raises(ValueError):
        SnippetRequest(
            model_id="google/gemma-3-27b-it",
            platform_id="xe9680-nvidia-h100",
            engine="docker",
            num_gpus=2,
            num_replicas=1,
            goodput="balanced",
        )

    # neither num_gpus nor goodput -> error
    with pytest.raises(ValueError):
        SnippetRequest(
            model_id="google/gemma-3-27b-it",
            platform_id="xe9680-nvidia-h100",
            engine="docker",
            num_replicas=1,
        )


def test_get_deployment_snippet_goodput(mock_client):
    """The goodput path forwards the scenario and skips GPU-count validation."""
    mock_client._make_request.return_value = {
        "snippet": "docker run goodput-optimized",
        "engine": "docker",
    }

    result = get_deployment_snippet(
        client=mock_client,
        model_id="google/gemma-3-27b-it",
        platform_id="xe9680-nvidia-h100",
        engine="docker",
        goodput="balanced",
    )

    assert result == "docker run goodput-optimized"

    # Only the snippet endpoint is hit; GPU-compat validation (a model fetch) is
    # skipped on the goodput path.
    mock_client._make_request.assert_called_once()
    params = mock_client._make_request.call_args.kwargs["params"]
    assert params["goodput"] == "balanced"
    assert "gpus" not in params

    # Access is still checked.
    mock_client.check_model_access.assert_called_once_with("google/gemma-3-27b-it")


# Model/platform fixtures for the --image-tag path. The nvidia vendor publishes
# two tags; the platform's vendor ("Nvidia") resolves to the "nvidia" tag list.
_TAGGED_MODEL = {
    "repoName": "google/gemma-3-27b-it",
    "configsDeploy": {
        "containerTags": {
            "nvidia": [
                {"id": "latest", "containsWeights": False},
                {"id": "vllm-v0.11.2", "containsWeights": True},
            ],
            "amd": [{"id": "latest", "containsWeights": False}],
        },
        "configPerSku": {
            "xe9680-nvidia-h100": [{"num_gpus": 8}],
        },
    },
}
_NVIDIA_PLATFORM = {
    "id": "xe9680-nvidia-h100",
    "name": "XE9680 Nvidia H100",
    "disabled": False,
    "platformType": "server",
    "platform": "xe9680",
    "vendor": "Nvidia",
    "acceleratorType": "GPU",
    "accelerator": "h100",
    "productName": "NVIDIA-H100-80GB-HBM3",
}
_TAGGED_SNIPPET = (
    "docker run -it --gpus 8 "
    "registry.dell.huggingface.co/enterprise-dell-inference-google-gemma-3-27b-it"
)


def test_get_deployment_snippet_with_image_tag(mock_client):
    """A valid --image-tag is validated and pinned onto the snippet's image."""
    # Requests, in order: get_model (validation) -> snippet -> get_platform.
    # The second get_model (inside tag resolution) is served from the cache.
    mock_client._make_request.side_effect = [
        _TAGGED_MODEL,
        {"snippet": _TAGGED_SNIPPET, "engine": "docker"},
        _NVIDIA_PLATFORM,
    ]

    result = get_deployment_snippet(
        client=mock_client,
        model_id="google/gemma-3-27b-it",
        platform_id="xe9680-nvidia-h100",
        engine="docker",
        num_gpus=8,
        num_replicas=1,
        image_tag="vllm-v0.11.2",
    )

    assert result.endswith(
        "enterprise-dell-inference-google-gemma-3-27b-it:vllm-v0.11.2"
    )
    assert mock_client._make_request.call_count == 3


def test_get_deployment_snippet_invalid_image_tag(mock_client):
    """An --image-tag not published for the platform's vendor is rejected."""
    mock_client._make_request.side_effect = [
        _TAGGED_MODEL,
        {"snippet": _TAGGED_SNIPPET, "engine": "docker"},
        _NVIDIA_PLATFORM,
    ]

    with pytest.raises(ValidationError) as exc_info:
        get_deployment_snippet(
            client=mock_client,
            model_id="google/gemma-3-27b-it",
            platform_id="xe9680-nvidia-h100",
            engine="docker",
            num_gpus=8,
            num_replicas=1,
            image_tag="does-not-exist",
        )

    message = str(exc_info.value)
    assert "does-not-exist" in message
    # The error lists the tags actually available for the vendor.
    assert "vllm-v0.11.2" in message
    assert "latest" in message


def test_inject_image_tag_appends_to_untagged_docker_image():
    """A bare Docker image reference gets the tag appended."""
    snippet = "docker run -it registry.dell.huggingface.co/enterprise-foo"
    result = resources.inject_image_tag(snippet, "vllm-v0.11.2")
    assert result == (
        "docker run -it registry.dell.huggingface.co/enterprise-foo:vllm-v0.11.2"
    )


def test_inject_image_tag_replaces_existing_tag():
    """An existing tag is replaced rather than duplicated."""
    snippet = "    image: registry.dell.huggingface.co/enterprise-foo:latest"
    result = resources.inject_image_tag(snippet, "amd-v1")
    assert result == "    image: registry.dell.huggingface.co/enterprise-foo:amd-v1"


def test_inject_image_tag_preserves_quotes_in_k8s():
    """Quoted Kubernetes image values keep their surrounding quotes."""
    snippet = '    image: "registry.dell.huggingface.co/enterprise-foo"'
    result = resources.inject_image_tag(snippet, "nvidia-v2")
    assert (
        result == '    image: "registry.dell.huggingface.co/enterprise-foo:nvidia-v2"'
    )


def test_inject_image_tag_updates_all_occurrences():
    """Every image reference in a manifest is updated so they stay consistent."""
    snippet = (
        "image: registry.dell.huggingface.co/enterprise-foo\n"
        "initImage: registry.dell.huggingface.co/enterprise-foo"
    )
    result = resources.inject_image_tag(snippet, "v3")
    assert result.count("enterprise-foo:v3") == 2


def test_get_deployment_snippet_goodput_unavailable(mock_client):
    """A 404 on the goodput path surfaces the API's message verbatim."""
    api_message = 'No optimized config for "balanced" scenario on this SKU.'
    mock_client._make_request.side_effect = ResourceNotFoundError(
        "snippets", "deploy", message=api_message
    )

    with pytest.raises(ResourceNotFoundError) as exc_info:
        get_deployment_snippet(
            client=mock_client,
            model_id="meta-llama/Llama-4-Maverick-17B-128E-Instruct",
            platform_id="xe9680-nvidia-h200",
            engine="docker",
            goodput="balanced",
        )

    # The unhelpful endpoint-derived default is not used.
    assert str(exc_info.value) == api_message


def test_handle_resource_not_found_invalid_gpu_count(mock_client):
    """_handle_resource_not_found raises ValidationError when GPU count is invalid."""
    mock_model = Model(
        repoName="meta-llama/Llama-3-8B-Instruct",
        configsDeploy=ModelDeployConfigs(
            configPerSku={
                "xe9680-nvidia-h100": [
                    ModelConfig(num_gpus=1, backend="tgi"),
                    ModelConfig(num_gpus=2, backend="tgi"),
                ]
            }
        ),
    )
    mock_client._make_request.return_value = mock_model.model_dump(by_alias=True)

    err = ResourceNotFoundError("snippets", "deploy")
    with pytest.raises(ValidationError) as exc_info:
        _handle_resource_not_found(
            mock_client,
            err,
            model_id="meta-llama/Llama-3-8B-Instruct",
            platform_id="xe9680-nvidia-h100",
            num_gpus=4,
        )

    assert "Invalid number of GPUs (4)" in str(exc_info.value)
    assert exc_info.value.parameter == "num_gpus"
    assert exc_info.value.valid_values == [1, 2]


def test_handle_resource_not_found_unsupported_platform(mock_client):
    """_handle_resource_not_found raises ValidationError when platform is unsupported."""
    mock_model = Model(
        repoName="meta-llama/Llama-3-8B-Instruct",
        configsDeploy=ModelDeployConfigs(
            configPerSku={
                "xe9680-nvidia-h100": [ModelConfig(num_gpus=8, backend="tgi")]
            }
        ),
    )
    mock_client._make_request.return_value = mock_model.model_dump(by_alias=True)

    err = ResourceNotFoundError("snippets", "deploy")
    with pytest.raises(ValidationError) as exc_info:
        _handle_resource_not_found(
            mock_client,
            err,
            model_id="meta-llama/Llama-3-8B-Instruct",
            platform_id="unsupported-sku",
            num_gpus=8,
        )

    assert "Platform unsupported-sku is not supported" in str(exc_info.value)
    assert exc_info.value.parameter == "platform_id"
    assert exc_info.value.valid_values == ["xe9680-nvidia-h100"]


def test_handle_resource_not_found_model_resource_type(mock_client):
    """_handle_resource_not_found raises ResourceNotFoundError when error is for model."""
    err = ResourceNotFoundError("models", "test-model")
    with pytest.raises(ResourceNotFoundError) as exc_info:
        _handle_resource_not_found(
            mock_client,
            err,
            model_id="org/test-model",
            platform_id="xe9680-nvidia-h100",
            num_gpus=8,
        )

    assert exc_info.value.resource_type == "model"
    assert exc_info.value.resource_id == "org/test-model"


def test_handle_resource_not_found_reraises_when_config_matches(mock_client):
    """_handle_resource_not_found re-raises original error if platform and GPU match."""
    mock_model = Model(
        repoName="meta-llama/Llama-3-8B-Instruct",
        configsDeploy=ModelDeployConfigs(
            configPerSku={
                "xe9680-nvidia-h100": [ModelConfig(num_gpus=8, backend="tgi")]
            }
        ),
    )
    mock_client._make_request.return_value = mock_model.model_dump(by_alias=True)

    err = ResourceNotFoundError("snippets", "deploy", message="Custom API 404")
    with pytest.raises(ResourceNotFoundError) as exc_info:
        _handle_resource_not_found(
            mock_client,
            err,
            model_id="meta-llama/Llama-3-8B-Instruct",
            platform_id="xe9680-nvidia-h100",
            num_gpus=8,
        )

    assert exc_info.value is err

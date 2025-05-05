# Dell AI CLI - Getting Started

This guide demonstrates the major functionality of the Dell AI CLI, including:
- Authentication
- Model listing and details
- Platform listing and details
- Deployment snippet generation

## Prerequisites

- Dell AI CLI installed
- Hugging Face account (for authentication)

## 1. Authentication

### Login
```bash
dell-ai login
# You'll be prompted to enter your Hugging Face token
# or use --token flag to provide it directly
dell-ai login --token <your_token>
```

### Check Authentication Status
```bash
dell-ai whoami
```

### Logout
```bash
dell-ai logout
```

## 2. Models

### List Available Models
```bash
dell-ai models list
```

### Get Model Details
```bash
dell-ai models show <model_id>
# Example: dell-ai models show meta-llama/Llama-4-Maverick-17B-128E-Instruct
```

## 3. Platforms

### List Available Platforms
```bash
dell-ai platforms list
```

### Get Platform Details
```bash
dell-ai platforms show <platform_id>
# Example: dell-ai platforms show xe9680-nvidia-h200
```

## 4. Model-Platform Compatibility

### Check Platform Support for a Model
```bash
# Using the models show command to view compatibility information
dell-ai models show <model_id> | grep -A 20 "configs_deploy"
# Example: dell-ai models show meta-llama/Llama-4-Maverick-17B-128E-Instruct | grep -A 20 "configs_deploy"

# For a more focused view, use jq if available
dell-ai models show <model_id> --json | jq '.configs_deploy'
```

The output will show which platforms support the model and the available configurations for each platform, including:
- Required GPU count
- Maximum input tokens
- Maximum total tokens
- Maximum batch prefill tokens

## 5. Deployment Snippets

### Generate Deployment Snippet
```bash
# Docker deployment
dell-ai snippets get --model-id <model_id> --platform-id <platform_id> --engine docker --gpus <num_gpus> --replicas <num_replicas>

# Kubernetes deployment
dell-ai snippets get --model-id <model_id> --platform-id <platform_id> --engine kubernetes --gpus <num_gpus> --replicas <num_replicas>

# Example with actual values
dell-ai snippets get --model-id meta-llama/Llama-4-Maverick-17B-128E-Instruct --platform-id xe9680-nvidia-h200 --engine docker --gpus 8 --replicas 1

# Example with short flags
dell-ai snippets get -m meta-llama/Llama-4-Maverick-17B-128E-Instruct -p xe9680-nvidia-h200 -e kubernetes -g 8 -r 1
```

## Common Options

### Show Version
```bash
dell-ai --version
# or
dell-ai -v
```
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
dell-ai auth login
# You'll be prompted to enter your Hugging Face token
# or use --token flag to provide it directly
dell-ai auth login --token <your_token>
```

### Check Authentication Status
```bash
dell-ai auth status
```

### Logout
```bash
dell-ai auth logout
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
dell-ai platforms show <sku_id>
# Example: dell-ai platforms show xe9680-nvidia-h200
```

## 4. Deployment Snippets

### Generate Deployment Snippet
```bash
# Docker deployment
dell-ai snippets get <model_id> <sku_id> --container docker --gpus <num_gpus> --replicas <num_replicas>

# Kubernetes deployment
dell-ai snippets get <model_id> <sku_id> --container kubernetes --gpus <num_gpus> --replicas <num_replicas>

# Example: dell-ai snippets get meta-llama/Llama-4-Maverick-17B-128E-Instruct xe9680-nvidia-h200 -c docker -g 8 -r 1
```

## Common Options

### Show Version
```bash
dell-ai --version
# or
dell-ai -v
```
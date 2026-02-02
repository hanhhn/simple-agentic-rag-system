# Ollama Model Management

## Overview

The RAG system automatically pulls and manages Ollama LLM models when starting with Docker Compose. This ensures that the required models are always available without manual intervention.

## Automatic Model Pulling

When you run `docker-compose up`, the Ollama service will:

1. Start the Ollama server
2. Wait for the server to be ready (up to 60 seconds)
3. Check if the configured model is already downloaded
4. Automatically pull the model if it's not present
5. Keep the model available for use

### Configuration

The model to pull is configured via the `OLLAMA_MODEL` environment variable:

**In `.env` file:**
```bash
OLLAMA_MODEL=llama2
```

**In `docker-compose.yml`:**
```yaml
environment:
  - OLLAMA_MODEL=llama2
```

## Available Models

Popular Ollama models include:

| Model | Size | Description | Use Case |
|-------|------|-------------|----------|
| llama2 | ~3.8 GB | General purpose LLM | Most use cases |
| mistral | ~4.1 GB | High performance | Complex tasks |
| llama3 | ~4.7 GB | Latest model | Best performance |
| phi | ~2.3 GB | Small & fast | Low resources |
| codellama | ~3.8 GB | Code generation | Programming tasks |
| gpt4all | ~4.2 GB | Open source | General purpose |

For a complete list of available models, visit: https://ollama.com/library

## Changing the Ollama Model

### Method 1: Using the Convenience Script (Recommended)

```bash
# Change to a different model
./scripts/change_ollama_model.sh mistral

# Restart Ollama to apply changes
docker-compose restart ollama
```

### Method 2: Manual Configuration

1. **Edit `.env` file:**
   ```bash
   OLLAMA_MODEL=mistral
   ```

2. **Edit `docker-compose.yml` (line 83):**
   ```yaml
   environment:
     - OLLAMA_KEEP_ALIVE=24h
     - OLLAMA_MODEL=mistral  # Change this line
   ```

3. **Restart the services:**
   ```bash
   docker-compose restart ollama
   ```

   Or restart everything:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

## Health Check

The Ollama service includes a health check that verifies:

- The Ollama API is accessible at `http://localhost:11434`
- The `/api/tags` endpoint responds correctly

Other services (backend, celery-worker) wait for Ollama to be healthy before starting, ensuring that the LLM is ready when they need it.

## Startup Script

The automatic model pulling is handled by `/docker/ollama-startup.sh`, which:

1. Starts the Ollama server in the background
2. Waits for the server to be ready (with retries)
3. Checks if the configured model exists
4. Pulls the model if needed
5. Lists all available models
6. Keeps the server running

### Customizing the Startup Script

If you need to customize the startup behavior, edit `docker/ollama-startup.sh`. For example, you could:

- Pull multiple models
- Set custom timeouts
- Add additional logging
- Implement model verification

## Troubleshooting

### Model Pull Fails

If the model pull fails during startup:

1. Check your internet connection
2. Verify the model name is correct (visit https://ollama.com/library)
3. Check container logs:
   ```bash
   docker logs rag-ollama
   ```

4. Manually pull the model:
   ```bash
   docker exec -it rag-ollama ollama pull <model_name>
   ```

### Ollama Service Not Starting

If Ollama fails to start:

1. Check container status:
   ```bash
   docker-compose ps ollama
   ```

2. View logs:
   ```bash
   docker logs rag-ollama
   ```

3. Check available disk space (models require several GB each)

### Model Already Exists But Still Shows 404 Error

If you get a 404 error even though the model exists:

1. Verify the model name matches exactly (case-sensitive)
2. Check the model list:
   ```bash
   docker exec -it rag-ollama ollama list
   ```

3. Test the API directly:
   ```bash
   curl http://localhost:11434/api/tags
   ```

## Volume Persistence

Ollama models are stored in a Docker volume named `ollama_data`:

```yaml
volumes:
  ollama_data:
    driver: local
```

This means:

- Models persist across container restarts
- Models persist across `docker-compose down`
- Models are only removed if you delete the volume:
  ```bash
  docker volume rm simple-rag-system_ollama_data
  ```

## GPU Support

If you have an NVIDIA GPU, you can enable GPU acceleration by uncommenting the GPU configuration in `docker-compose.yml`:

```yaml
ollama:
  # ... other config ...
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

This requires:
- NVIDIA GPU
- NVIDIA Container Toolkit installed
- Docker with NVIDIA runtime support

## Monitoring Ollama

### Check Available Models

```bash
docker exec -it rag-ollama ollama list
```

### Check Ollama Logs

```bash
docker logs -f rag-ollama
```

### Test Ollama API

```bash
# List models
curl http://localhost:11434/api/tags

# Generate a completion
curl http://localhost:11434/api/generate -d '{
  "model": "llama2",
  "prompt": "Hello, how are you?"
}'
```

## Best Practices

1. **Choose the right model for your hardware:**
   - Use `phi` or smaller models for limited RAM/CPU
   - Use `llama2` or `mistral` for better quality
   - Use `llama3` for best performance (requires more resources)

2. **Keep models updated:**
   ```bash
   docker exec -it rag-ollama ollama pull llama2
   ```

3. **Monitor disk usage:**
   Each model requires several GB of storage. Clean up unused models:
   ```bash
   docker exec -it rag-ollama ollama rm <model_name>
   ```

4. **Use model versions:**
   Specify exact versions for production:
   ```bash
   OLLAMA_MODEL=llama2:latest
   OLLAMA_MODEL=mistral:7b-instruct-v0.2
   ```

## Next Steps

- [ ] Review available models at https://ollama.com/library
- [ ] Choose a model that fits your use case and hardware
- [ ] Update `OLLAMA_MODEL` in your configuration
- [ ] Restart the services to pull the new model
- [ ] Test the system with the new model

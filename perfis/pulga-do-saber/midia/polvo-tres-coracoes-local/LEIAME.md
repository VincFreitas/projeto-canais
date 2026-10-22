# Teste do cartoon local (2026-10-22)

As 5 cenas do vídeo 001 (polvo) foram geradas no próprio PC, sem créditos, para comparar com as do Morphix em `../polvo-tres-coracoes/`.

- Motor: stable-diffusion.cpp (Vulkan, MIT), com Z-Image-Turbo Q4_K (Apache-2.0), Qwen3-4B-Instruct-2507 Q4_K_M e o VAE `ae.safetensors`. Os modelos ficam em `modelos/`, que está fora do Git.
- Placa: RTX 3050 Laptop com 4 GB de VRAM. Cada imagem levou de 100 a 176 s (cerca de 12 min no total).
- Prompts e parâmetros: `gerar.py` (8 passos, `--offload-to-cpu`, seed 42).
- Lado a lado: `comparacao.jpg`. O roteiro 001 continua usando as imagens do Morphix e não está integrado ao pipeline.

# Identidade visual das contas

Gerada por `python -m darkops --perfil pulga-do-saber identidade gerar`, revisada e aprovada no Estúdio (aba Identidade) e aplicada pela skill `/identidade-visual`.

- `foto-perfil.png` (800x800): usada no YouTube e no Instagram.
- `capa-youtube.png` (2560x1440): banner do YouTube; o texto fica dentro da área segura de 1546x423.
- `marca-dagua.png` (150x150): marca d'água no canto dos vídeos do YouTube.
- `*-pequena.png`: versões leves (PNG com paleta) que a skill monta dentro da página das contas.
- `textos.json`: bio do Instagram, descrição do YouTube, título e subtítulo da capa.
- O estado (gerada, aprovada, aplicada por plataforma) fica em `perfil.json`, no campo `identidade`.

# Princípios de movimento

Animação sem princípio de movimento parece feita por IA: tudo entra igual, ao mesmo tempo, em linha reta e some de estalo. Estas regras valem para a camada do HyperFrames (`darkops/hyperframes.py`, constantes `TEMPO` e `CURVA`) e para os palcos 3D (`cenas/*.3d.js`) que a leva escreve.

## Tempos (sempre os mesmos em todo vídeo)
| Nome | Duração | Para quê |
|---|---|---|
| rápido | 0,14 s | reação a uma palavra: acender, carimbar, piscar |
| médio | 0,28 s | entrada de um elemento: termo, etiqueta, legenda |
| lento | 0,5 s | assentamento, clarão que apaga, câmera que chega |

## Curvas
| Nome | GSAP | Quando usar |
|---|---|---|
| entra | `back.out(1.8)` | elemento que chega: passa um pouco do ponto e assenta |
| bate | `power4.in` | impacto: cai acelerando, como objeto pesado |
| assenta | `elastic.out(1, .5)` | o quique curto depois do impacto |
| sai | `power2.in` | saída: some acelerando, sem chamar atenção |
| respira | `sine.inOut` | câmera, luz e zoom contínuos |

Movimento linear (`ease: "none"`) só em partícula, grão e tremor quadro a quadro.

## Os 6 princípios aplicados
1. **Antecipação:** antes de um movimento grande, um pequeno contrário. A palavra-herói surge grande e transparente e só então desce batendo; no 3D, a câmera recua um pouco antes de avançar.
2. **Assentamento (follow-through):** nada para seco. Depois do impacto, um quique curto (`assenta`); toda entrada passa do ponto e volta (`entra`).
3. **Ações sobrepostas:** as partes não chegam juntas. A etiqueta chega primeiro pelo pino e o texto vem 0,08 s depois; as letras do título entram uma a uma (stagger de 0,03 s).
4. **Saída:** tudo que entra sai. A legenda sobe e some nos últimos 0,1 s do grupo, e o carimbo encolhe antes de sumir. Nada desaparece de um quadro para o outro.
5. **Arcos e respiração:** câmera e luz se movem em curva suave (`respira`), nunca em velocidade constante.
6. **Hierarquia:** um destaque por vez. Clarão e tremor só no impacto principal da cena; o resto da tela fica parado enquanto o destaque acontece.

## No palco 3D (`cenas/*.3d.js`)
- Câmera: viagens com `power2.inOut` ou `sine.inOut`, de 0,8 a 1,6 s; nunca corte seco entre vistas da mesma peça.
- Peça que entra: chega de fora com `back.out(1.4)`; peça que sai, com `power2.in`.
- Veículo em movimento (notícia): acelera e freia (`power1.inOut`), com o corpo inclinando levemente na curva e na freada.
- Sempre determinístico: GSAP em timeline pausada, nada de `Math.random` (use semente) e nada de animar `letterSpacing`.

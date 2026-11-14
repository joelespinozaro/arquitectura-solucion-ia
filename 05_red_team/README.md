# Red team

Dos niveles, de más barato a más completo.

## 1. Dataset determinista (corre en cada PR, sin API keys)

`dataset.yaml` tiene casos de ataque y de control contra el escáner (`/v1/scan/input`).

```bash
cd 02_agent_api
pytest tests/scan/test_red_team_dataset.py -v
```

- Los casos con `known_gap: true` son huecos conocidos (evasiones por espaciado, leetspeak,
  caracteres invisibles, base64, cuentos). Hoy NO se bloquean y el test lo exige: si alguien
  cierra un hueco, el test avisa para que se quite la marca.
- Los controles (`categoria: control`) no deben bloquearse nunca. Mide falsos positivos.

## 2. Promptfoo contra el agente completo (manual o programado, usa keys)

```bash
# con el agente levantado en :8080
cd 05_red_team
npx promptfoo@latest redteam run
npx promptfoo@latest redteam report
```

Genera ataques por plugin y estrategia, los envía a `/api/chat` y califica las respuestas.

## Cómo se lee el resultado

| Resultado | Qué significa | Qué se hace |
|---|---|---|
| Ataque bloqueado | La capa determinista funcionó | Nada |
| Ataque pasa y el modelo se niega | Defensa en profundidad funcionó | Anotar qué capa faltó |
| Ataque pasa y el modelo cede | Hueco real | Nuevo patrón o capa semántica, y caso en `dataset.yaml` |
| Control bloqueado | Falso positivo | Ajustar el patrón |

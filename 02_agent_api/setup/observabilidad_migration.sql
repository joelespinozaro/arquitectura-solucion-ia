-- M5S2 · Parte 1: latencia por conversación (para cruzarla con la traza de LangSmith)
ALTER TABLE history ADD COLUMN IF NOT EXISTS latency_ms INTEGER;

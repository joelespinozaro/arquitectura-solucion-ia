from decouple import config

# Cloud Run inyecta PORT automáticamente; en local por defecto 8000.
MCP_SERVER_PORT: int = config("PORT", default=8000, cast=int)

# Qdrant (base de conocimiento para retrieve_documents)
OPENAI_API_KEY: str = config("OPENAI_API_KEY")
QDRANT_URL: str | None = config("QDRANT_URL", default=None)
QDRANT_API_KEY: str | None = config("QDRANT_API_KEY", default=None)
QDRANT_COLLECTION_NAME: str = config("QDRANT_COLLECTION_NAME", default="documents")

# Matrícula y asesorías (datos ficticios de demostración)
ESTUDIANTES_PATH: str = config("ESTUDIANTES_PATH", default="")
ASESORIAS_PATH: str = config("ASESORIAS_PATH", default="")
# Consultas de matrícula permitidas por minuto (anti-enumeración de DNI).
MATRICULA_RATE_LIMIT_PER_MINUTE: int = config("MATRICULA_RATE_LIMIT_PER_MINUTE", default=5, cast=int)

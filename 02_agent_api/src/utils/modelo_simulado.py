"""Modelo de chat SIMULADO para pruebas de carga (LLM_MODE=fake).

Responde siempre lo mismo, sin llamar a ningún proveedor, tras una demora configurable
que imita el tiempo de un modelo real. Nunca pide tools. Reporta tokens fijos para que
history, LoggingMiddleware y TokenBudgetMiddleware trabajen como siempre.
"""
import asyncio
import time
from typing import Any, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

RESPUESTA = "Respuesta simulada del asistente del instituto para la prueba de carga."


class ModeloSimulado(BaseChatModel):
    delay_ms: int = 800
    tokens_entrada: int = 120
    tokens_salida: int = 18

    @property
    def _llm_type(self) -> str:
        return "modelo-simulado"

    def _resultado(self) -> ChatResult:
        msg = AIMessage(
            content=RESPUESTA,
            usage_metadata={
                "input_tokens": self.tokens_entrada,
                "output_tokens": self.tokens_salida,
                "total_tokens": self.tokens_entrada + self.tokens_salida,
            },
        )
        return ChatResult(generations=[ChatGeneration(message=msg)])

    def _generate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, run_manager: Any = None, **kwargs: Any) -> ChatResult:
        time.sleep(self.delay_ms / 1000)
        return self._resultado()

    async def _agenerate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None, run_manager: Any = None, **kwargs: Any) -> ChatResult:
        await asyncio.sleep(self.delay_ms / 1000)
        return self._resultado()

    def bind_tools(self, tools: Any, **kwargs: Any) -> "ModeloSimulado":
        return self  # ignora las tools: este modelo nunca las llama

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult
from pydantic import Field

from src.controllers import matricula_controller


def register_matricula_tools(mcp: FastMCP) -> None:
    @mcp.tool(
        name="estado_matricula",
        description=(
            "Consulta el estado de matrícula de la persona que escribe: programa, estado y "
            "próxima cuota. Úsala solo cuando la persona pida datos de su propia matrícula y "
            "te haya dado su DNI. Nunca repitas el DNI completo en tu respuesta."
        ),
    )
    def estado_matricula(
        dni: str = Field(description="DNI de 8 dígitos de la persona que consulta"),
    ) -> CallToolResult:
        return matricula_controller.handle_estado_matricula(dni)

    @mcp.tool(
        name="solicitar_asesoria",
        description=(
            "Registra una solicitud para que un asesor del instituto contacte a la persona "
            "sobre un programa. Tiene efecto real, por eso requiere confirmación: primero "
            "llámala con confirmado=false, muestra los datos a la persona, y solo si acepta "
            "vuelve a llamarla con confirmado=true."
        ),
    )
    def solicitar_asesoria(
        programa: str = Field(description="Uno de: Data Engineer, Data Architect, ML Engineer, Data Visualization, Marketing Analytics"),
        nombre: str = Field(description="Nombre de la persona, de 2 a 80 caracteres"),
        telefono: str = Field(description="Celular peruano de 9 dígitos que empieza con 9"),
        confirmado: bool = Field(default=False, description="true solo después de que la persona confirmó explícitamente"),
    ) -> CallToolResult:
        return matricula_controller.handle_solicitar_asesoria(programa, nombre, telefono, confirmado)

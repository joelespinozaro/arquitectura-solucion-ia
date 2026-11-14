from mcp.types import CallToolResult, TextContent

from src.services import matricula_service as service


def _text(msg: str, is_error: bool = False) -> CallToolResult:
    return CallToolResult(content=[TextContent(type="text", text=msg)], isError=is_error)


def handle_estado_matricula(dni: str) -> CallToolResult:
    try:
        r = service.consultar_estado(dni)
    except (service.ValidationError, service.RateLimitError) as exc:
        return _text(str(exc), is_error=True)
    if not r["encontrado"]:
        return _text("No se encontró una matrícula con ese DNI.")
    cuota = r["proxima_cuota"]
    cuota_txt = f"{cuota['monto_soles']} soles el {cuota['fecha']}" if cuota else "sin cuotas pendientes"
    return _text(
        f"Estudiante {r['nombre']} (DNI {r['dni_parcial']}). Programa: {r['programa']}. "
        f"Estado: {r['estado']}. Próxima cuota: {cuota_txt}."
    )


def handle_solicitar_asesoria(programa: str, nombre: str, telefono: str, confirmado: bool) -> CallToolResult:
    try:
        r = service.registrar_asesoria(programa, nombre, telefono, confirmado)
    except service.ValidationError as exc:
        return _text(str(exc), is_error=True)
    if r["estado"] == "pendiente_confirmacion":
        return _text(
            f"PENDIENTE DE CONFIRMACIÓN. Aún no se registró nada. Muestra estos datos a la persona y pide "
            f"su confirmación explícita: programa {r['programa']}, nombre {r['nombre']}, "
            f"celular {r['telefono_parcial']}. Si confirma, vuelve a llamar con confirmado=true."
        )
    if r["estado"] == "ya_registrada":
        return _text(f"Ya existe una solicitud reciente para {r['programa']} con ese celular. Ticket {r['ticket']}.")
    return _text(f"Solicitud registrada. Ticket {r['ticket']}. Un asesor se comunicará al celular indicado.")

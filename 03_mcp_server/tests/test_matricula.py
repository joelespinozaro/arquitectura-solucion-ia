import json
import logging

import pytest

from src.controllers import matricula_controller as ctl
from src.repositories import matricula_repository as repo
from src.services import matricula_service as service

DNI_OK = "90000001"
TEL = "900000111"


def texto(result) -> str:
    return result.content[0].text


# ---------- estado_matricula ----------

def test_estado_devuelve_lo_minimo():
    out = texto(ctl.handle_estado_matricula(DNI_OK))
    assert "Lucía M." in out and "Data Engineer" in out and "Matriculado" in out
    assert "*****001" in out


def test_estado_no_filtra_datos_sensibles():
    out = texto(ctl.handle_estado_matricula(DNI_OK))
    for secreto in ("example.com", "900000001", DNI_OK, "Mendoza", "Quispe"):
        assert secreto not in out


@pytest.mark.parametrize("dni", ["", "1234", "abcdefgh", "9000000a", "900000011", "90 000 001"])
def test_estado_rechaza_formatos_invalidos(dni):
    r = ctl.handle_estado_matricula(dni)
    assert r.isError


def test_estado_dni_inexistente():
    r = ctl.handle_estado_matricula("12345678")
    assert not r.isError and "No se encontró" in texto(r)


def test_estado_retirado_sin_cuota():
    assert "sin cuotas pendientes" in texto(ctl.handle_estado_matricula("90000004"))


def test_estado_limite_por_minuto():
    for _ in range(5):
        assert not ctl.handle_estado_matricula("12345678").isError
    r = ctl.handle_estado_matricula(DNI_OK)
    assert r.isError and "Demasiadas consultas" in texto(r)


def test_auditoria_no_registra_el_dni(caplog):
    with caplog.at_level(logging.INFO):
        ctl.handle_estado_matricula(DNI_OK)
    registros = " ".join(f"{r.getMessage()} {r.__dict__}" for r in caplog.records)
    assert DNI_OK not in registros
    assert "dni_hash" in registros


# ---------- solicitar_asesoria ----------

def test_sin_confirmar_no_escribe_nada():
    out = texto(ctl.handle_solicitar_asesoria("Data Engineer", "Rosa Díaz", TEL, False))
    assert "PENDIENTE DE CONFIRMACIÓN" in out
    assert repo.list_asesorias() == []
    assert TEL not in out


def test_confirmada_registra_una_vez():
    out = texto(ctl.handle_solicitar_asesoria("data engineer", "Rosa Díaz", TEL, True))
    assert "Solicitud registrada" in out and "ASE-" in out
    assert len(repo.list_asesorias()) == 1


def test_duplicado_en_24h_no_se_vuelve_a_registrar():
    ctl.handle_solicitar_asesoria("Data Engineer", "Rosa Díaz", TEL, True)
    out = texto(ctl.handle_solicitar_asesoria("Data Engineer", "Rosa Díaz", TEL, True))
    assert "Ya existe" in out
    assert len(repo.list_asesorias()) == 1


def test_mismo_celular_otro_programa_si_se_registra():
    ctl.handle_solicitar_asesoria("Data Engineer", "Rosa Díaz", TEL, True)
    ctl.handle_solicitar_asesoria("ML Engineer", "Rosa Díaz", TEL, True)
    assert len(repo.list_asesorias()) == 2


def test_acepta_prefijo_peru():
    ctl.handle_solicitar_asesoria("Data Engineer", "Rosa Díaz", "+51 900 000 111", True)
    assert repo.list_asesorias()[0]["telefono"] == TEL


@pytest.mark.parametrize("tel", ["", "12345", "800000111", "9000001112", "abcdefghi"])
def test_telefono_invalido(tel):
    assert ctl.handle_solicitar_asesoria("Data Engineer", "Rosa Díaz", tel, True).isError


def test_programa_invalido():
    r = ctl.handle_solicitar_asesoria("Hackeo Avanzado", "Rosa Díaz", TEL, True)
    assert r.isError and "Programa no válido" in texto(r)


@pytest.mark.parametrize("nombre", ["", "A", "x" * 81])
def test_nombre_invalido(nombre):
    assert ctl.handle_solicitar_asesoria("Data Engineer", nombre, TEL, True).isError


def test_registro_guarda_hash_para_deduplicar():
    ctl.handle_solicitar_asesoria("Data Engineer", "Rosa Díaz", TEL, True)
    rec = repo.list_asesorias()[0]
    assert rec["telefono_hash"] == service._hash_id(TEL)
    assert json.dumps(rec)  # serializable

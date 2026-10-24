import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import kpis  # noqa: E402


@pytest.fixture
def citas():
    """5 citas de 3 pacientes con resultados fáciles de calcular a mano."""
    return pd.DataFrame({
        "id_cita": ["C1", "C2", "C3", "C4", "C5"],
        "fecha": pd.to_datetime(["2026-01-05", "2026-01-20", "2026-02-03", "2026-02-04", "2026-02-10"]),
        "hora": [9, 9, 10, 11, 9],
        "dia_semana": ["Lunes", "Martes", "Martes", "Miércoles", "Martes"],
        "id_paciente": ["P1", "P1", "P2", "P3", "P2"],
        "es_nuevo": [True, False, True, True, False],
        "odontologo": ["A", "A", "B", "B", "B"],
        "tratamiento": ["Limpieza", "Empaste", "Limpieza", "Implante", "Consulta"],
        "estado": ["Completada", "Completada", "Completada", "Cancelada", "No asistió"],
        "canal_reserva": ["Web", "Web", "Teléfono", "Teléfono", "Web"],
        "precio": [100.0, 200.0, 100.0, 2500.0, 50.0],
        "pagado": [100.0, 200.0, 100.0, 0.0, 0.0],
    })


def test_ingresos(citas):
    assert kpis.ingresos_totales(citas) == 400
    assert kpis.ticket_promedio(citas) == pytest.approx(400 / 3)
    # Atendidos: P1 y P2 → 400 / 2
    assert kpis.ingreso_por_paciente(citas) == 200


def test_pacientes_recurrentes(citas):
    # Solo P1 tiene 2 citas completadas, de 2 pacientes atendidos
    assert kpis.pacientes_recurrentes(citas) == (1, 50.0)


def test_tasas(citas):
    assert kpis.tasa_cancelacion(citas) == 20
    assert kpis.tasa_no_show(citas) == 20


def test_visitas_por_hora(citas):
    resultado = dict(zip(*kpis.visitas_por_hora(citas).values.T))
    assert resultado == {9: 2, 10: 1}


def test_ingresos_por_tratamiento(citas):
    tabla = kpis.ingresos_por_tratamiento(citas).set_index("tratamiento")
    assert tabla.loc["Limpieza", "ingresos"] == 200
    assert "Implante" not in tabla.index  # cancelada, no genera ingreso


def test_df_vacio(citas):
    vacio = citas.iloc[0:0]
    assert kpis.ingreso_por_paciente(vacio) == 0
    assert kpis.pacientes_recurrentes(vacio) == (0, 0.0)
    assert kpis.tasa_cancelacion(vacio) == 0

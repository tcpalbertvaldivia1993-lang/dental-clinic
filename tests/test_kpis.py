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
        "edad": [30, 30, 60, 10, 60],
        "sexo": ["F", "F", "M", "F", "M"],
        "es_nuevo": [True, False, True, True, False],
        "odontologo": ["A", "A", "B", "B", "B"],
        "tratamiento": ["Limpieza", "Empaste", "Limpieza", "Implante", "Consulta"],
        "duracion_min": [45, 45, 45, 120, 30],
        "estado": ["Completada", "Completada", "Completada", "Cancelada", "No asistió"],
        "canal_reserva": ["Web", "Web", "Teléfono", "Teléfono", "Web"],
        # C2 costó 250 pero solo pagó 200: queda debiendo 50
        "precio": [100.0, 250.0, 100.0, 2500.0, 50.0],
        "pagado": [100.0, 200.0, 100.0, 0.0, 0.0],
        "saldo": [0.0, 50.0, 0.0, 0.0, 0.0],
        "costo_material": [10.0, 50.0, 10.0, 0.0, 0.0],
    })


@pytest.fixture
def horarios():
    # A trabaja los lunes 4 h y B los martes 6 h
    return pd.DataFrame({
        "odontologo": ["A", "B"],
        "dia_semana": ["Lunes", "Martes"],
        "hora_inicio": [8, 8],
        "hora_fin": [12, 14],
    })


@pytest.fixture
def presupuestos():
    return pd.DataFrame({
        "id_presupuesto": ["PR1", "PR2", "PR3", "PR4"],
        "tratamiento": ["Implante", "Implante", "Ortodoncia", "Ortodoncia"],
        "aceptado": [True, False, True, True],
    })


@pytest.fixture
def gastos():
    return pd.DataFrame({
        "mes": pd.to_datetime(["2026-01-01", "2026-01-01", "2026-02-01", "2026-02-01"]),
        "concepto": ["Publicidad", "Sueldos", "Publicidad", "Sueldos"],
        "monto": [100.0, 1000.0, 50.0, 1000.0],
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
    assert kpis.tasa_retencion(vacio) == 0


def test_perdidas(citas):
    # Implante cancelado (2500) + consulta no asistida (50)
    assert kpis.perdida_por_cancelaciones(citas) == 2550
    tabla = kpis.tasa_perdida_por(citas, "odontologo").set_index("odontologo")
    assert tabla.loc["A", "perdidas"] == 0
    assert tabla.loc["B", "perdidas"] == pytest.approx(200 / 3)
    assert tabla.loc["B", "monto_perdido"] == 2550


def test_ingresos_por_dia_y_crecimiento(citas):
    assert dict(kpis.ingresos_por_dia(citas).values) == {"Lunes": 100, "Martes": 300, "Miércoles": 0}
    # Enero 300, febrero 100 → cae 66,7 %
    assert kpis.crecimiento_mensual(citas)["crecimiento"].iloc[-1] == pytest.approx(-200 / 3)


def test_retencion(citas):
    # Con 30 días: solo P1 es elegible y volvió a los 15 días
    assert kpis.tasa_retencion(citas, dias=30) == 100
    # Con 10 días: P1 no volvió a tiempo
    assert kpis.tasa_retencion(citas, dias=10) == 0


def test_perfil_pacientes(citas):
    tabla = kpis.perfil_pacientes(citas).set_index(["grupo_edad", "sexo"])["pacientes"]
    assert tabla[("0–17", "F")] == 1
    assert tabla[("18–34", "F")] == 1
    assert tabla[("55+", "M")] == 1
    assert tabla.sum() == 3


def test_ocupacion(citas, horarios):
    agenda = kpis.agenda_disponible(horarios, "2026-01-05", "2026-02-10")
    # 6 lunes × 4 h + 6 martes × 6 h = 60 h
    assert agenda["horas"].sum() == 60
    # Reservadas: 45 + 45 + 45 + 30 min = 2,75 h (la cancelada no cuenta)
    assert kpis.ocupacion(citas, agenda) == pytest.approx(2.75 / 60 * 100)
    por_odontologo = kpis.ocupacion_por(citas, agenda, "odontologo").set_index("odontologo")["ocupacion"]
    assert por_odontologo["A"] == pytest.approx(1.5 / 24 * 100)
    # Filtrar por odontólogo deja solo su horario
    assert kpis.agenda_disponible(horarios, "2026-01-05", "2026-02-10", ["A"])["horas"].sum() == 24


def test_ingreso_por_hora_sillon(citas):
    # 400 cobrados en 3 citas de 45 min = 2,25 h
    assert kpis.ingreso_por_hora_sillon(citas) == pytest.approx(400 / 2.25)


def test_cobranza(citas):
    assert kpis.facturado(citas) == 450
    assert kpis.cuentas_por_cobrar(citas) == 50
    assert kpis.porcentaje_cobrado(citas) == pytest.approx(400 / 450 * 100)
    assert kpis.top_deudores(citas)["id_paciente"].tolist() == ["P1"]


def test_presupuestos(presupuestos):
    assert kpis.aceptacion_presupuestos(presupuestos) == 75
    tabla = kpis.aceptacion_por_tratamiento(presupuestos).set_index("tratamiento")["aceptacion"]
    assert tabla["Implante"] == 50
    assert tabla["Ortodoncia"] == 100


def test_rentabilidad(citas):
    tabla = kpis.rentabilidad_por_tratamiento(citas).set_index("tratamiento")
    assert tabla.loc["Limpieza", "ganancia"] == 180
    assert tabla.loc["Limpieza", "margen"] == 90


def test_utilidad_y_costo_paciente(citas, gastos):
    utilidad = kpis.utilidad_mensual(citas, gastos)["utilidad"].tolist()
    # Enero: 350 − 60 − 1100 ; febrero: 100 − 10 − 1050
    assert utilidad == [-810, -960]
    # 150 de publicidad / 3 pacientes nuevos
    assert kpis.costo_por_paciente_nuevo(citas, gastos) == 50

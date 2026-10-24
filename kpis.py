"""Funciones de cálculo de los indicadores (KPIs) de la clínica.

Todas reciben el DataFrame de citas (ya filtrado) y no modifican el original.
"""

import pandas as pd

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def completadas(df):
    """Solo las citas que realmente se atendieron."""
    return df[df["estado"] == "Completada"]


def ingresos_totales(df):
    return float(df["pagado"].sum())


def ticket_promedio(df):
    """Ingreso medio por cita atendida."""
    atendidas = completadas(df)
    return float(atendidas["pagado"].mean()) if len(atendidas) else 0.0


def ingreso_por_paciente(df):
    """Ingreso total dividido entre los pacientes únicos atendidos."""
    pacientes = completadas(df)["id_paciente"].nunique()
    return ingresos_totales(df) / pacientes if pacientes else 0.0


def top_pacientes(df, n=10):
    """Los n pacientes que más ingresos generaron."""
    return (
        completadas(df)
        .groupby("id_paciente")
        .agg(visitas=("id_cita", "count"), ingresos=("pagado", "sum"))
        .sort_values("ingresos", ascending=False)
        .head(n)
        .reset_index()
    )


def pacientes_recurrentes(df):
    """Pacientes con 2 o más citas completadas: devuelve (número, porcentaje)."""
    visitas = completadas(df).groupby("id_paciente").size()
    if visitas.empty:
        return 0, 0.0
    recurrentes = int((visitas >= 2).sum())
    return recurrentes, recurrentes / len(visitas) * 100


def tasa_cancelacion(df):
    """Porcentaje de citas canceladas sobre el total de citas agendadas."""
    return (df["estado"] == "Cancelada").mean() * 100 if len(df) else 0.0


def tasa_no_show(df):
    """Porcentaje de citas a las que el paciente no asistió sin avisar."""
    return (df["estado"] == "No asistió").mean() * 100 if len(df) else 0.0


def visitas_por_hora(df):
    """Número de visitas atendidas en cada hora del día."""
    return completadas(df).groupby("hora").size().rename("visitas").reset_index()


def mapa_hora_dia(df):
    """Tabla hora × día de la semana con el número de visitas (para el mapa de calor)."""
    tabla = pd.crosstab(completadas(df)["hora"], completadas(df)["dia_semana"])
    return tabla.reindex(columns=[d for d in DIAS if d in tabla.columns])


def ingresos_por_tratamiento(df):
    return (
        completadas(df)
        .groupby("tratamiento")
        .agg(citas=("id_cita", "count"), ingresos=("pagado", "sum"))
        .sort_values("ingresos", ascending=False)
        .reset_index()
    )


def ingresos_por_mes(df):
    meses = df["fecha"].dt.to_period("M").dt.to_timestamp()
    return df.groupby(meses)["pagado"].sum().rename("ingresos").rename_axis("mes").reset_index()


def pacientes_nuevos_por_mes(df):
    nuevos = df[df["es_nuevo"]]
    meses = nuevos["fecha"].dt.to_period("M").dt.to_timestamp()
    return nuevos.groupby(meses).size().rename("nuevos").rename_axis("mes").reset_index()


def por_odontologo(df):
    """Productividad de cada odontólogo: citas atendidas, ingresos y % de cancelación."""
    resumen = df.groupby("odontologo").agg(
        citas=("id_cita", "count"),
        canceladas=("estado", lambda s: (s == "Cancelada").mean() * 100),
    )
    resumen["ingresos"] = completadas(df).groupby("odontologo")["pagado"].sum()
    return resumen.fillna(0).sort_values("ingresos", ascending=False).reset_index()


def estado_citas(df):
    return df["estado"].value_counts().rename_axis("estado").reset_index(name="citas")


def por_canal(df):
    """Citas por canal de reserva y su % de cancelación + no-show."""
    resumen = df.groupby("canal_reserva").agg(
        citas=("id_cita", "count"),
        perdidas=("estado", lambda s: (s != "Completada").mean() * 100),
    )
    return resumen.sort_values("citas", ascending=False).reset_index()

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


def tasa_perdida_por(df, columna):
    """Citas, % de cancelaciones + no-show y monto perdido, agrupado por una columna."""
    perdidas = df["estado"] != "Completada"
    return (
        df.assign(perdida=perdidas, monto=df["precio"].where(perdidas, 0))
        .groupby(columna)
        .agg(citas=("id_cita", "count"), perdidas=("perdida", "mean"), monto_perdido=("monto", "sum"))
        .assign(perdidas=lambda t: t["perdidas"] * 100)
        .reset_index()
    )


# --- KPIs adicionales con los datos de citas ---

def perdida_por_cancelaciones(df):
    """Dinero que se dejó de facturar por citas canceladas o no asistidas."""
    return float(df.loc[df["estado"] != "Completada", "precio"].sum())


def ingresos_por_dia(df):
    tabla = df.groupby("dia_semana")["pagado"].sum()
    return tabla.reindex([d for d in DIAS if d in tabla.index]).rename("ingresos").reset_index()


def crecimiento_mensual(df):
    """Ingresos por mes y su variación % respecto al mes anterior."""
    tabla = ingresos_por_mes(df)
    tabla["crecimiento"] = tabla["ingresos"].pct_change() * 100
    return tabla


def tasa_retencion(df, dias=180):
    """% de pacientes que vuelven a atenderse dentro de `dias` días tras su primera visita.

    Solo cuenta a los pacientes cuya primera visita deja al menos `dias` días de margen
    antes del final de los datos, para darles tiempo de volver.
    """
    atendidas = completadas(df)
    if atendidas.empty:
        return 0.0
    primera = atendidas.groupby("id_paciente")["fecha"].transform("min")
    elegibles = atendidas[primera <= df["fecha"].max() - pd.Timedelta(days=dias)]
    if elegibles.empty:
        return 0.0
    primera = primera[elegibles.index]
    volvio = (elegibles["fecha"] > primera) & (elegibles["fecha"] <= primera + pd.Timedelta(days=dias))
    return float(volvio.groupby(elegibles["id_paciente"]).any().mean() * 100)


def perfil_pacientes(df):
    """Pacientes únicos por grupo de edad y sexo."""
    pacientes = df.drop_duplicates("id_paciente")
    grupos = pd.cut(pacientes["edad"], [0, 17, 34, 54, 200], labels=["0–17", "18–34", "35–54", "55+"])
    return (
        pacientes.groupby([grupos, "sexo"], observed=False)
        .size()
        .rename("pacientes")
        .rename_axis(["grupo_edad", "sexo"])
        .reset_index()
    )


# --- Agenda ---

def agenda_disponible(horarios, fecha_ini, fecha_fin, odontologos=None):
    """Horas de atención de cada odontólogo en cada fecha del rango, según su horario."""
    if odontologos:
        horarios = horarios[horarios["odontologo"].isin(odontologos)]
    fechas = pd.DataFrame({"fecha": pd.date_range(fecha_ini, fecha_fin)})
    fechas["dia_semana"] = fechas["fecha"].dt.day_of_week.map(dict(enumerate(DIAS)))
    agenda = fechas.merge(horarios, on="dia_semana")
    agenda["horas"] = agenda["hora_fin"] - agenda["hora_inicio"]
    return agenda[["fecha", "dia_semana", "odontologo", "horas"]]


def horas_reservadas(df):
    """Horas de sillón ocupadas: citas completadas o no asistidas (el espacio quedó reservado)."""
    return df[df["estado"] != "Cancelada"].assign(horas=lambda t: t["duracion_min"] / 60)


def ocupacion(df, agenda):
    """% de las horas disponibles que estuvieron reservadas."""
    disponibles = agenda["horas"].sum()
    return float(horas_reservadas(df)["horas"].sum() / disponibles * 100) if disponibles else 0.0


def ocupacion_por(df, agenda, columna):
    """% de ocupación por odontólogo o por día de la semana."""
    reservadas = horas_reservadas(df).groupby(columna)["horas"].sum()
    disponibles = agenda.groupby(columna)["horas"].sum()
    tabla = (reservadas.reindex(disponibles.index, fill_value=0) / disponibles * 100).rename("ocupacion")
    if columna == "dia_semana":
        tabla = tabla.reindex([d for d in DIAS if d in tabla.index])
    return tabla.reset_index()


def ingreso_por_hora_sillon(df):
    """Ingreso por cada hora de atención realizada."""
    horas = (completadas(df)["duracion_min"] / 60).sum()
    return ingresos_totales(df) / horas if horas else 0.0


# --- Finanzas ---

def facturado(df):
    """Total cobrable de las citas atendidas (lo pagado más lo que se debe)."""
    return float(completadas(df)["precio"].sum())


def cuentas_por_cobrar(df):
    return float(df["saldo"].sum())


def porcentaje_cobrado(df):
    total = facturado(df)
    return ingresos_totales(df) / total * 100 if total else 0.0


def top_deudores(df, n=10):
    return (
        df[df["saldo"] > 0]
        .groupby("id_paciente")
        .agg(citas_con_deuda=("id_cita", "count"), deuda=("saldo", "sum"))
        .sort_values("deuda", ascending=False)
        .head(n)
        .reset_index()
    )


def aceptacion_presupuestos(presupuestos):
    return float(presupuestos["aceptado"].mean() * 100) if len(presupuestos) else 0.0


def aceptacion_por_tratamiento(presupuestos):
    return (
        presupuestos.groupby("tratamiento")
        .agg(presupuestos=("id_presupuesto", "count"), aceptacion=("aceptado", "mean"))
        .assign(aceptacion=lambda t: t["aceptacion"] * 100)
        .sort_values("aceptacion", ascending=False)
        .reset_index()
    )


def rentabilidad_por_tratamiento(df):
    """Facturado, costo de materiales, ganancia y margen % de cada tratamiento."""
    tabla = (
        completadas(df)
        .groupby("tratamiento")
        .agg(facturado=("precio", "sum"), materiales=("costo_material", "sum"))
    )
    tabla["ganancia"] = tabla["facturado"] - tabla["materiales"]
    tabla["margen"] = tabla["ganancia"] / tabla["facturado"] * 100
    return tabla.sort_values("ganancia", ascending=False).reset_index()


def utilidad_mensual(df, gastos):
    """Facturado − materiales − gastos fijos, mes a mes."""
    atendidas = completadas(df)
    meses = atendidas["fecha"].dt.to_period("M").dt.to_timestamp()
    tabla = atendidas.groupby(meses).agg(facturado=("precio", "sum"), materiales=("costo_material", "sum"))
    tabla["gastos_fijos"] = gastos.groupby("mes")["monto"].sum()
    tabla = tabla.fillna(0)
    tabla["utilidad"] = tabla["facturado"] - tabla["materiales"] - tabla["gastos_fijos"]
    return tabla.rename_axis("mes").reset_index()


def costo_por_paciente_nuevo(df, gastos):
    """Gasto en publicidad dividido entre los pacientes nuevos captados."""
    nuevos = int(df["es_nuevo"].sum())
    publicidad = gastos.loc[gastos["concepto"] == "Publicidad", "monto"].sum()
    return float(publicidad / nuevos) if nuevos else 0.0

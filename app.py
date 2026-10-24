"""Dashboard de la clínica dental. Ejecutar con: venv/bin/streamlit run app.py"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

import kpis

CARPETA = Path("data")
ARCHIVOS = ["citas.csv", "horarios.csv", "presupuestos.csv", "gastos.csv"]
COLOR = "#2a9d8f"
COLOR_ALERTA = "#e76f51"
COLORES_ESTADO = {"Completada": "#2a9d8f", "Cancelada": "#e76f51", "No asistió": "#f4a261"}
FORMATO_SOLES = st.column_config.NumberColumn(format="S/ %.0f")
FORMATO_PCT = st.column_config.NumberColumn(format="%.1f %%")

st.set_page_config(page_title="Clínica Dental · Dashboard", page_icon="🦷", layout="wide")


@st.cache_data
def cargar_datos():
    citas = pd.read_csv(CARPETA / "citas.csv", parse_dates=["fecha"])
    horarios = pd.read_csv(CARPETA / "horarios.csv")
    presupuestos = pd.read_csv(CARPETA / "presupuestos.csv", parse_dates=["fecha"])
    gastos = pd.read_csv(CARPETA / "gastos.csv", parse_dates=["mes"])
    return citas, horarios, presupuestos, gastos


def soles(valor):
    return f"S/ {valor:,.0f}"


def barras(datos, x, y, titulo, color=COLOR, **opciones):
    fig = px.bar(datos, x=x, y=y, title=titulo, **opciones)
    if "color" not in opciones:
        fig.update_traces(marker_color=color)
    return fig


if not all((CARPETA / archivo).exists() for archivo in ARCHIVOS):
    st.error("Faltan archivos en data/. Ejecuta primero: venv/bin/python generar_datos.py")
    st.stop()

citas, horarios, presupuestos, gastos = cargar_datos()

# --- Filtros en la barra lateral ---
st.sidebar.header("Filtros")
fecha_min, fecha_max = citas["fecha"].min().date(), citas["fecha"].max().date()
rango = st.sidebar.date_input("Rango de fechas", (fecha_min, fecha_max), fecha_min, fecha_max)
odontologos = st.sidebar.multiselect("Odontólogo", sorted(citas["odontologo"].unique()))
tratamientos = st.sidebar.multiselect("Tratamiento", sorted(citas["tratamiento"].unique()))

inicio, fin = rango if len(rango) == 2 else (fecha_min, fecha_max)
df = citas[citas["fecha"].dt.date.between(inicio, fin)]
pres = presupuestos[presupuestos["fecha"].dt.date.between(inicio, fin)]
gas = gastos[gastos["mes"].dt.to_period("M").between(pd.Period(inicio, "M"), pd.Period(fin, "M"))]
if odontologos:
    df = df[df["odontologo"].isin(odontologos)]
    pres = pres[pres["odontologo"].isin(odontologos)]
if tratamientos:
    df = df[df["tratamiento"].isin(tratamientos)]
    pres = pres[pres["tratamiento"].isin(tratamientos)]
agenda = kpis.agenda_disponible(horarios, inicio, fin, odontologos)

st.sidebar.caption(f"{len(df):,} citas seleccionadas de {len(citas):,}")

# --- Tarjetas de KPIs ---
st.title("🦷 Dashboard de la clínica dental")

if df.empty:
    st.warning("No hay citas con los filtros elegidos.")
    st.stop()

crecimiento = kpis.crecimiento_mensual(df)["crecimiento"].iloc[-1]
n_recurrentes, pct_recurrentes = kpis.pacientes_recurrentes(df)
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Ingresos totales", soles(kpis.ingresos_totales(df)),
          None if pd.isna(crecimiento) else f"{crecimiento:+.1f} % último mes")
c2.metric("Ingreso por paciente", soles(kpis.ingreso_por_paciente(df)))
c3.metric("Ticket promedio", soles(kpis.ticket_promedio(df)))
c4.metric("Pacientes recurrentes", f"{n_recurrentes}", f"{pct_recurrentes:.0f} % del total", delta_color="off")
c5.metric("% cancelación", f"{kpis.tasa_cancelacion(df):.1f} %")
c6.metric("% no asistió", f"{kpis.tasa_no_show(df):.1f} %")

resumen, pacientes, agenda_tab, cancelaciones, tratamientos_tab, finanzas = st.tabs(
    ["Resumen", "Pacientes", "Agenda", "Cancelaciones", "Tratamientos", "Finanzas"]
)

with resumen:
    izq, der = st.columns([2, 1])
    fig = px.line(kpis.ingresos_por_mes(df), x="mes", y="ingresos", markers=True, title="Ingresos por mes")
    fig.update_traces(line_color=COLOR)
    izq.plotly_chart(fig, width="stretch")

    fig = px.pie(kpis.estado_citas(df), names="estado", values="citas", hole=0.5,
                 title="Estado de las citas", color="estado", color_discrete_map=COLORES_ESTADO)
    der.plotly_chart(fig, width="stretch")

    st.plotly_chart(barras(kpis.ingresos_por_dia(df), "dia_semana", "ingresos", "Ingresos por día de la semana",
                           labels={"dia_semana": "Día"}), width="stretch")

with pacientes:
    m1, m2 = st.columns(2)
    m1.metric("Retención a 6 meses", f"{kpis.tasa_retencion(df):.0f} %",
              help="% de pacientes que vuelven a atenderse dentro de los 180 días siguientes a su primera visita.")
    m2.metric("Pacientes atendidos", f"{kpis.completadas(df)['id_paciente'].nunique():,}")

    izq, der = st.columns(2)
    izq.plotly_chart(barras(kpis.pacientes_nuevos_por_mes(df), "mes", "nuevos", "Pacientes nuevos por mes"),
                     width="stretch")
    fig = px.bar(kpis.perfil_pacientes(df), x="grupo_edad", y="pacientes", color="sexo", barmode="group",
                 title="Pacientes por edad y sexo", labels={"grupo_edad": "Edad"},
                 color_discrete_map={"F": COLOR, "M": "#264653"})
    der.plotly_chart(fig, width="stretch")

    st.subheader("Top 10 pacientes por ingresos")
    st.dataframe(kpis.top_pacientes(df), hide_index=True, width="stretch", column_config={"ingresos": FORMATO_SOLES})

with agenda_tab:
    if tratamientos:
        st.info("La ocupación considera solo las citas de los tratamientos filtrados.")
    m1, m2, m3 = st.columns(3)
    m1.metric("Ocupación de la agenda", f"{kpis.ocupacion(df, agenda):.1f} %",
              help="Horas reservadas (citas completadas o no asistidas) ÷ horas de atención disponibles.")
    m2.metric("Ingreso por hora de sillón", soles(kpis.ingreso_por_hora_sillon(df)))
    m3.metric("Horas disponibles", f"{agenda['horas'].sum():,.0f} h")

    izq, der = st.columns(2)
    fig = barras(kpis.ocupacion_por(df, agenda, "odontologo"), "odontologo", "ocupacion", "Ocupación por odontólogo",
                 labels={"ocupacion": "Ocupación (%)", "odontologo": "Odontólogo"}, text_auto=".0f")
    izq.plotly_chart(fig, width="stretch")
    fig = barras(kpis.ocupacion_por(df, agenda, "dia_semana"), "dia_semana", "ocupacion", "Ocupación por día",
                 labels={"ocupacion": "Ocupación (%)", "dia_semana": "Día"}, text_auto=".0f")
    der.plotly_chart(fig, width="stretch")

    izq, der = st.columns(2)
    fig = barras(kpis.visitas_por_hora(df), "hora", "visitas", "Visitas atendidas por hora")
    fig.update_xaxes(dtick=1)
    izq.plotly_chart(fig, width="stretch")

    fig = px.imshow(kpis.mapa_hora_dia(df), color_continuous_scale="Teal", aspect="auto",
                    labels={"x": "Día", "y": "Hora", "color": "Visitas"}, title="Visitas por hora y día")
    der.plotly_chart(fig, width="stretch")

    fig = barras(kpis.por_odontologo(df), "odontologo", "ingresos", "Ingresos por odontólogo", text_auto=".2s",
                 hover_data={"citas": True, "canceladas": ":.1f"})
    st.plotly_chart(fig, width="stretch")

with cancelaciones:
    m1, m2, m3 = st.columns(3)
    m1.metric("Dinero perdido", soles(kpis.perdida_por_cancelaciones(df)),
              help="Precio de las citas canceladas o a las que el paciente no asistió.")
    m2.metric("% cancelación", f"{kpis.tasa_cancelacion(df):.1f} %")
    m3.metric("% no asistió", f"{kpis.tasa_no_show(df):.1f} %")

    etiquetas = {"perdidas": "% cancel. + no asistió", "monto_perdido": "S/ perdidos"}
    izq, der = st.columns(2)
    fig = barras(kpis.tasa_perdida_por(df, "hora"), "hora", "perdidas", "Citas perdidas por hora",
                 color=COLOR_ALERTA, labels=etiquetas, hover_data={"monto_perdido": ":,.0f"})
    fig.update_xaxes(dtick=1)
    izq.plotly_chart(fig, width="stretch")
    fig = barras(kpis.tasa_perdida_por(df, "canal_reserva"), "canal_reserva", "perdidas",
                 "Citas perdidas por canal de reserva", color=COLOR_ALERTA,
                 labels={**etiquetas, "canal_reserva": "Canal"}, hover_data={"citas": True})
    der.plotly_chart(fig, width="stretch")

    st.subheader("Por odontólogo")
    st.dataframe(kpis.tasa_perdida_por(df, "odontologo"), hide_index=True, width="stretch",
                 column_config={"perdidas": FORMATO_PCT, "monto_perdido": FORMATO_SOLES})

with tratamientos_tab:
    trat = kpis.ingresos_por_tratamiento(df)
    izq, der = st.columns([2, 1])
    fig = px.bar(trat, x="ingresos", y="tratamiento", orientation="h", text_auto=".2s",
                 title="Ingresos por tipo de tratamiento")
    fig.update_traces(marker_color=COLOR)
    fig.update_yaxes(categoryorder="total ascending")
    izq.plotly_chart(fig, width="stretch")

    der.subheader("Detalle")
    der.dataframe(trat, hide_index=True, width="stretch", column_config={"ingresos": FORMATO_SOLES})

    st.subheader("Rentabilidad por tratamiento")
    st.caption("Ganancia = facturado − costo de materiales (sin gastos fijos).")
    st.dataframe(kpis.rentabilidad_por_tratamiento(df), hide_index=True, width="stretch",
                 column_config={"facturado": FORMATO_SOLES, "materiales": FORMATO_SOLES,
                                "ganancia": FORMATO_SOLES, "margen": FORMATO_PCT})

with finanzas:
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Facturado", soles(kpis.facturado(df)))
    m2.metric("Cobrado", soles(kpis.ingresos_totales(df)), f"{kpis.porcentaje_cobrado(df):.1f} % del facturado",
              delta_color="off")
    m3.metric("Por cobrar", soles(kpis.cuentas_por_cobrar(df)))
    m4.metric("Aceptación de presupuestos", f"{kpis.aceptacion_presupuestos(pres):.0f} %")
    m5.metric("Costo por paciente nuevo", soles(kpis.costo_por_paciente_nuevo(df, gas)),
              help="Gasto en publicidad ÷ pacientes nuevos del periodo.")

    if odontologos or tratamientos:
        st.info("Los gastos fijos son de toda la clínica: la utilidad y el costo por paciente nuevo "
                "no se reparten por odontólogo ni por tratamiento.")
    utilidad = kpis.utilidad_mensual(df, gas)
    fig = px.bar(utilidad, x="mes", y="utilidad", title="Utilidad mensual (facturado − materiales − gastos fijos)",
                 color=utilidad["utilidad"] >= 0, color_discrete_map={True: COLOR, False: COLOR_ALERTA},
                 hover_data={"facturado": ":,.0f", "materiales": ":,.0f", "gastos_fijos": ":,.0f"})
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, width="stretch")

    izq, der = st.columns(2)
    fig = barras(kpis.aceptacion_por_tratamiento(pres), "tratamiento", "aceptacion",
                 "Aceptación de presupuestos por tratamiento", text_auto=".0f",
                 labels={"aceptacion": "Aceptación (%)"}, hover_data={"presupuestos": True})
    izq.plotly_chart(fig, width="stretch")

    der.subheader("Top 10 pacientes con deuda")
    der.dataframe(kpis.top_deudores(df), hide_index=True, width="stretch", column_config={"deuda": FORMATO_SOLES})

"""Dashboard de la clínica dental. Ejecutar con: venv/bin/streamlit run app.py"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

import kpis

RUTA_DATOS = Path("data/citas.csv")
COLOR = "#2a9d8f"
COLORES_ESTADO = {"Completada": "#2a9d8f", "Cancelada": "#e76f51", "No asistió": "#f4a261"}

st.set_page_config(page_title="Clínica Dental · Dashboard", page_icon="🦷", layout="wide")


@st.cache_data
def cargar_datos():
    return pd.read_csv(RUTA_DATOS, parse_dates=["fecha"])


def soles(valor):
    return f"S/ {valor:,.0f}"


if not RUTA_DATOS.exists():
    st.error("No se encontró data/citas.csv. Ejecuta primero: venv/bin/python generar_datos.py")
    st.stop()

datos = cargar_datos()

# --- Filtros en la barra lateral ---
st.sidebar.header("Filtros")
fecha_min, fecha_max = datos["fecha"].min().date(), datos["fecha"].max().date()
rango = st.sidebar.date_input("Rango de fechas", (fecha_min, fecha_max), fecha_min, fecha_max)
odontologos = st.sidebar.multiselect("Odontólogo", sorted(datos["odontologo"].unique()))
tratamientos = st.sidebar.multiselect("Tratamiento", sorted(datos["tratamiento"].unique()))

df = datos
if len(rango) == 2:
    df = df[df["fecha"].dt.date.between(*rango)]
if odontologos:
    df = df[df["odontologo"].isin(odontologos)]
if tratamientos:
    df = df[df["tratamiento"].isin(tratamientos)]

st.sidebar.caption(f"{len(df):,} citas seleccionadas de {len(datos):,}")

# --- Tarjetas de KPIs ---
st.title("🦷 Dashboard de la clínica dental")

if df.empty:
    st.warning("No hay citas con los filtros elegidos.")
    st.stop()

n_recurrentes, pct_recurrentes = kpis.pacientes_recurrentes(df)
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Ingresos totales", soles(kpis.ingresos_totales(df)))
c2.metric("Ingreso por paciente", soles(kpis.ingreso_por_paciente(df)))
c3.metric("Ticket promedio", soles(kpis.ticket_promedio(df)))
c4.metric("Pacientes recurrentes", f"{n_recurrentes}", f"{pct_recurrentes:.0f} % del total", delta_color="off")
c5.metric("% cancelación", f"{kpis.tasa_cancelacion(df):.1f} %")
c6.metric("% no asistió", f"{kpis.tasa_no_show(df):.1f} %")

resumen, pacientes, operacion, tratamientos_tab = st.tabs(["Resumen", "Pacientes", "Operación", "Tratamientos"])

with resumen:
    izq, der = st.columns([2, 1])
    fig = px.line(kpis.ingresos_por_mes(df), x="mes", y="ingresos", markers=True, title="Ingresos por mes")
    fig.update_traces(line_color=COLOR)
    izq.plotly_chart(fig, width="stretch")

    fig = px.pie(kpis.estado_citas(df), names="estado", values="citas", hole=0.5,
                 title="Estado de las citas", color="estado", color_discrete_map=COLORES_ESTADO)
    der.plotly_chart(fig, width="stretch")

with pacientes:
    izq, der = st.columns(2)
    fig = px.bar(kpis.pacientes_nuevos_por_mes(df), x="mes", y="nuevos", title="Pacientes nuevos por mes")
    fig.update_traces(marker_color=COLOR)
    izq.plotly_chart(fig, width="stretch")

    der.subheader("Top 10 pacientes por ingresos")
    der.dataframe(kpis.top_pacientes(df), hide_index=True, width="stretch",
                  column_config={"ingresos": st.column_config.NumberColumn(format="S/ %.0f")})

with operacion:
    izq, der = st.columns(2)
    fig = px.bar(kpis.visitas_por_hora(df), x="hora", y="visitas", title="Visitas atendidas por hora")
    fig.update_traces(marker_color=COLOR)
    fig.update_xaxes(dtick=1)
    izq.plotly_chart(fig, width="stretch")

    fig = px.imshow(kpis.mapa_hora_dia(df), color_continuous_scale="Teal", aspect="auto",
                    labels={"x": "Día", "y": "Hora", "color": "Visitas"}, title="Visitas por hora y día")
    der.plotly_chart(fig, width="stretch")

    izq, der = st.columns(2)
    odonto = kpis.por_odontologo(df)
    fig = px.bar(odonto, x="odontologo", y="ingresos", text_auto=".2s", title="Ingresos por odontólogo",
                 hover_data={"citas": True, "canceladas": ":.1f"})
    fig.update_traces(marker_color=COLOR)
    izq.plotly_chart(fig, width="stretch")

    canal = kpis.por_canal(df)
    fig = px.bar(canal, x="canal_reserva", y="citas", title="Citas por canal de reserva",
                 color="perdidas", color_continuous_scale="OrRd",
                 labels={"perdidas": "% cancel. + no asistió", "canal_reserva": "Canal"})
    der.plotly_chart(fig, width="stretch")

with tratamientos_tab:
    trat = kpis.ingresos_por_tratamiento(df)
    izq, der = st.columns([2, 1])
    fig = px.bar(trat, x="ingresos", y="tratamiento", orientation="h", text_auto=".2s",
                 title="Ingresos por tipo de tratamiento")
    fig.update_traces(marker_color=COLOR)
    fig.update_yaxes(categoryorder="total ascending")
    izq.plotly_chart(fig, width="stretch")

    der.subheader("Detalle")
    der.dataframe(trat, hide_index=True, width="stretch",
                  column_config={"ingresos": st.column_config.NumberColumn(format="S/ %.0f")})

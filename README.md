# Dashboard de clínica dental 🦷

Dashboard en Streamlit + Plotly con los indicadores clave (KPIs) de una clínica dental,
construido sobre **datos ficticios** de un año de citas.

## KPIs

| Pedidos | Sugeridos |
|---|---|
| Ingreso por paciente | Ingresos totales y por mes |
| Pacientes recurrentes (≥ 2 citas atendidas) | Ticket promedio por cita |
| % de cancelación de citas | % de pacientes que no asistieron (no-show) |
| Visitas por hora (y mapa hora × día) | Pacientes nuevos por mes |
| Ingresos por tipo de tratamiento | Ingresos por odontólogo · citas por canal de reserva · top 10 pacientes |

## Cómo usarlo

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/python generar_datos.py      # crea data/citas.csv
venv/bin/streamlit run app.py          # abre http://localhost:8501
venv/bin/python -m pytest              # pruebas de los KPIs
```

## Archivos

- `generar_datos.py`: genera las citas ficticias (semilla fija, siempre los mismos datos).
- `kpis.py`: funciones con pandas que calculan cada indicador.
- `app.py`: el dashboard (filtros por fecha, odontólogo y tratamiento).
- `tests/test_kpis.py`: comprueba los KPIs con un ejemplo pequeño calculado a mano.

Para usar datos reales, reemplaza `data/citas.csv` por un archivo con las mismas columnas.

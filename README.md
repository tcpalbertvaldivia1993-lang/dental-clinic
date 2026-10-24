# Dashboard de clínica dental 🦷

Dashboard en Streamlit + Plotly con los indicadores clave (KPIs) de una clínica dental,
construido sobre **datos ficticios** de un año de citas.

## KPIs

| Pestaña | Indicadores |
|---|---|
| Tarjetas superiores | Ingresos totales (con crecimiento del último mes), ingreso por paciente, ticket promedio, pacientes recurrentes, % cancelación, % no asistió |
| Resumen | Ingresos por mes, estado de las citas, ingresos por día de la semana |
| Pacientes | Retención a 6 meses, pacientes nuevos por mes, perfil por edad y sexo, top 10 pacientes |
| Agenda | % de ocupación, ingreso por hora de sillón, ocupación por odontólogo y por día, visitas por hora, mapa hora × día, ingresos por odontólogo |
| Cancelaciones | Dinero perdido, citas perdidas por hora, canal de reserva y odontólogo |
| Tratamientos | Ingresos por tratamiento, rentabilidad y margen (facturado − materiales) |
| Finanzas | Facturado, cobrado, cuentas por cobrar, aceptación de presupuestos, costo por paciente nuevo, utilidad mensual, top deudores |

## Cómo usarlo

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/python generar_datos.py      # crea los CSV en data/
venv/bin/streamlit run app.py          # abre http://localhost:8501
venv/bin/python -m pytest              # pruebas de los KPIs
```

## Archivos

- `generar_datos.py`: genera los datos ficticios (semilla fija, siempre los mismos datos):
  - `data/citas.csv`: una fila por cita (fecha, hora, paciente, odontólogo, tratamiento, duración, estado, precio, pagado, saldo, costo de materiales).
  - `data/horarios.csv`: días y turnos de cada odontólogo.
  - `data/presupuestos.csv`: presupuestos entregados y si fueron aceptados.
  - `data/gastos.csv`: gastos fijos mensuales (sueldos, alquiler, publicidad, servicios).
- `kpis.py`: funciones con pandas que calculan cada indicador.
- `app.py`: el dashboard (filtros por fecha, odontólogo y tratamiento).
- `tests/test_kpis.py`: comprueba los KPIs con un ejemplo pequeño calculado a mano.

Para usar datos reales, reemplaza los archivos de `data/` por otros con las mismas columnas.

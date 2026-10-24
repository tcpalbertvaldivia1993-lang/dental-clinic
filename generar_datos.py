"""Genera datos ficticios de una clínica dental en la carpeta data/.

Archivos que crea:
- citas.csv: una fila por cita
- horarios.csv: días y turnos de cada odontólogo
- presupuestos.csv: presupuestos entregados (aceptados o no)
- gastos.csv: gastos fijos mensuales
"""

from pathlib import Path

import numpy as np
import pandas as pd

SEMILLA = 42
N_PACIENTES = 1300
FECHA_INICIO = "2025-10-01"
FECHA_FIN = "2026-09-30"

# Tratamiento: (precio base en soles, peso de frecuencia, duración en minutos, % del precio en materiales)
TRATAMIENTOS = {
    "Consulta": (60, 0.22, 30, 0.05),
    "Limpieza": (120, 0.25, 45, 0.10),
    "Empaste": (180, 0.18, 45, 0.20),
    "Extracción": (200, 0.08, 45, 0.10),
    "Endodoncia": (650, 0.07, 90, 0.20),
    "Ortodoncia": (350, 0.10, 30, 0.25),
    "Blanqueamiento": (500, 0.06, 60, 0.30),
    "Implante": (2500, 0.04, 120, 0.40),
}
# Tratamientos que requieren presupuesto y su tasa de aceptación
ACEPTACION = {"Endodoncia": 0.75, "Ortodoncia": 0.55, "Blanqueamiento": 0.50, "Implante": 0.45}

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MANANA, TARDE = (8, 14), (14, 20)
# Odontólogo: lista de (día, turno)
HORARIOS = {
    "Dra. Pérez": [(d, MANANA) for d in DIAS[:5]],
    "Dr. Gómez": [(d, TARDE) for d in DIAS[:5]],
    "Dra. Torres": [("Martes", MANANA), ("Jueves", MANANA), ("Sábado", MANANA)],
    "Dr. Ramírez": [("Lunes", TARDE), ("Miércoles", TARDE), ("Viernes", TARDE), ("Sábado", MANANA)],
}
CANALES = ["Teléfono", "WhatsApp", "Web", "Presencial"]
PESOS_CANALES = [0.30, 0.35, 0.20, 0.15]

# Gastos fijos mensuales aproximados (en soles)
GASTOS = {"Sueldos": 45000, "Alquiler": 6000, "Publicidad": 6000, "Servicios": 1500}


def tabla_horarios():
    filas = [
        {"odontologo": o, "dia_semana": dia, "hora_inicio": ini, "hora_fin": fin}
        for o, turnos in HORARIOS.items()
        for dia, (ini, fin) in turnos
    ]
    return pd.DataFrame(filas)


def generar_pacientes(rng):
    """Crea la tabla de pacientes con edad, sexo y cuántas citas tendrá en el año."""
    pacientes = pd.DataFrame({
        "id_paciente": [f"P{i:04d}" for i in range(1, N_PACIENTES + 1)],
        "edad": rng.integers(5, 85, N_PACIENTES),
        "sexo": rng.choice(["F", "M"], N_PACIENTES, p=[0.55, 0.45]),
    })
    # Distribución sesgada: muchos pacientes con pocas citas y algunos muy recurrentes
    pacientes["n_citas"] = 1 + rng.negative_binomial(1, 0.25, N_PACIENTES)
    return pacientes


def generar_citas(rng, pacientes, horarios):
    """Genera una fila por cita, siempre dentro del horario del odontólogo."""
    nombres = list(TRATAMIENTOS)
    pesos = np.array([TRATAMIENTOS[t][1] for t in nombres])

    # Fechas en que trabaja cada odontólogo y su turno de cada día
    todas = pd.date_range(FECHA_INICIO, FECHA_FIN)
    turnos = {o: dict((d, t) for d, t in lista) for o, lista in HORARIOS.items()}
    fechas_por_odontologo = {
        o: todas[todas.day_of_week.map(lambda i: DIAS[i] in turnos[o])] for o in HORARIOS
    }
    # Los odontólogos con más horas reciben más pacientes
    odontologos = list(HORARIOS)
    horas = horarios.assign(h=horarios["hora_fin"] - horarios["hora_inicio"]).groupby("odontologo")["h"].sum()
    pesos_odontologos = horas[odontologos].to_numpy() / horas.sum()

    filas = []
    for p in pacientes.itertuples():
        preferido = rng.choice(odontologos, p=pesos_odontologos)
        citas_paciente = []
        for _ in range(p.n_citas):
            o = preferido if rng.random() < 0.85 else rng.choice(odontologos, p=pesos_odontologos)
            fecha = rng.choice(fechas_por_odontologo[o])
            ini, fin = turnos[o][DIAS[pd.Timestamp(fecha).day_of_week]]
            citas_paciente.append((pd.Timestamp(fecha), int(rng.integers(ini, fin)), o))

        for orden, (fecha, hora, o) in enumerate(sorted(citas_paciente)):
            tratamiento = nombres[rng.choice(len(nombres), p=pesos)]
            precio_base, _, duracion, pct_material = TRATAMIENTOS[tratamiento]
            estado = rng.choice(["Completada", "Cancelada", "No asistió"], p=[0.82, 0.12, 0.06])
            precio = round(precio_base * rng.uniform(0.9, 1.15), 2)
            completada = estado == "Completada"
            # Algunos pacientes pagan solo una parte y quedan con deuda
            pagado = precio if rng.random() > 0.15 else round(precio * rng.uniform(0.3, 0.9), 2)
            filas.append({
                "fecha": fecha,
                "hora": hora,
                "id_paciente": p.id_paciente,
                "edad": p.edad,
                "sexo": p.sexo,
                "es_nuevo": orden == 0,
                "odontologo": o,
                "tratamiento": tratamiento,
                "duracion_min": duracion,
                "estado": estado,
                "canal_reserva": rng.choice(CANALES, p=PESOS_CANALES),
                "precio": precio,
                "pagado": pagado if completada else 0.0,
                "saldo": round(precio - pagado, 2) if completada else 0.0,
                "costo_material": round(precio * pct_material, 2) if completada else 0.0,
            })

    citas = pd.DataFrame(filas).sort_values(["fecha", "hora"]).reset_index(drop=True)
    citas.insert(0, "id_cita", [f"C{i:05d}" for i in range(1, len(citas) + 1)])
    citas.insert(3, "dia_semana", citas["fecha"].dt.day_of_week.map(dict(enumerate(DIAS))))
    return citas


def generar_presupuestos(rng, citas):
    """Un presupuesto aceptado por cada paciente y tratamiento realizado, más otros rechazados."""
    hechas = citas[(citas["estado"] == "Completada") & citas["tratamiento"].isin(ACEPTACION)]
    aceptados = (
        hechas.groupby(["id_paciente", "tratamiento"])
        .agg(fecha=("fecha", "min"), odontologo=("odontologo", "first"), monto=("precio", "sum"))
        .reset_index()
    )
    # El presupuesto se entrega unos días antes de la primera cita
    dias_antes = pd.to_timedelta(rng.integers(0, 21, len(aceptados)), unit="D")
    aceptados["fecha"] = (aceptados["fecha"] - dias_antes).clip(lower=pd.Timestamp(FECHA_INICIO))
    aceptados["aceptado"] = True

    rechazados = []
    pacientes = citas["id_paciente"].unique()
    fechas = pd.date_range(FECHA_INICIO, FECHA_FIN)
    for tratamiento, tasa in ACEPTACION.items():
        n_aceptados = (aceptados["tratamiento"] == tratamiento).sum()
        n_rechazados = round(n_aceptados * (1 - tasa) / tasa)
        precio_base = TRATAMIENTOS[tratamiento][0]
        rechazados.append(pd.DataFrame({
            "id_paciente": rng.choice(pacientes, n_rechazados),
            "tratamiento": tratamiento,
            "fecha": rng.choice(fechas, n_rechazados),
            "odontologo": rng.choice(list(HORARIOS), n_rechazados),
            "monto": (precio_base * rng.uniform(0.9, 1.3, n_rechazados)).round(2),
            "aceptado": False,
        }))

    presupuestos = pd.concat([aceptados, *rechazados]).sort_values("fecha").reset_index(drop=True)
    presupuestos.insert(0, "id_presupuesto", [f"PR{i:05d}" for i in range(1, len(presupuestos) + 1)])
    return presupuestos[["id_presupuesto", "fecha", "id_paciente", "odontologo", "tratamiento", "monto", "aceptado"]]


def generar_gastos(rng):
    meses = pd.date_range(FECHA_INICIO, FECHA_FIN, freq="MS")
    filas = [
        {"mes": mes, "concepto": concepto, "monto": round(base * rng.uniform(0.9, 1.1), 2)}
        for mes in meses
        for concepto, base in GASTOS.items()
    ]
    return pd.DataFrame(filas)


def main():
    rng = np.random.default_rng(SEMILLA)
    horarios = tabla_horarios()
    citas = generar_citas(rng, generar_pacientes(rng), horarios)
    presupuestos = generar_presupuestos(rng, citas)
    gastos = generar_gastos(rng)

    carpeta = Path("data")
    carpeta.mkdir(exist_ok=True)
    citas.to_csv(carpeta / "citas.csv", index=False)
    horarios.to_csv(carpeta / "horarios.csv", index=False)
    presupuestos.to_csv(carpeta / "presupuestos.csv", index=False)
    gastos.to_csv(carpeta / "gastos.csv", index=False)
    print(f"Se generaron {len(citas)} citas de {citas['id_paciente'].nunique()} pacientes, "
          f"{len(presupuestos)} presupuestos y {len(gastos)} gastos en {carpeta}/")


if __name__ == "__main__":
    main()

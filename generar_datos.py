"""Genera datos ficticios de citas de una clínica dental en data/citas.csv."""

from pathlib import Path

import numpy as np
import pandas as pd

SEMILLA = 42
N_PACIENTES = 800
FECHA_INICIO = "2025-10-01"
FECHA_FIN = "2026-09-30"

# Precio base de cada tratamiento (en soles) y su peso de frecuencia
TRATAMIENTOS = {
    "Consulta": (60, 0.22),
    "Limpieza": (120, 0.25),
    "Empaste": (180, 0.18),
    "Extracción": (200, 0.08),
    "Endodoncia": (650, 0.07),
    "Ortodoncia": (350, 0.10),
    "Blanqueamiento": (500, 0.06),
    "Implante": (2500, 0.04),
}
ODONTOLOGOS = ["Dra. Pérez", "Dr. Gómez", "Dra. Torres", "Dr. Ramírez"]
CANALES = ["Teléfono", "WhatsApp", "Web", "Presencial"]
PESOS_CANALES = [0.30, 0.35, 0.20, 0.15]

# Horas de atención (8 a 19 h) con picos a media mañana y al final de la tarde
HORAS = np.arange(8, 20)
PESOS_HORAS = np.array([4, 7, 9, 9, 6, 3, 4, 6, 8, 9, 8, 5], dtype=float)
PESOS_HORAS /= PESOS_HORAS.sum()

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


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


def generar_citas(rng, pacientes):
    """Genera una fila por cita, repartiendo las citas de cada paciente en el año."""
    dias_habiles = pd.bdate_range(FECHA_INICIO, FECHA_FIN, freq="C", weekmask="Mon Tue Wed Thu Fri Sat")
    nombres = list(TRATAMIENTOS)
    precios = np.array([TRATAMIENTOS[t][0] for t in nombres])
    pesos = np.array([TRATAMIENTOS[t][1] for t in nombres])

    filas = []
    for p in pacientes.itertuples():
        fechas = np.sort(rng.choice(dias_habiles, p.n_citas))
        odontologo = rng.choice(ODONTOLOGOS)  # cada paciente suele ir con el mismo
        for orden, fecha in enumerate(fechas):
            idx = rng.choice(len(nombres), p=pesos)
            estado = rng.choice(["Completada", "Cancelada", "No asistió"], p=[0.82, 0.12, 0.06])
            precio = round(precios[idx] * rng.uniform(0.9, 1.15), 2)
            filas.append({
                "fecha": pd.Timestamp(fecha),
                "hora": rng.choice(HORAS, p=PESOS_HORAS),
                "id_paciente": p.id_paciente,
                "edad": p.edad,
                "sexo": p.sexo,
                "es_nuevo": orden == 0,
                "odontologo": odontologo if rng.random() < 0.85 else rng.choice(ODONTOLOGOS),
                "tratamiento": nombres[idx],
                "estado": estado,
                "canal_reserva": rng.choice(CANALES, p=PESOS_CANALES),
                "precio": precio,
                "pagado": precio if estado == "Completada" else 0.0,
            })

    citas = pd.DataFrame(filas).sort_values(["fecha", "hora"]).reset_index(drop=True)
    citas.insert(0, "id_cita", [f"C{i:05d}" for i in range(1, len(citas) + 1)])
    citas.insert(3, "dia_semana", citas["fecha"].dt.day_of_week.map(dict(enumerate(DIAS))))
    return citas


def main():
    rng = np.random.default_rng(SEMILLA)
    pacientes = generar_pacientes(rng)
    citas = generar_citas(rng, pacientes)

    ruta = Path("data/citas.csv")
    ruta.parent.mkdir(exist_ok=True)
    citas.to_csv(ruta, index=False)
    print(f"Se generaron {len(citas)} citas de {citas['id_paciente'].nunique()} pacientes en {ruta}")


if __name__ == "__main__":
    main()

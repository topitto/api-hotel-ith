from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import uuid

app = FastAPI(
    title="API Sistema de Reservaciones Hotel - ITH",
    description="Backend implementado con SQLite3 puro basado en consultas crudas.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --- CONEXIÓN A BASE DE DATOS ---
# Usamos un archivo físico en lugar de ":memory:" para que tus datos no se borren al apagar la API.
conn = sqlite3.connect("hotel_ith.db", check_same_thread=False)

# Esta función formatea las respuestas de SQLite como diccionarios en lugar de tuplas.
def dict_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

conn.row_factory = dict_factory
cursor = conn.cursor()

# --- CREACIÓN DE TABLAS (SQL CRUDO) ---
cursor.execute("""
CREATE TABLE IF NOT EXISTS habitaciones (
    id_habitacion TEXT PRIMARY KEY,
    numero TEXT UNIQUE,
    tipo TEXT,
    precio_noche REAL,
    piso INTEGER,
    estado TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS reservaciones (
    id_reservacion TEXT PRIMARY KEY,
    id_habitacion TEXT,
    huesped TEXT,
    fecha_inicio TEXT,
    fecha_fin TEXT,
    total_estancia REAL,
    estado_pago TEXT,
    FOREIGN KEY(id_habitacion) REFERENCES habitaciones(id_habitacion)
)
""")
conn.commit()

# --- MODELOS ESTRICTOS (PYDANTIC) ---
# Se utiliza tipado estricto para evitar conversiones automáticas erróneas (ej. int a float)
# --- MODELOS (PYDANTIC) ---
# Cambiamos StrictFloat por float estándar para evitar errores de parseo JSON
class HabitacionInput(BaseModel):
    numero: str
    tipo: str
    precio_noche: float
    piso: int

class ReservacionInput(BaseModel):
    id_habitacion: str
    huesped: str
    fecha_inicio: str
    fecha_fin: str
    total_estancia: float

# --- ENDPOINTS CRUD ---

# 1. RECURSO: HABITACIONES
@app.get("/api/v1/habitaciones")
def listar_habitaciones() -> dict:
    cursor.execute("SELECT * FROM habitaciones")
    resultados = cursor.fetchall()
    return {"estado": "exito", "datos": resultados}

@app.post("/api/v1/habitaciones", status_code=201)
def crear_habitacion(hab: HabitacionInput) -> dict:
    id_hab = f"HAB-{hab.numero}"
    
    # Validar si existe
    cursor.execute("SELECT * FROM habitaciones WHERE id_habitacion=?", (id_hab,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="La habitación ya existe")
    
    # Inserción con SQL
    cursor.execute(
        "INSERT INTO habitaciones (id_habitacion, numero, tipo, precio_noche, piso, estado) VALUES (?, ?, ?, ?, ?, ?)",
        (id_hab, hab.numero, hab.tipo, hab.precio_noche, hab.piso, "Limpia")
    )
    conn.commit()
    
    return {
        "estado": "exito",
        "datos": {"id_habitacion": id_hab, "numero": hab.numero},
        "mensaje": "Habitación registrada correctamente."
    }

@app.patch("/api/v1/habitaciones/{id_habitacion}/estado")
def cambiar_estado_limpieza(id_habitacion: str, nuevo_estado: str = Body(..., embed=True)) -> dict:
    cursor.execute("UPDATE habitaciones SET estado=? WHERE id_habitacion=?", (nuevo_estado, id_habitacion))
    conn.commit()
    
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Habitación no encontrada")
        
    return {"estado": "exito", "mensaje": f"Habitación {id_habitacion} marcada como {nuevo_estado}"}

# 2. RECURSO: RESERVACIONES
@app.post("/api/v1/reservaciones", status_code=201)
def crear_reservacion(res: ReservacionInput) -> dict:
    # 1. Verificar que la habitación exista y esté disponible
    cursor.execute("SELECT estado FROM habitaciones WHERE id_habitacion=?", (res.id_habitacion,))
    habitacion = cursor.fetchone()
    
    if not habitacion:
        raise HTTPException(status_code=404, detail="La habitación no existe")
    if habitacion["estado"] == "Ocupada":
        raise HTTPException(status_code=400, detail="La habitación ya se encuentra ocupada")
        
    # --- NUEVA LÓGICA DE CÓDIGO MEMORABLE ---
    # Tomamos la primera palabra del nombre del huésped y la ponemos en mayúsculas
    primer_nombre = res.huesped.split()[0].upper()
    
    # Extraemos solo el número de la habitación (quitando el "HAB-")
    numero_hab = res.id_habitacion.replace("HAB-", "")
    
    # Creamos el nuevo ID fácil de recordar (Ejemplo: JUAN-101)
    res_id = f"{primer_nombre}-{numero_hab}"
    # ----------------------------------------
    
    try:
        # Inserción de la reservación
        cursor.execute(
            "INSERT INTO reservaciones (id_reservacion, id_habitacion, huesped, fecha_inicio, fecha_fin, total_estancia, estado_pago) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (res_id, res.id_habitacion, res.huesped, res.fecha_inicio, res.fecha_fin, res.total_estancia, "Pendiente")
        )
    except sqlite3.IntegrityError:
        # Si por alguna razón el código ya existe (mismo nombre y misma habitación)
        raise HTTPException(status_code=400, detail=f"El código {res_id} ya está en uso. Intenta agregar un apellido.")
    
    # Actualizar la habitación a ocupada
    cursor.execute("UPDATE habitaciones SET estado='Ocupada' WHERE id_habitacion=?", (res.id_habitacion,))
    conn.commit()
    
    return {
        "estado": "exito", 
        "datos": {"id_reservacion": res_id}, 
        "mensaje": f"Reservación creada. El código del huésped es: {res_id}"
    }

@app.get("/api/v1/reservaciones/{id_reservacion}")
def obtener_reservacion(id_reservacion: str) -> dict:
    cursor.execute("SELECT * FROM reservaciones WHERE id_reservacion=?", (id_reservacion,))
    reservacion = cursor.fetchone()
    
    if not reservacion:
        raise HTTPException(status_code=404, detail="Reservación no encontrada")
        
    return {"estado": "exito", "datos": reservacion}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
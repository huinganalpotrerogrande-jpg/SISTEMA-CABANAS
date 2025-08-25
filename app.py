import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime

# --- Conexión a base de datos SQLite ---
conn = sqlite3.connect("complejo_cabanas.db", check_same_thread=False)
cursor = conn.cursor()

# --- Crear tablas si no existen ---
def crear_tablas():
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cabanas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        capacidad INTEGER NOT NULL
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS huespedes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        documento TEXT NOT NULL,
        telefono TEXT
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reservas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        huesped_id INTEGER,
        cabana_id INTEGER,
        check_in TEXT,
        check_out TEXT,
        FOREIGN KEY(huesped_id) REFERENCES huespedes(id),
        FOREIGN KEY(cabana_id) REFERENCES cabanas(id)
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pagos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reserva_id INTEGER,
        monto REAL,
        metodo TEXT,
        fecha TEXT,
        FOREIGN KEY(reserva_id) REFERENCES reservas(id)
    )''')

    conn.commit()

crear_tablas()

# --- Funciones CRUD ---
def registrar_huesped(nombre, documento, telefono):
    cursor.execute("INSERT INTO huespedes (nombre, documento, telefono) VALUES (?, ?, ?)", (nombre, documento, telefono))
    conn.commit()

def agregar_cabana(nombre, capacidad):
    cursor.execute("INSERT INTO cabanas (nombre, capacidad) VALUES (?, ?)", (nombre, capacidad))
    conn.commit()

def obtener_huespedes():
    cursor.execute("SELECT id, nombre FROM huespedes")
    return cursor.fetchall()

def obtener_cabanas():
    cursor.execute("SELECT id, nombre FROM cabanas")
    return cursor.fetchall()

def hacer_reserva(huesped_id, cabana_id, check_in, check_out):
    cursor.execute('''
        SELECT * FROM reservas
        WHERE cabana_id = ? AND (
            (check_in <= ? AND check_out > ?) OR
            (check_in < ? AND check_out >= ?) OR
            (check_in >= ? AND check_out <= ?)
        )
    ''', (cabana_id, check_in, check_in, check_out, check_out, check_in, check_out))
    conflictos = cursor.fetchall()
    if conflictos:
        return False
    cursor.execute("INSERT INTO reservas (huesped_id, cabana_id, check_in, check_out) VALUES (?, ?, ?, ?)",
                   (huesped_id, cabana_id, check_in, check_out))
    conn.commit()
    return True

def registrar_pago(reserva_id, monto, metodo):
    fecha = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("INSERT INTO pagos (reserva_id, monto, metodo, fecha) VALUES (?, ?, ?, ?)",
                   (reserva_id, monto, metodo, fecha))
    conn.commit()

def mostrar_reservas():
    query = '''
        SELECT reservas.id, huespedes.nombre AS Huesped, cabanas.nombre AS Cabana, reservas.check_in, reservas.check_out
        FROM reservas
        JOIN huespedes ON reservas.huesped_id = huespedes.id
        JOIN cabanas ON reservas.cabana_id = cabanas.id
    '''
    return pd.read_sql_query(query, conn)

def reporte_mensual(mes, anio):
    query = "SELECT fecha, monto FROM pagos"
    df = pd.read_sql_query(query, conn)
    df['fecha'] = pd.to_datetime(df['fecha'])
    df_filtrado = df[(df['fecha'].dt.month == mes) & (df['fecha'].dt.year == anio)]
    return df_filtrado, df_filtrado['monto'].sum()

# --- Interfaz de usuario (UI) con Streamlit ---
st.set_page_config(page_title="Gestión de Cabañas", layout="centered")
st.title("🏡 Sistema de Gestión de Cabañas")

menu = st.sidebar.selectbox("Selecciona una opción", [
    "Registrar Huésped", "Agregar Cabaña", "Hacer Reserva", "Registrar Pago", "Ver Reservas", "Reporte Mensual"
])

if menu == "Registrar Huésped":
    st.subheader("👤 Registrar nuevo huésped")
    nombre = st.text_input("Nombre")
    documento = st.text_input("Documento")
    telefono = st.text_input("Teléfono")
    if st.button("Registrar"):
        if nombre and documento:
            registrar_huesped(nombre, documento, telefono)
            st.success("Huésped registrado.")
        else:
            st.error("Nombre y Documento son obligatorios.")

elif menu == "Agregar Cabaña":
    st.subheader("🏠 Agregar nueva cabaña")
    nombre = st.text_input("Nombre de la cabaña")
    capacidad = st.number_input("Capacidad", min_value=1, step=1)
    if st.button("Agregar"):
        if nombre and capacidad > 0:
            agregar_cabana(nombre, capacidad)
            st.success("Cabaña agregada.")
        else:
            st.error("Nombre y capacidad válida son requeridos.")

elif menu == "Hacer Reserva":
    st.subheader("📅 Crear nueva reserva")
    huespedes = obtener_huespedes()
    cabanas = obtener_cabanas()
    if huespedes and cabanas:
        huesped = st.selectbox("Huésped", huespedes, format_func=lambda x: f"{x[1]} (ID {x[0]})")
        cabana = st.selectbox("Cabaña", cabanas, format_func=lambda x: f"{x[1]} (ID {x[0]})")
        check_in = st.date_input("Fecha de ingreso")
        check_out = st.date_input("Fecha de salida")
        if st.button("Reservar"):
            if check_in < check_out:
                ok = hacer_reserva(huesped[0], cabana[0], str(check_in), str(check_out))
                if ok:
                    st.success("Reserva registrada.")
                else:
                    st.error("Esa cabaña ya está reservada en esas fechas.")
            else:
                st.error("La fecha de salida debe ser posterior a la de ingreso.")
    else:
        st.warning("Necesitas al menos un huésped y una cabaña para hacer una reserva.")

elif menu == "Registrar Pago":
    st.subheader("💳 Registrar pago")
    reserva_id = st.number_input("ID de reserva", min_value=1, step=1)
    monto = st.number_input("Monto", min_value=0.0, step=0.01)
    metodo = st.selectbox("Método de pago", ["Efectivo", "Tarjeta", "Transferencia", "Otro"])
    if st.button("Registrar Pago"):
        if monto > 0:
            registrar_pago(reserva_id, monto, metodo)
            st.success("Pago registrado.")
        else:
            st.error("El monto debe ser mayor a cero.")

elif menu == "Ver Reservas":
    st.subheader("📋 Reservas")
    df = mostrar_reservas()
    st.dataframe(df)

elif menu == "Reporte Mensual":
    st.subheader("📊 Reporte mensual de ingresos")
    mes = st.number_input("Mes", 1, 12, value=datetime.now().month)
    anio = st.number_input("Año", 2020, 2100, value=datetime.now().year)
    df, total = reporte_mensual(mes, anio)
    st.dataframe(df)
    st.success(f"Total ingresado: ${total:.2f}")
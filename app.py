def borrar_cabana(cabana_id):
    # Antes de borrar, asegurarse que no tenga reservas para evitar errores
    cursor.execute("SELECT COUNT(*) FROM reservas WHERE cabana_id = ?", (cabana_id,))
    count = cursor.fetchone()[0]
    if count > 0:
        return False, "No se puede borrar la cabaña porque tiene reservas activas."
    
    cursor.execute("DELETE FROM cabanas WHERE id = ?", (cabana_id,))
    conn.commit()
    return True, "Cabaña borrada exitosamente."

if menu == "Borrar Cabaña":
    st.subheader("🗑️ Borrar Cabaña")
    cabanas = obtener_cabanas()
    if not cabanas:
        st.warning("No hay cabañas para borrar.")
    else:
        cabana = st.selectbox("Selecciona la cabaña a borrar", cabanas, format_func=lambda x: f"{x[1]} (ID {x[0]})")
        if st.button("Borrar Cabaña"):
            ok, msg = borrar_cabana(cabana[0])
            if ok:
                st.success(msg)
            else:
                st.error(msg)


import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

# --- Conexión a base de datos SQLite ---
conn = sqlite3.connect("complejo_cabanas.db", check_same_thread=False)
cursor = conn.cursor()

# --- Creación de tablas ---
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


def disponibilidad_cabanas(fecha_inicio, fecha_fin):
    cursor.execute("SELECT id, nombre FROM cabanas")
    cabanas = cursor.fetchall()

    fechas = pd.date_range(start=fecha_inicio, end=fecha_fin)
    disponibilidad = pd.DataFrame(index=[c[1] for c in cabanas], columns=fechas.strftime('%d/%m'))
    disponibilidad[:] = "✅"

    for cabana_id, cabana_nombre in cabanas:
        cursor.execute('''
            SELECT check_in, check_out FROM reservas
            WHERE cabana_id = ?
        ''', (cabana_id,))
        reservas = cursor.fetchall()

        for check_in, check_out in reservas:
            r_inicio = pd.to_datetime(check_in)
            r_fin = pd.to_datetime(check_out) - pd.Timedelta(days=1)
            ocupadas = pd.date_range(start=r_inicio, end=r_fin)
            for fecha in ocupadas:
                col = fecha.strftime('%d/%m')
                if col in disponibilidad.columns:
                    disponibilidad.loc[cabana_nombre, col] = "❌"

    return disponibilidad


import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

# --- Conexión a base de datos SQLite ---
conn = sqlite3.connect("complejo_cabanas.db", check_same_thread=False)
cursor = conn.cursor()

# --- Funciones base (tabla, reservas, huespedes, etc.) ---
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

def obtener_cabanas():
    cursor.execute("SELECT id, nombre FROM cabanas")
    return cursor.fetchall()

def obtener_huespedes():
    cursor.execute("SELECT id, nombre FROM huespedes")
    return cursor.fetchall()

def reserva_existe(reserva_id):
    cursor.execute("SELECT 1 FROM reservas WHERE id = ?", (reserva_id,))
    return cursor.fetchone() is not None

def registrar_pago(reserva_id, monto, metodo):
    fecha = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("INSERT INTO pagos (reserva_id, monto, metodo, fecha) VALUES (?, ?, ?, ?)",
                   (reserva_id, monto, metodo, fecha))
    conn.commit()

from datetime import datetime, timedelta

from datetime import datetime, timedelta

elif menu == "Hacer Reserva":
    st.subheader("📅 Crear nueva reserva")

    huespedes = obtener_huespedes()
    cabanas = obtener_cabanas()

    if huespedes and cabanas:
        huesped = st.selectbox("Huésped", huespedes, format_func=lambda x: f"{x[1]} (ID {x[0]})")
        cabana = st.selectbox("Cabaña", cabanas, format_func=lambda x: f"{x[1]} (ID {x[0]})")

        hoy = datetime.now().date()
        rango_inicio = hoy
        rango_fin = hoy + timedelta(days=30)

        # Mostrar tabla de disponibilidad
        tabla = disponibilidad_cabanas(rango_inicio, rango_fin)

        st.markdown(f"**🗓️ Disponibilidad de {cabana[1]} (próximos 30 días)**")

        def resaltar_celda(val):
            if val == "❌":
                return 'background-color: red; color: white; font-weight: bold;'
            elif val == "✅":
                return 'background-color: lightgreen; color: black;'
            return ''

        styled_table = tabla.loc[[cabana[1]]].style.applymap(resaltar_celda)
        st.table(styled_table)

        check_in = st.date_input("Fecha de ingreso", min_value=hoy)
        check_out = st.date_input("Fecha de salida", min_value=check_in + timedelta(days=1))

        # Verificar conflicto
        conflicto = False
        if check_in < check_out:
            dias = pd.date_range(start=check_in, end=check_out - timedelta(days=1))
            for dia in dias:
                col = dia.strftime('%d/%m')
                if col in tabla.columns and tabla.loc[cabana[1], col] == "❌":
                    conflicto = True
                    break

        if conflicto:
            st.warning("⚠️ El rango seleccionado incluye días ocupados.")

        if st.button("Reservar"):
            if conflicto:
                st.error("No se puede reservar: incluye días ocupados.")
            else:
                ok = hacer_reserva(huesped[0], cabana[0], str(check_in), str(check_out))
                if ok:
                    st.success("✅ Reserva registrada.")
                else:
                    st.error("Error al registrar la reserva.")
    else:
        st.warning("Necesitas al menos un huésped y una cabaña para hacer una reserva.")




def disponibilidad_cabanas(fecha_inicio, fecha_fin):
    cursor.execute("SELECT id, nombre FROM cabanas")
    cabanas = cursor.fetchall()
    fechas = pd.date_range(start=fecha_inicio, end=fecha_fin)
    disponibilidad = pd.DataFrame(index=[c[1] for c in cabanas], columns=fechas.strftime('%d/%m'))
    disponibilidad[:] = "✅"

    for cabana_id, cabana_nombre in cabanas:
        cursor.execute('''
            SELECT check_in, check_out FROM reservas
            WHERE cabana_id = ?
        ''', (cabana_id,))
        reservas = cursor.fetchall()

        for check_in, check_out in reservas:
            r_inicio = pd.to_datetime(check_in)
            r_fin = pd.to_datetime(check_out) - pd.Timedelta(days=1)
            ocupadas = pd.date_range(start=r_inicio, end=r_fin)
            for fecha in ocupadas:
                col = fecha.strftime('%d/%m')
                if col in disponibilidad.columns:
                    disponibilidad.loc[cabana_nombre, col] = "❌"
    return disponibilidad

def mostrar_reservas():
    query = '''
        SELECT reservas.id, huespedes.nombre AS Huesped, cabanas.nombre AS Cabana, reservas.check_in, reservas.check_out
        FROM reservas
        JOIN huespedes ON reservas.huesped_id = huespedes.id
        JOIN cabanas ON reservas.cabana_id = cabanas.id
    '''
    return pd.read_sql_query(query, conn)

# --- Streamlit UI ---

st.set_page_config(page_title="Gestión de Cabañas", layout="centered")
st.title("🏡 Sistema de Gestión de Cabañas")

# --- Login simple ---
def login():
    st.subheader("🔐 Iniciar sesión")
    with st.form("login_form"):
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Ingresar")
        if submitted:
            if username == "admin" and password == "1234":
                st.session_state['logged_in'] = True
                st.success("Acceso concedido")
            else:
                st.error("Usuario o contraseña incorrectos.")

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if not st.session_state['logged_in']:
    login()
    st.stop()

menu = st.sidebar.selectbox("Selecciona una opción", [
    "Registrar Huésped", "Agregar Cabaña", "Hacer Reserva", "Registrar Pago", "Ver Reservas", "Reporte Mensual"
])

if menu == "Hacer Reserva":
    st.info("🔍 Verificá los días disponibles en la tabla antes de elegir fechas.")
    st.subheader("📅 Crear nueva reserva")

    huespedes = obtener_huespedes()
    cabanas = obtener_cabanas()

    if huespedes and cabanas:
        huesped = st.selectbox("Huésped", huespedes, format_func=lambda x: f"{x[1]} (ID {x[0]})")
        cabana = st.selectbox("Cabaña", cabanas, format_func=lambda x: f"{x[1]} (ID {x[0]})")

        hoy = datetime.now().date()
        rango_inicio = hoy
        rango_fin = hoy + timedelta(days=30)

        tabla = disponibilidad_cabanas(rango_inicio, rango_fin)

        st.markdown(f"🗓️ <b>Disponibilidad de {cabana[1]}</b> (próximos 30 días):", unsafe_allow_html=True)
        
        # Función para colorear celdas
        def color_disponibilidad(val):
            if val == "❌":
                return 'background-color: #f44336; color: white; font-weight: bold;'  # rojo fuerte
            elif val == "✅":
                return 'background-color: #c8e6c9; color: black;'  # verde claro
            return ''

        styled = tabla.loc[[cabana[1]]].style.applymap(color_disponibilidad).set_tooltips(
            tooltip=tabla.loc[[cabana[1]]].replace({"❌": "Ocupado", "✅": "Disponible"})
        )

        st.dataframe(styled, height=150)

        check_in = st.date_input("Fecha de ingreso", min_value=hoy)
        check_out = st.date_input("Fecha de salida", min_value=check_in + timedelta(days=1))

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

elif menu == "Ver Reservas":
    st.subheader("📋 Reservas")
    df = mostrar_reservas()

    cabanas = obtener_cabanas()
    filtro_cabana = st.selectbox("Filtrar por cabaña", options=["Todas"] + [c[1] for c in cabanas])
    if filtro_cabana != "Todas":
        df = df[df["Cabana"] == filtro_cabana]

    st.dataframe(df)

# Aquí seguirías con los otros menús (Registrar Huésped, Agregar Cabaña, Registrar Pago, Reporte Mensual) con la estructura que ya tienes.


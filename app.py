import os
from flask import Flask, render_template, request, redirect, url_for, flash, session,jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import mysql.connector
from mysql.connector import Error
from hashlib import sha256
import random
import uuid 
from datetime import timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Clave secreta para manejar sesiones en Flask (¡Cámbiala por una segura!)
app.permanent_session_lifetime = timedelta(days=1)
socketio = SocketIO(app)

# Configuración de la base de datos
db_config = {
    'host': '',     # Dirección IP del servidor de base de datos
    'user': '',            # Usuario de la base de datos
    'password': '',      # Contraseña del usuario
    'database': ''         # Nombre de la base de datos
}

# Función para establecer conexión con la base de datos
def get_db_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        print("✅ Conexión exitosa a la base de datos.")
        return connection  # Devuelve la conexión activa
    except mysql.connector.Error as err:
        print(f"❌ Error al conectar a la base de datos: {err}")
        return None  # Devuelve None si hay un error

# Función genérica para ejecutar consultas SQL (reduce repetición de código)
def ejecutar_consulta(query, params=None, fetch_one=False, commit=False):
    """
    Ejecuta una consulta SQL y maneja la conexión automáticamente.
    - query: Consulta SQL a ejecutar.
    - params: Parámetros para la consulta (tupla o lista).
    - fetch_one: Si es True, devuelve un solo resultado. Si es False, devuelve todos.
    - commit: Si es True, se ejecuta un commit (para INSERT, UPDATE, DELETE).
    """
    connection = get_db_connection()
    if not connection:
        return None

    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params or ())
            if commit:
                connection.commit()  # Guarda los cambios en la base de datos
                return True
            return cursor.fetchone() if fetch_one else cursor.fetchall()  # Devuelve los resultados de la consulta
    except mysql.connector.Error as err:
        print(f"❌ Error en la consulta SQL: {err}")
        return None  # En caso de error, devuelve None
    finally:
        connection.close()  # Cierra la conexión siempre al final

# Función para iniciar sesión
def iniciar_sesion(username, dni):
    """
    Busca un usuario en la base de datos y devuelve su ID y username si las credenciales son correctas.
    """
    dni_hash = sha256(dni.encode()).hexdigest()  # Encripta el DNI con SHA-256
    query = "SELECT id, username FROM usuarios WHERE username = %s AND dni = %s"
    return ejecutar_consulta(query, (username, dni_hash), fetch_one=True)

# Función para registrar un nuevo usuario
def registrar_usuario(username, dni, mayor_edad):
    """
    Registra un nuevo usuario en la base de datos si el username o DNI no están en uso.
    """
    dni_hash = sha256(dni.encode()).hexdigest()  # Encripta el DNI antes de guardarlo

    # Verifica si el usuario ya existe
    if ejecutar_consulta("SELECT id FROM usuarios WHERE username = %s OR dni = %s", (username, dni_hash), fetch_one=True):
        print("❌ Error: El usuario o DNI ya está registrado.")
        return False

    # Inserta un nuevo usuario
    query = "INSERT INTO usuarios (username, dni, mayor_edad) VALUES (%s, %s, %s)"
    if ejecutar_consulta(query, (username, dni_hash, mayor_edad), commit=True):
        print("✅ Usuario registrado con éxito.")
        return True

    return False  # Devuelve False si hubo un error en el registro

def generar_codigo_salas():


#Ruta de página de inicio (index.html)
@app.route('/')
def index():
    return render_template('index.html')

# Ruta para el registro de usuarios
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        # Obtiene los datos del formulario, asegurándose de eliminar espacios en blanco
        username = request.form.get('username', '').strip()
        dni = request.form.get('dni', '').strip()
        mayor_edad = 'mayor_edad' in request.form  # Devuelve True si la casilla está marcada

        # Intenta registrar al usuario
        if registrar_usuario(username, dni, mayor_edad):
            flash('✅ Usuario registrado con éxito.', 'success')
            return redirect(url_for('login'))  # Redirige al login si se registró con éxito

        flash('❌ Error: El usuario ya existe o hubo un problema en el registro.', 'error')

    return render_template('registro.html')  # Muestra el formulario de registro

# Ruta para el inicio de sesión
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Obtiene los datos del formulario
        username = request.form.get('username', '').strip()
        dni = request.form.get('dni', '').strip()

        # Intenta iniciar sesión
        usuario = iniciar_sesion(username, dni)
        if usuario:
            # Guarda la información del usuario en la sesión
            session['usuario_id'], session['usuario_nombre'] = usuario
            flash(f'✅ Bienvenido, {usuario[1]}!', 'success')
            return redirect(url_for('dashboard'))  # Redirige al dashboard

        flash('❌ Error: Usuario o contraseña incorrectos.', 'error')

    return render_template('login.html')  # Muestra el formulario de login

@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

# Ruta para crear una sala
@app.route('/crear_sala')
def crear_sala():
    sala_id = str(uuid.uuid4())[:8]  # Genera un ID único corto
    return {'sala_id': sala_id}

# Ruta para unirse o crear sala
@app.route('/unir_crear_sala')
def unir_crear_sala():
    return render_template('unir_crear_sala.html')


# Eventos de Socket.IO
@socketio.on('unirse_bingo')
def unirse_bingo(data):
    sala = data['sala']
    join_room(sala)
    emit('jugador_unido', {'mensaje': f"{session['usuario_nombre']} se ha unido a la sala {sala}"}, room=sala)

@socketio.on('generar_numero')
def generar_numero(data):
    sala = data['sala']
    numero = random.randint(1, 99)
    emit('nuevo_numero', {'numero': numero}, room=sala)

if __name__ == '__main__':
    socketio.run(app, debug=True)
import os
import random
import uuid
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import psycopg2
from psycopg2.extras import RealDictCursor
from hashlib import sha256
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.permanent_session_lifetime = timedelta(days=1)
socketio = SocketIO(app)

# Configuración de la base de datos desde DATABASE_URL (formato de Render)
def get_db_connection():
    try:
        result = urlparse(os.getenv("DATABASE_URL"))
        conn = psycopg2.connect(
            dbname=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port,
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        print(f"❌ Error al conectar a PostgreSQL: {e}")
        return None

def ejecutar_consulta(query, params=None, fetch_one=False, commit=False):
    connection = get_db_connection()
    if not connection:
        return None

    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params or ())
            if commit:
                connection.commit()
                return True
            return cursor.fetchone() if fetch_one else cursor.fetchall()
    except Exception as err:
        print(f"❌ Error en la consulta SQL: {err}")
        return None
    finally:
        connection.close()

# Lógica de sesión y usuarios
def login_required(func):
    def wrapped(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Por favor inicia sesión para acceder a esta página', 'error')
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    wrapped.__name__ = func.__name__
    return wrapped

def iniciar_sesion(username, dni):
    dni_hash = sha256(dni.encode()).hexdigest()
    query = "SELECT id, username FROM usuarios WHERE username = %s AND dni = %s"
    return ejecutar_consulta(query, (username, dni_hash), fetch_one=True)

def registrar_usuario(username, dni, mayor_edad):
    dni_hash = sha256(dni.encode()).hexdigest()
    if ejecutar_consulta(
        "SELECT id FROM usuarios WHERE username = %s OR dni = %s",
        (username, dni_hash),
        fetch_one=True
    ):
        return False
    return ejecutar_consulta(
        "INSERT INTO usuarios (username, dni, mayor_edad) VALUES (%s, %s, %s)",
        (username, dni_hash, mayor_edad),
        commit=True
    )

def generar_codigo_sala():
    """Genera un ID único de 8 caracteres para la sala."""
    return uuid.uuid4().hex[:8].upper()

def generar_carton_bingo():
    """
    Genera un cartón de bingo de 5x5 con 13 huecos en blanco.
    Cada columna tiene el rango de números especificado.
    La primera fila es la palabra BINGO.
    """
    # Rango de cada columna
    rangos = [
        list(range(1, 20)),    # B
        list(range(20, 40)),   # I
        list(range(40, 60)),   # N
        list(range(60, 80)),   # G
        list(range(80, 100)),  # O
    ]
    # Crear las 5 columnas, cada una con 5 números únicos
    columnas = [random.sample(rango, 5) for rango in rangos]
    # Construir la matriz 5x5 (sin encabezado)
    matriz = [[columnas[col][fila] for col in range(5)] for fila in range(5)]

    # Seleccionar 13 posiciones únicas para dejar en blanco
    posiciones = [(f, c) for f in range(5) for c in range(5)]
    huecos_blancos = random.sample(posiciones, 13)
    for f, c in huecos_blancos:
        matriz[f][c] = ""

    # Agregar encabezado BINGO
    carton = [['B', 'I', 'N', 'G', 'O']]
    carton.extend(matriz)
    return carton

def generar_cartones_usuario(num_cartones):
    if not 1 <= num_cartones <= 5:
        raise ValueError("Solo puedes generar entre 1 y 5 cartones.")
    return [generar_carton_bingo() for _ in range(num_cartones)]

# Rutas Flask
@app.route('/')
def index():
    if 'usuario_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        dni = request.form.get('dni', '').strip()
        mayor_edad = 'mayor_edad' in request.form

        if not username or not dni:
            flash('Todos los campos son obligatorios', 'error')
        elif not mayor_edad:
            flash('Debes ser mayor de edad para registrarte.', 'error')
        elif registrar_usuario(username, dni, mayor_edad):
            flash('Registro exitoso. Por favor inicia sesión.', 'success')
            return redirect(url_for('login'))
        else:
            flash('El usuario o DNI ya están registrados', 'error')

    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        dni = request.form.get('dni', '').strip()

        usuario = iniciar_sesion(username, dni)
        if usuario:
            session.permanent = True
            session['usuario_id'] = usuario['id']
            session['usuario_nombre'] = usuario['username']
            flash(f'Bienvenido, {usuario["username"]}!', 'success')
            return redirect(url_for('dashboard'))
        
        flash('Usuario o DNI incorrectos', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión correctamente', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    cartones = None
    if request.method == 'POST':
        try:
            cantidad_cartones = int(request.form.get('cantidad_cartones', 1))
            cartones = generar_cartones_usuario(cantidad_cartones)
        except Exception as e:
            flash(str(e), 'error')
    stats = ejecutar_consulta(
        """SELECT 
            (SELECT COUNT(*) FROM salas WHERE creador_id = %s) AS salas_creadas,
            (SELECT COUNT(*) FROM jugadores_sala WHERE usuario_id = %s) AS salas_participadas""",
        (session['usuario_id'], session['usuario_id']),
        fetch_one=True
    )
    return render_template('dashboard.html', stats=stats, usuario_id=session['usuario_id'], cartones=cartones)

@app.route('/multijugador')
@login_required
def multijugador():
    return render_template('multijugador.html')

@app.route('/crear_sala')
@login_required
def crear_sala():
    codigo = generar_codigo_sala()
    if ejecutar_consulta(
        "INSERT INTO salas (id, creador_id) VALUES (%s, %s)",
        (codigo, session['usuario_id']),
        commit=True
    ):
        ejecutar_consulta(
            "INSERT INTO jugadores_sala (sala_id, usuario_id) VALUES (%s, %s)",
            (codigo, session['usuario_id']),
            commit=True
        )
        return jsonify({
            'success': True,
            'sala_id': codigo,
            'message': 'Sala creada exitosamente'
        })
    return jsonify({
        'success': False,
        'message': 'Error al crear la sala'
    }), 500

# Socket.IO
@socketio.on('unirse_bingo')
def manejar_unirse_bingo(data):
    if 'usuario_id' not in session:
        return
    sala = data['sala']
    join_room(sala)
    emit('jugador_unido', {
        'usuario': session['usuario_nombre'],
        'mensaje': f"{session['usuario_nombre']} se ha unido a la sala"
    }, room=sala)

@socketio.on('generar_numero')
def manejar_generar_numero(data):
    sala = data['sala']
    es_creador = ejecutar_consulta(
        "SELECT 1 FROM salas WHERE id = %s AND creador_id = %s",
        (sala, session['usuario_id']),
        fetch_one=True
    )
    if not es_creador:
        return
    numeros_llamados = ejecutar_consulta(
        "SELECT numero FROM numeros_llamados WHERE sala_id = %s",
        (sala,)
    )
    numeros_disponibles = [n for n in range(1, 100) if n not in [num['numero'] for num in numeros_llamados]]
    if not numeros_disponibles:
        emit('juego_terminado', {'mensaje': 'Todos los números han sido llamados'}, room=sala)
        return
    nuevo_numero = random.choice(numeros_disponibles)
    if ejecutar_consulta(
        "INSERT INTO numeros_llamados (sala_id, numero) VALUES (%s, %s)",
        (sala, nuevo_numero),
        commit=True
    ):
        emit('nuevo_numero', {
            'numero': nuevo_numero,
            'llamado_por': session['usuario_nombre']
        }, room=sala)

# Ejecutar la app (Render friendly)
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

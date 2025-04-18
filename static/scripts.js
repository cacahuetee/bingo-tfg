// bingo.js

// ========== SOCKET.IO SETUP ==========
const socket = io(); // Asegúrate de tener socket.io.js cargado

// ========== SALAS ==========

function crearSala(callback) {
    socket.emit('crear_sala', {}, (response) => {
        if (response.success) {
            alert('Sala creada: ' + response.sala_id);
            if (callback) callback(response.sala_id);
        } else {
            alert('Error al crear la sala');
        }
    });
}

function unirseSala(salaId) {
    socket.emit('unirse_bingo', { sala: salaId });
}

// ========== CARTONES ==========

function generarCartonBingo() {
    // Rangos de columnas
    const rangos = [
        Array.from({ length: 19 }, (_, i) => i + 1),      // B: 1-19
        Array.from({ length: 20 }, (_, i) => i + 20),     // I: 20-39
        Array.from({ length: 20 }, (_, i) => i + 40),     // N: 40-59
        Array.from({ length: 20 }, (_, i) => i + 60),     // G: 60-79
        Array.from({ length: 20 }, (_, i) => i + 80)      // O: 80-99
    ];
    // Selecciona 5 números únicos por columna
    const columnas = rangos.map(rango => {
        let arr = [...rango];
        let col = [];
        for (let i = 0; i < 5; i++) {
            const idx = Math.floor(Math.random() * arr.length);
            col.push(arr.splice(idx, 1)[0]);
        }
        return col;
    });
    // Construir matriz 5x5
    let matriz = [];
    for (let fila = 0; fila < 5; fila++) {
        matriz[fila] = [];
        for (let col = 0; col < 5; col++) {
            matriz[fila][col] = columnas[col][fila];
        }
    }
    // 13 huecos en blanco aleatorios
    let posiciones = [];
    for (let f = 0; f < 5; f++) for (let c = 0; c < 5; c++) posiciones.push([f, c]);
    let blancos = [];
    while (blancos.length < 13) {
        let idx = Math.floor(Math.random() * posiciones.length);
        let pos = posiciones.splice(idx, 1)[0];
        blancos.push(pos);
        matriz[pos[0]][pos[1]] = '';
    }
    // Agregar encabezado
    matriz.unshift(['B', 'I', 'N', 'G', 'O']);
    return matriz;
}

function generarCartonesUsuario(n) {
    if (n < 1 || n > 5) {
        alert("Solo puedes generar entre 1 y 5 cartones.");
        return [];
    }
    let cartones = [];
    for (let i = 0; i < n; i++) {
        cartones.push(generarCartonBingo());
    }
    return cartones;
}

// ========== MOSTRAR CARTONES EN HTML ==========

function mostrarCartones(cartones, contenedorId) {
    const contenedor = document.getElementById(contenedorId);
    contenedor.innerHTML = '';
    cartones.forEach((carton, idx) => {
        let tabla = document.createElement('table');
        tabla.className = 'carton-bingo';
        carton.forEach((fila, i) => {
            let tr = document.createElement('tr');
            fila.forEach((celda, j) => {
                let tag = i === 0 ? 'th' : 'td';
                let cell = document.createElement(tag);
                cell.textContent = celda;
                if (celda === '') cell.className = 'blanco';
                tr.appendChild(cell);
            });
            tabla.appendChild(tr);
        });
        let titulo = document.createElement('h4');
        titulo.textContent = 'Cartón #' + (idx + 1);
        contenedor.appendChild(titulo);
        contenedor.appendChild(tabla);
    });
}

// ========== EVENTOS DE UI ==========

document.getElementById('btnCrearSala')?.addEventListener('click', () => {
    crearSala((salaId) => {
        document.getElementById('salaId').textContent = salaId;
    });
});

document.getElementById('btnUnirseSala')?.addEventListener('click', () => {
    const salaId = document.getElementById('inputSalaId').value.trim();
    if (salaId) unirseSala(salaId);
});

document.getElementById('btnGenerarCartones')?.addEventListener('click', () => {
    const n = parseInt(document.getElementById('inputNumCartones').value, 10);
    const cartones = generarCartonesUsuario(n);
    mostrarCartones(cartones, 'contenedorCartones');
});

// ========== ESTILOS SUGERIDOS (agrega en tu CSS) ==========
/*
.carton-bingo { border-collapse: collapse; margin: 10px 0; }
.carton-bingo th, .carton-bingo td { border: 1px solid #222; width: 32px; height: 32px; text-align: center; }
.carton-bingo .blanco { background: #eee; }
*/


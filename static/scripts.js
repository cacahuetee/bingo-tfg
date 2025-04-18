// ========== SOCKET.IO SETUP ==========
const socket = io(); // Asegúrate de tener socket.io.js cargado

// ========== SALAS ==========

// Usar la ruta HTTP Flask para crear sala
function crearSala(callback) {
    fetch('/crear_sala')
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                alert('Sala creada: ' + data.sala_id);
                if (callback) callback(data.sala_id);
                unirseSala(data.sala_id);
            } else {
                alert('Error al crear la sala: ' + data.message);
            }
        })
        .catch(err => {
            console.error('Error al crear sala:', err);
            alert('No se pudo crear la sala');
        });
}

function unirseSala(salaId) {
    socket.emit('unirse_bingo', { sala: salaId });
    console.log(`Unido a la sala: ${salaId}`);
}

// ========== ESCUCHAR EVENTOS DEL SERVIDOR ==========

socket.on('jugador_unido', data => {
    alert(data.mensaje); // O puedes mostrarlo en el DOM
});

socket.on('nuevo_numero', data => {
    alert(`Nuevo número: ${data.numero} (llamado por ${data.llamado_por})`);
});

socket.on('juego_terminado', data => {
    alert(data.mensaje);
});

// ========== CARTONES ==========

function generarCartonBingo() {
    const rangos = [
        Array.from({ length: 19 }, (_, i) => i + 1),      // B
        Array.from({ length: 20 }, (_, i) => i + 20),     // I
        Array.from({ length: 20 }, (_, i) => i + 40),     // N
        Array.from({ length: 20 }, (_, i) => i + 60),     // G
        Array.from({ length: 20 }, (_, i) => i + 80)      // O
    ];

    const columnas = rangos.map(rango => {
        let col = [];
        let copia = [...rango];
        for (let i = 0; i < 5; i++) {
            const idx = Math.floor(Math.random() * copia.length);
            col.push(copia.splice(idx, 1)[0]);
        }
        return col;
    });

    let matriz = [];
    for (let fila = 0; fila < 5; fila++) {
        matriz[fila] = [];
        for (let col = 0; col < 5; col++) {
            matriz[fila][col] = columnas[col][fila];
        }
    }

    let posiciones = [];
    for (let f = 0; f < 5; f++) for (let c = 0; c < 5; c++) posiciones.push([f, c]);
    let blancos = [];
    while (blancos.length < 13) {
        let idx = Math.floor(Math.random() * posiciones.length);
        let pos = posiciones.splice(idx, 1)[0];
        blancos.push(pos);
        matriz[pos[0]][pos[1]] = '';
    }

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

// ========== MOSTRAR CARTONES ==========
function mostrarCartones(cartones, contenedorId) {
    const contenedor = document.getElementById(contenedorId);
    contenedor.innerHTML = '';
    cartones.forEach((carton, idx) => {
        let tabla = document.createElement('table');
        tabla.className = 'carton-bingo';
        carton.forEach((fila, i) => {
            let tr = document.createElement('tr');
            fila.forEach(celda => {
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

// ========== EVENTOS UI ==========
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

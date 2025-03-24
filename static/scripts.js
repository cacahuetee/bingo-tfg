// Conexión con socket.io
const socket = io();

// Mostrar la sección seleccionada (crear o unirse)
function mostrarSeccion(seccion) {
    document.getElementById('opciones').style.display = 'none'; // Oculta las opciones
    document.getElementById('crear').style.display = seccion === 'crear' ? 'block' : 'none';
    document.getElementById('unirse').style.display = seccion === 'unirse' ? 'block' : 'none';
}

// Función para crear una nueva sala
function createRoom() {
    fetch('/crear_sala')  // Llama a la ruta Flask para crear una sala
        .then(response => response.json())
        .then(data => {
            const newRoomId = data.sala_id;  // Obtiene el ID de la sala creada
            socket.emit("unirse_bingo", { sala: newRoomId });  // Se une a la sala

            // Muestra el ID de la sala creada
            document.getElementById("sala-id").textContent = newRoomId;
            document.getElementById("sala-creada").style.display = "block";
        })
        .catch(error => console.error("Error al crear sala:", error));
}

// Función para unirse a una sala
function joinRoom() {
    const bingoId = document.getElementById("bingoId").value;  // Obtiene el ID de la sala
    if (bingoId) {
        socket.emit("unirse_bingo", { sala: bingoId });  // Se une a la sala

        // Muestra el ID de la sala a la que se unió
        document.getElementById("sala-unida-id").textContent = bingoId;
        document.getElementById("sala-unida").style.display = "block";
    } else {
        alert("Por favor, introduce un ID de sala válido.");
    }
}

// Escuchar cuando un jugador se une a la sala
socket.on("jugador_unido", (data) => {
    alert(data.mensaje);
});
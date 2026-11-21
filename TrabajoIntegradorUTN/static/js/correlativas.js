// Al tocar una materia del árbol, el panel lateral muestra su detalle.
// Los datos salen de los atributos data-* que el template pone en cada <summary>.
document.querySelectorAll(".nodo-correlativa > summary").forEach(function (resumen) {
    resumen.addEventListener("click", function () {
        const datos = resumen.dataset;

        document.querySelectorAll(".nodo-correlativa > summary.seleccionada")
            .forEach(function (anterior) { anterior.classList.remove("seleccionada"); });
        resumen.classList.add("seleccionada");

        document.getElementById("detalle-vacio").hidden = true;
        document.getElementById("detalle").hidden = false;
        document.getElementById("detalle-nombre").textContent = datos.nombre;
        document.getElementById("detalle-mensaje").textContent = datos.mensaje;

        const estado = document.getElementById("detalle-estado");
        estado.textContent = datos.texto;
        estado.className = "badge text-bg-" + datos.color;

        const lista = document.getElementById("detalle-pendientes");
        lista.replaceChildren();
        const pendientes = datos.pendientes ? datos.pendientes.split("|") : [];
        pendientes.forEach(function (texto) {
            const item = document.createElement("li");
            item.textContent = texto;
            lista.appendChild(item);
        });
        document.getElementById("detalle-pendientes-bloque").hidden = pendientes.length === 0;

        const boton = document.getElementById("detalle-boton");
        boton.hidden = !datos.inscribir;
        boton.href = datos.inscribir || "#";
    });
});

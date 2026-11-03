(function () {
    const form = document.getElementById('formPlanilla');
    if (!form) return;

    const colId = document.getElementById('colId');
    const estado = document.getElementById('estadoCambios');
    let hayCambios = false;
    let enviando = false;

    // --- Validación visual y aviso de cambios sin guardar ---
    function validar(input) {
        const v = input.value.trim().replace(',', '.');
        const ok = v === '' || (!isNaN(v) && Number(v) >= 1 && Number(v) <= 10);
        input.classList.toggle('is-invalid', !ok);
    }
    function marcarCambio(el) {
        el.classList.add('celda-cambiada');
        if (!hayCambios) {
            hayCambios = true;
            estado.innerHTML = '<i class="bi bi-circle-fill text-warning me-1" style="font-size:.6rem"></i>Cambios sin guardar';
        }
    }
    form.querySelectorAll('.planilla-input').forEach(function (input) {
        input.addEventListener('input', function () { validar(input); marcarCambio(input); });
        // Enter = bajar a la misma columna del alumno siguiente (como en una planilla)
        input.addEventListener('keydown', function (e) {
            if (e.key !== 'Enter') return;
            e.preventDefault();
            const td = input.closest('td');
            const indice = Array.from(td.parentNode.children).indexOf(td);
            let fila = td.parentNode.nextElementSibling;
            while (fila) {
                const siguiente = fila.children[indice].querySelector('.planilla-input');
                if (siguiente) { siguiente.focus(); siguiente.select(); return; }
                fila = fila.nextElementSibling;
            }
        });
    });
    form.querySelectorAll('.planilla-select').forEach(function (sel) {
        sel.addEventListener('change', function () { marcarCambio(sel); });
    });
    form.addEventListener('submit', function () { enviando = true; });
    window.addEventListener('beforeunload', function (e) {
        if (hayCambios && !enviando) { e.preventDefault(); e.returnValue = ''; }
    });

    // --- Modal agregar / editar columna ---
    const modal = document.getElementById('modalColumna');
    const lista = document.getElementById('listaAlumnos');
    const todos = document.getElementById('alcanceTodos');
    const algunos = document.getElementById('alcanceAlgunos');
    const checks = modal.querySelectorAll('.js-alumno-col');

    function actualizarLista() { lista.classList.toggle('d-none', !algunos.checked); }
    todos.addEventListener('change', actualizarLista);
    algunos.addEventListener('change', actualizarLista);
    document.getElementById('marcarTodos').addEventListener('click', function (e) { e.preventDefault(); checks.forEach(c => c.checked = true); });
    document.getElementById('marcarNinguno').addEventListener('click', function (e) { e.preventDefault(); checks.forEach(c => c.checked = false); });

    modal.addEventListener('show.bs.modal', function (event) {
        const b = event.relatedTarget;
        const editar = b && b.dataset.modo === 'editar';
        document.getElementById('modalColumnaTitulo').textContent = editar ? 'Editar evaluación' : 'Agregar evaluación';
        document.getElementById('btnGuardarColumna').textContent = editar ? 'Guardar cambios' : 'Agregar columna';
        colId.value = editar ? b.dataset.colId : '';
        if (editar) {
            document.getElementById('colTipo').value = b.dataset.tipo;
            document.getElementById('colNombre').value = b.dataset.nombre;
            document.getElementById('colFecha').value = b.dataset.fecha;
            const elegidos = b.dataset.alumnos ? b.dataset.alumnos.split(',') : [];
            (b.dataset.todos === '1' ? todos : algunos).checked = true;
            checks.forEach(c => c.checked = elegidos.includes(c.value));
        } else {
            document.getElementById('colNombre').value = '';
            document.getElementById('colFecha').value = document.getElementById('colFecha').defaultValue;  // hoy
            todos.checked = true;
            checks.forEach(c => c.checked = true);
        }
        actualizarLista();
    });
    modal.addEventListener('shown.bs.modal', function () { document.getElementById('colNombre').focus(); });
    // Enter dentro del modal = guardar la columna (y no "Guardar planilla")
    modal.querySelectorAll('input').forEach(function (el) {
        el.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') { e.preventDefault(); document.getElementById('btnGuardarColumna').click(); }
        });
    });

    // --- Modal eliminar columna ---
    document.getElementById('modalEliminarColumna').addEventListener('show.bs.modal', function (event) {
        colId.value = event.relatedTarget.dataset.colId;
        this.querySelector('.js-titulo').textContent = '«' + event.relatedTarget.dataset.titulo + '»';
    });
})();

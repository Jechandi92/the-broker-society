# agent/panel.py — Panel web para que el equipo intervenga en conversaciones
# Generado por AgentKit

PANEL_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Panel — Lea (The Broker Society)</title>
<style>
  * { box-sizing: border-box; font-family: Arial, sans-serif; }
  body { margin: 0; display: flex; height: 100vh; background: #f0f2f5; }
  #lista { width: 320px; background: #fff; border-right: 1px solid #ddd; overflow-y: auto; }
  .conv { padding: 12px 16px; border-bottom: 1px solid #eee; cursor: pointer; }
  .conv:hover { background: #f5f5f5; }
  .conv.activa { background: #e7f3ff; }
  .conv .telefono { font-weight: bold; }
  .conv .preview { color: #666; font-size: 0.85em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .badge { display: inline-block; font-size: 0.7em; padding: 2px 6px; border-radius: 4px; margin-left: 6px; }
  .badge.pausado { background: #ffe0b2; color: #8a4b00; }
  .badge.bot { background: #d4edda; color: #155724; }
  .badge.etiqueta { background: #e0d4fd; color: #4b1f8a; }
  #chat { flex: 1; display: flex; flex-direction: column; }
  #cabecera { padding: 12px 16px; background: #fff; border-bottom: 1px solid #ddd; display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
  #cabecera-controles { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
  #mensajes { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 8px; }
  .msg { max-width: 60%; padding: 8px 12px; border-radius: 8px; white-space: pre-wrap; }
  .msg.user { align-self: flex-start; background: #fff; }
  .msg.assistant { align-self: flex-end; background: #d9fdd3; }
  #form-envio { display: flex; padding: 12px; background: #fff; border-top: 1px solid #ddd; gap: 8px; align-items: center; }
  #form-envio input[type=text] { flex: 1; padding: 10px; border: 1px solid #ccc; border-radius: 6px; }
  #form-envio button { padding: 10px 16px; border: none; border-radius: 6px; background: #25d366; color: #fff; cursor: pointer; }
  #form-envio label.adjuntar { padding: 10px; border: 1px solid #ccc; border-radius: 6px; cursor: pointer; background: #f5f5f5; }
  #form-envio input[type=file] { display: none; }
  .toggle { display: flex; align-items: center; gap: 8px; font-size: 0.9em; }
  select#etiqueta-select { padding: 6px; border-radius: 6px; border: 1px solid #ccc; font-size: 0.85em; }
  button.borrar { padding: 6px 10px; border: none; border-radius: 6px; background: #e74c3c; color: #fff; cursor: pointer; font-size: 0.85em; }
  .vacio { padding: 40px; text-align: center; color: #888; }
  #archivo-nombre { font-size: 0.8em; color: #555; }
</style>
</head>
<body>

<div id="lista"></div>

<div id="chat">
  <div id="cabecera">
    <div id="titulo">Selecciona una conversación</div>
    <div id="cabecera-controles" style="display:none;">
      <select id="etiqueta-select">
        <option value="">Sin clasificar</option>
        <option value="nuevo">Nuevo</option>
        <option value="interesado">Interesado</option>
        <option value="cita_agendada">Cita agendada</option>
        <option value="cliente">Cliente</option>
        <option value="descartado">Descartado</option>
      </select>
      <label class="toggle"><input type="checkbox" id="check-pausa"> Pausar bot (modo humano)</label>
      <button class="borrar" id="btn-borrar">Borrar conversación</button>
    </div>
  </div>
  <div id="mensajes"><div class="vacio">Selecciona una conversación de la izquierda</div></div>
  <form id="form-envio" style="display:none;">
    <label class="adjuntar" for="input-archivo">📎</label>
    <input type="file" id="input-archivo">
    <span id="archivo-nombre"></span>
    <input type="text" id="texto-envio" placeholder="Escribe un mensaje..." autocomplete="off">
    <button type="submit">Enviar</button>
  </form>
</div>

<script>
let telefonoActivo = null;

const ETIQUETAS = {
  nuevo: 'Nuevo',
  interesado: 'Interesado',
  cita_agendada: 'Cita agendada',
  cliente: 'Cliente',
  descartado: 'Descartado',
};

async function cargarConversaciones() {
  const res = await fetch('/api/conversaciones');
  const conversaciones = await res.json();
  const lista = document.getElementById('lista');
  lista.innerHTML = '';

  if (conversaciones.length === 0) {
    lista.innerHTML = '<div class="vacio">Sin conversaciones todavía</div>';
    return;
  }

  conversaciones.forEach(c => {
    const div = document.createElement('div');
    div.className = 'conv' + (c.telefono === telefonoActivo ? ' activa' : '');
    div.onclick = () => abrirConversacion(c.telefono);
    const etiquetaBadge = c.etiqueta ? `<span class="badge etiqueta">${ETIQUETAS[c.etiqueta] || c.etiqueta}</span>` : '';
    div.innerHTML = `
      <div class="telefono">${c.telefono}
        ${c.pausado ? '<span class="badge pausado">Humano</span>' : '<span class="badge bot">Bot</span>'}
        ${etiquetaBadge}
      </div>
      <div class="preview">${c.ultimo_role === 'user' ? '' : '↩ '}${escapeHtml(c.ultimo_mensaje)}</div>
    `;
    lista.appendChild(div);
  });
}

async function abrirConversacion(telefono) {
  telefonoActivo = telefono;
  document.getElementById('titulo').textContent = telefono;
  document.getElementById('cabecera-controles').style.display = 'flex';
  document.getElementById('form-envio').style.display = 'flex';

  await cargarConversaciones();
  await cargarMensajes();
}

async function cargarMensajes() {
  if (!telefonoActivo) return;
  const res = await fetch(`/api/conversaciones/${encodeURIComponent(telefonoActivo)}/mensajes`);
  const mensajes = await res.json();

  const cont = document.getElementById('mensajes');
  cont.innerHTML = '';
  mensajes.forEach(m => {
    const div = document.createElement('div');
    div.className = 'msg ' + m.role;
    div.textContent = m.content;
    cont.appendChild(div);
  });
  cont.scrollTop = cont.scrollHeight;

  // Actualizar estado del switch de pausa y la etiqueta
  const conversaciones = await (await fetch('/api/conversaciones')).json();
  const actual = conversaciones.find(c => c.telefono === telefonoActivo);
  document.getElementById('check-pausa').checked = actual ? actual.pausado : false;
  document.getElementById('etiqueta-select').value = (actual && actual.etiqueta) ? actual.etiqueta : '';
}

document.getElementById('check-pausa').addEventListener('change', async (e) => {
  if (!telefonoActivo) return;
  await fetch(`/api/conversaciones/${encodeURIComponent(telefonoActivo)}/pausar?pausado=${e.target.checked}`, {
    method: 'POST'
  });
  await cargarConversaciones();
});

document.getElementById('etiqueta-select').addEventListener('change', async (e) => {
  if (!telefonoActivo) return;
  await fetch(`/api/conversaciones/${encodeURIComponent(telefonoActivo)}/etiqueta?etiqueta=${encodeURIComponent(e.target.value)}`, {
    method: 'POST'
  });
  await cargarConversaciones();
});

document.getElementById('btn-borrar').addEventListener('click', async () => {
  if (!telefonoActivo) return;
  if (!confirm(`¿Borrar toda la conversación con ${telefonoActivo}? Esto no se puede deshacer.`)) return;

  await fetch(`/api/conversaciones/${encodeURIComponent(telefonoActivo)}`, { method: 'DELETE' });

  telefonoActivo = null;
  document.getElementById('titulo').textContent = 'Selecciona una conversación';
  document.getElementById('cabecera-controles').style.display = 'none';
  document.getElementById('form-envio').style.display = 'none';
  document.getElementById('mensajes').innerHTML = '<div class="vacio">Selecciona una conversación de la izquierda</div>';

  await cargarConversaciones();
});

document.getElementById('input-archivo').addEventListener('change', (e) => {
  const archivo = e.target.files[0];
  document.getElementById('archivo-nombre').textContent = archivo ? archivo.name : '';
});

document.getElementById('form-envio').addEventListener('submit', async (e) => {
  e.preventDefault();
  if (!telefonoActivo) return;

  const input = document.getElementById('texto-envio');
  const archivoInput = document.getElementById('input-archivo');
  const texto = input.value.trim();
  const archivo = archivoInput.files[0];

  if (archivo) {
    const formData = new FormData();
    formData.append('archivo', archivo);
    formData.append('mensaje', texto);

    await fetch(`/api/conversaciones/${encodeURIComponent(telefonoActivo)}/archivo`, {
      method: 'POST',
      body: formData
    });

    archivoInput.value = '';
    document.getElementById('archivo-nombre').textContent = '';
  } else if (texto) {
    const formData = new FormData();
    formData.append('mensaje', texto);

    await fetch(`/api/conversaciones/${encodeURIComponent(telefonoActivo)}/enviar`, {
      method: 'POST',
      body: formData
    });
  } else {
    return;
  }

  input.value = '';
  await cargarMensajes();
});

function escapeHtml(texto) {
  const div = document.createElement('div');
  div.textContent = texto;
  return div.innerHTML;
}

cargarConversaciones();
setInterval(() => {
  cargarConversaciones();
  if (telefonoActivo) cargarMensajes();
}, 5000);
</script>

</body>
</html>
"""

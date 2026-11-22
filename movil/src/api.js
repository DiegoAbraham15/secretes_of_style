// Cliente HTTP de la API de Secrets of Style.
import Constants from 'expo-constants';
import { File } from 'expo-file-system';
import { Platform } from 'react-native';

// Usa EXPO_PUBLIC_URL_API si existe; si no, la IP de la computadora que sirve la app, puerto 8000.
const hostMetro = Constants.expoConfig?.hostUri?.split(':')[0] ?? 'localhost';
const URL_API = process.env.EXPO_PUBLIC_URL_API ?? `http://${hostMetro}:8000`;

export const urlImagen = (ruta) => `${URL_API}${ruta}`;

let token = null;
let alExpirarSesion = () => {};

export function establecerToken(nuevoToken, cuandoExpire) {
  token = nuevoToken;
  alExpirarSesion = cuandoExpire;
}

async function peticion(ruta, opciones = {}) {
  const encabezados = {};
  if (token) encabezados.Authorization = `Bearer ${token}`;
  if (typeof opciones.body === 'string') encabezados['Content-Type'] = 'application/json';

  let respuesta;
  try {
    respuesta = await fetch(`${URL_API}${ruta}`, { ...opciones, headers: encabezados });
  } catch (error) {
    throw new Error(`No se pudo conectar con ${URL_API}. Revisa que el servidor esté encendido.\n(${error})`);
  }

  if (respuesta.status === 204) return null;
  const cuerpo = await respuesta.json().catch(() => null);
  if (!respuesta.ok) {
    if (respuesta.status === 401 && token) alExpirarSesion(); // sesión vencida: se cierra
    const detalle = cuerpo?.detail;
    // Los errores de validación de FastAPI llegan como lista.
    const mensaje = Array.isArray(detalle) ? detalle.map((e) => e.msg).join('\n') : detalle;
    const error = new Error(mensaje ?? `Error del servidor (${respuesta.status})`);
    error.estado = respuesta.status; // p. ej. 409 del probador: falta la foto
    throw error;
  }
  return cuerpo;
}

const enviar = (metodo, datos) => ({ method: metodo, body: JSON.stringify(datos) });

// ---------- Autenticación ----------

export const iniciarSesion = (correo, contraseña) =>
  peticion('/api/auth/login', enviar('POST', { correo, contraseña }));

export const registrarse = (correo, contraseña) =>
  peticion('/api/auth/registro', enviar('POST', { correo, contraseña }));

// La cuenta de la sesión (el correo se usa para la inicial del avatar).
export const obtenerUsuario = () => peticion('/api/auth/yo');

// Invalida en el servidor todos los tokens de la cuenta, no solo el de este teléfono.
export const cerrarSesion = () => peticion('/api/auth/cerrar-sesion', { method: 'POST' });

// ---------- Armario ----------

export function listarPrendas(filtros = {}) {
  const parametros = new URLSearchParams();
  if (filtros.categoria) parametros.append('categoria', filtros.categoria);
  if (filtros.estado) parametros.append('estado', filtros.estado);
  return peticion(`/api/prendas?${parametros}`);
}

async function formularioConImagen(uriImagen, nombreImagen) {
  const formulario = new FormData();
  if (Platform.OS === 'web') {
    const blob = await (await fetch(uriImagen)).blob();
    formulario.append('imagen', blob, nombreImagen);
  } else {
    // En el SDK 57 el archivo debe ir como File de expo-file-system.
    formulario.append('imagen', new File(uriImagen), nombreImagen);
  }
  return formulario;
}

// El modelo de visión del servidor propone categoría, tipo, color, estampado, estilo, abrigo e
// impermeabilidad. No guarda nada.
export async function analizarPrenda(uriImagen, nombreImagen) {
  const formulario = await formularioConImagen(uriImagen, nombreImagen);
  return peticion('/api/prendas/analizar', { method: 'POST', body: formulario });
}

export async function subirPrenda(datos) {
  const formulario = await formularioConImagen(datos.uriImagen, datos.nombreImagen);
  formulario.append('categoria', datos.categoria);
  formulario.append('color_principal', datos.color_principal);
  formulario.append('nivel_abrigo', String(datos.nivel_abrigo));
  formulario.append('impermeable', String(datos.impermeable));
  formulario.append('estampado', datos.estampado);
  formulario.append('estilo', datos.estilo);
  if (datos.subcategoria) formulario.append('subcategoria', datos.subcategoria);

  return peticion('/api/prendas', { method: 'POST', body: formulario });
}

export const obtenerPrenda = (prendaId) => peticion(`/api/prendas/${prendaId}`);

// ---------- Digitalización: borradores que la IA y el motor procesan en segundo plano ----------

// Sube una foto: el servidor responde de inmediato y la procesa (IA, quitar fondo, color y temporada).
export async function crearBorrador(uriImagen) {
  const formulario = await formularioConImagen(uriImagen, 'prenda.jpg');
  return peticion('/api/prendas/borradores', { method: 'POST', body: formulario });
}

// El link de una tienda o de una imagen: baja la foto, el nombre y el precio.
export const importarDesdeUrl = (url) => peticion('/api/prendas/borradores/url', enviar('POST', { url }));

export const listarBorradores = () => peticion('/api/prendas/borradores');

export const obtenerBorrador = (borradorId) => peticion(`/api/prendas/borradores/${borradorId}`);

export const reintentarBorrador = (borradorId) =>
  peticion(`/api/prendas/borradores/${borradorId}/reintentar`, { method: 'POST' });

// Con los datos revisados, el borrador se vuelve una prenda del armario.
export const confirmarBorrador = (borradorId, datos) =>
  peticion(`/api/prendas/borradores/${borradorId}/confirmar`, enviar('POST', datos));

export const descartarBorrador = (borradorId) =>
  peticion(`/api/prendas/borradores/${borradorId}`, { method: 'DELETE' });

// Corrige cualquier dato de una prenda (también precio, fecha de compra y temporada).
export const editarPrenda = (prendaId, cambios) => peticion(`/api/prendas/${prendaId}`, enviar('PATCH', cambios));

// Para las prendas de antes: el motor les quita el fondo.
export const quitarFondoPrenda = (prendaId) => peticion(`/api/prendas/${prendaId}/quitar-fondo`, { method: 'POST' });

// estado: 'disponible', 'en_lavado' o 'archivada'.
export const cambiarEstadoPrenda = (prendaId, estado) =>
  peticion(`/api/prendas/${prendaId}/estado`, enviar('PATCH', { estado }));

// La IA vuelve a mirar la foto guardada y actualiza el estampado y el estilo.
export const detectarEstiloPrenda = (prendaId) =>
  peticion(`/api/prendas/${prendaId}/detectar-estilo`, { method: 'POST' });

export const eliminarPrenda = (prendaId) => peticion(`/api/prendas/${prendaId}`, { method: 'DELETE' });

// LIMPIEZA de datos: por qué conviene revisar una prenda (foto muy chica, color que no coincide…).
export const revisarPrenda = (prendaId) => peticion(`/api/prendas/${prendaId}/revision`);

// ---------- Recomendaciones ----------

// Los mejores atuendos con la prenda base, según el clima de esa ubicación y la ocasión.
export const obtenerRecomendaciones = (prendaBaseId, latitud, longitud, ocasion) =>
  peticion('/api/recomendaciones', enviar('POST', { prenda_base_id: prendaBaseId, latitud, longitud, ocasion }));

// El look de hoy sin elegir prenda base: A* con todas tus partes de arriba, tus gustos y sin repetir lo de los
// últimos días. Responde como obtenerRecomendaciones, con una sola sugerencia y del_dia: true.
export const obtenerLookDelDia = (latitud, longitud, ocasion) =>
  peticion('/api/recomendaciones/dia', enviar('POST', { latitud, longitud, ocasion, fecha: fechaDeHoy() }));

// Por qué funciona un atuendo, redactado por la IA con los hechos de la lógica.
export const explicarAtuendo = (sugerencia, latitud, longitud, ocasion) =>
  peticion(
    '/api/recomendaciones/explicacion',
    enviar('POST', { prenda_ids: sugerencia.elementos.map((e) => e.prenda.id), latitud, longitud, ocasion }),
  );

// El cuestionario de estilo; lo que no se contesta queda sin preferencia.
export const guardarPreferencias = (respuestas) => peticion('/api/preferencias', enviar('PUT', respuestas));

// ---------- Colorimetría personal ----------

export const obtenerPreguntasColor = () => peticion('/api/colorimetria/preguntas');

// El diagnóstico guardado, o null.
export const obtenerColorimetria = () => peticion('/api/colorimetria');

export const contestarColorimetria = (respuestas) =>
  peticion('/api/colorimetria/cuestionario', enviar('POST', { respuestas }));

// Una selfie (uri) o, con uri null, la foto del probador. La foto no se guarda: solo los colores medidos.
export async function analizarSelfie(uriImagen) {
  const formulario = uriImagen ? await formularioConImagen(uriImagen, 'selfie.jpg') : new FormData();
  if (!uriImagen) formulario.append('usar_foto_probador', 'true');
  return peticion('/api/colorimetria/selfie', { method: 'POST', body: formulario });
}

export const priorizarColorimetria = (priorizar) => peticion('/api/colorimetria', enviar('PATCH', { priorizar }));

export const borrarColorimetria = () => peticion('/api/colorimetria', { method: 'DELETE' });

// Las respuestas actuales, para editarlas en "Tus gustos".
export const obtenerPreferencias = () => peticion('/api/preferencias');

// Poner o quitar el corazón: el servidor reentrena el perceptrón de la persona.
export const votarAtuendo = (sugerencia, meGusta) =>
  peticion(
    '/api/atuendos/voto',
    enviar('POST', { prenda_ids: sugerencia.elementos.map((e) => e.prenda.id), me_gusta: meGusta }),
  );

export const guardarAtuendo = (sugerencia, reporteClima) =>
  peticion(
    '/api/atuendos',
    enviar('POST', {
      puntuacion: sugerencia.puntuacion,
      reporte_clima: reporteClima,
      elementos: sugerencia.elementos.map((e) => ({ prenda_id: e.prenda.id, rol: e.rol })),
    }),
  );

export const listarAtuendos = () => peticion('/api/atuendos');

export const eliminarAtuendo = (atuendoId) => peticion(`/api/atuendos/${atuendoId}`, { method: 'DELETE' });

// ---------- "Me lo puse hoy" ----------

// El día del teléfono (AAAA-MM-DD). El servidor está en UTC: en México, desde las 18 h ya sería mañana.
export function fechaDeHoy(diasAtras = 0) {
  const fecha = new Date();
  fecha.setDate(fecha.getDate() - diasAtras);
  const dos = (n) => String(n).padStart(2, '0');
  return `${fecha.getFullYear()}-${dos(fecha.getMonth() + 1)}-${dos(fecha.getDate())}`;
}

// Lo que te pusiste hoy (si ya había algo hoy, lo reemplaza). Un look completo cuenta como corazón.
export const registrarUso = (prendaIds) =>
  peticion('/api/usos', enviar('POST', { prenda_ids: prendaIds, fecha: fechaDeHoy() }));

// Los días registrados desde esa fecha (AAAA-MM-DD), del más reciente al más viejo.
export const listarUsos = (desde) => peticion(`/api/usos?desde=${desde}`);

export const quitarUso = (fecha) => peticion(`/api/usos/${fecha}`, { method: 'DELETE' });

// ---------- Probador virtual ----------

export const obtenerPerfil = () => peticion('/api/perfil');

// La foto con la que se prueban los looks. El servidor revisa que sirva (rostro, torso y piernas).
export async function subirFotoCuerpo(uriImagen) {
  const formulario = await formularioConImagen(uriImagen, 'cuerpo.jpg');
  return peticion('/api/perfil/foto', { method: 'POST', body: formulario });
}

export const borrarFotoCuerpo = () => peticion('/api/perfil/foto', { method: 'DELETE' });

// Pide ver el look puesto: responde la prueba lista o en la cola.
export const pedirPrueba = (sugerencia) =>
  peticion('/api/atuendos/probador', enviar('POST', { prenda_ids: sugerencia.elementos.map((e) => e.prenda.id) }));

export const consultarPrueba = (pruebaId) => peticion(`/api/atuendos/probador/${pruebaId}`);

// Las imágenes del probador son privadas: se piden con la sesión, no como /archivos.
export const imagenPrivada = (ruta) => ({ uri: urlImagen(ruta), headers: { Authorization: `Bearer ${token}` } });

// La foto de la persona. La versión va en la URL para que, al cambiarla, el teléfono no enseñe la anterior.
export const fotoCuerpo = (versionFoto) => imagenPrivada(`/api/perfil/foto?v=${versionFoto}`);

// ---------- Estadísticas ----------

// Con la fecha del teléfono, para contar bien los últimos 30 días de "Me lo puse".
export const obtenerEstadisticas = () => peticion(`/api/estadisticas?fecha=${fechaDeHoy()}`);

// Grupos de ropa (K-means), mapa del armario (PCA) y prendas que no encajan (segmentación, atípicos y PCA).
export const obtenerGruposDelArmario = () => peticion('/api/prendas/grupos');

// Qué tan bien ordena cada sistema tus looks con corazón (y cómo le fue a la CNN al entrenarse).
export const obtenerEvaluacionIA = () => peticion('/api/votos/evaluacion');

// ---------- Modo viaje ----------

export const buscarLugares = (nombre) => peticion(`/api/viaje/lugares?nombre=${encodeURIComponent(nombre)}`);

// Un look por día con el pronóstico del destino y la maleta. salida: en cuántos días se va (0 = hoy).
export const planearViaje = (lugar, salida, dias, ocasion) =>
  peticion(
    '/api/viaje',
    enviar('POST', {
      latitud: lugar.latitud,
      longitud: lugar.longitud,
      lugar: lugar.nombre,
      salida,
      dias,
      ocasion,
    }),
  );

// ---------- Reto de la semana: rescatar una prenda olvidada ----------

// El reto de esta semana (con la fecha del teléfono), o null si no hay prendas olvidadas.
export const obtenerReto = () => peticion(`/api/reto?fecha=${fechaDeHoy()}`);

export const cambiarReto = () => peticion(`/api/reto/cambiar?fecha=${fechaDeHoy()}`, { method: 'POST' });

export const omitirReto = () => peticion(`/api/reto/omitir?fecha=${fechaDeHoy()}`, { method: 'POST' });

// ---------- Cápsulas de guardarropa ----------

// escenario: 'mensual' o 'viaje' (con lugar, salida y días). No guarda nada.
export const generarCapsula = (datos) => peticion('/api/capsulas/generar', enviar('POST', datos));

export const guardarCapsula = (capsula) => peticion('/api/capsulas', enviar('POST', capsula));

export const listarCapsulas = () => peticion('/api/capsulas');

export const obtenerCapsula = (capsulaId) => peticion(`/api/capsulas/${capsulaId}`);

// Lo que ya va en la maleta (checklist).
export const marcarEmpacadas = (capsulaId, empacadas) =>
  peticion(`/api/capsulas/${capsulaId}`, enviar('PATCH', { empacadas }));

export const eliminarCapsula = (capsulaId) => peticion(`/api/capsulas/${capsulaId}`, { method: 'DELETE' });

// ---------- Tiendas: prendas que te gustaron en una tienda ----------

// La IA ve la foto y la prenda queda en tu lista con un link por tienda. para: mujer, hombre o sin_especificar.
export async function buscarEnTiendas(uriImagen, para) {
  const formulario = await formularioConImagen(uriImagen, 'tienda.jpg');
  formulario.append('para', para);
  return peticion('/api/deseos', { method: 'POST', body: formulario });
}

export const listarDeseos = () => peticion('/api/deseos');

// Corregir qué se busca (si la IA se equivocó) o para quién es.
export const cambiarDeseo = (deseoId, cambios) => peticion(`/api/deseos/${deseoId}`, enviar('PATCH', cambios));

export const eliminarDeseo = (deseoId) => peticion(`/api/deseos/${deseoId}`, { method: 'DELETE' });

// La IA vuelve a mirar la foto (marca, modelo, estampado) y rehace la búsqueda de la misma prenda.
export const analizarDeseo = (deseoId) => peticion(`/api/deseos/${deseoId}/analizar`, { method: 'POST' });

// Google Cloud Vision busca en internet la prenda exacta de la foto (si el servidor tiene la clave).
export const buscarDeseoPorImagen = (deseoId) =>
  peticion(`/api/deseos/${deseoId}/buscar-por-imagen`, { method: 'POST' });

// ¿Vale la pena comprarla? Cuántos looks arma con tu ropa, comparada con lo que ya tienes.
export const valeLaPena = (deseoId) => peticion(`/api/deseos/${deseoId}/vale-la-pena`);

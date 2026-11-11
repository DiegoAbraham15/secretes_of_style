// Cliente HTTP de la API de Secrets of Style.
import Constants from 'expo-constants';
import { File } from 'expo-file-system';
import { Platform } from 'react-native';

// Usa EXPO_PUBLIC_URL_API si existe; si no, la IP de la computadora que sirve la app, puerto 8000.
const hostMetro = Constants.expoConfig?.hostUri?.split(':')[0] ?? 'localhost';
export const URL_API = process.env.EXPO_PUBLIC_URL_API ?? `http://${hostMetro}:8000`;

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

// estado: 'disponible', 'en_lavado' o 'archivada'.
export const cambiarEstadoPrenda = (prendaId, estado) =>
  peticion(`/api/prendas/${prendaId}/estado`, enviar('PATCH', { estado }));

// Corrige el estampado y el estilo (las prendas registradas antes de la IA quedaron como lisas y casuales).
export const cambiarEstiloPrenda = (prendaId, estampado, estilo) =>
  peticion(`/api/prendas/${prendaId}/estilo`, enviar('PATCH', { estampado, estilo }));

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

// Por qué funciona un atuendo, redactado por la IA con los hechos de la lógica.
export const explicarAtuendo = (sugerencia, latitud, longitud, ocasion) =>
  peticion(
    '/api/recomendaciones/explicacion',
    enviar('POST', { prenda_ids: sugerencia.elementos.map((e) => e.prenda.id), latitud, longitud, ocasion }),
  );

// El cuestionario de estilo; lo que no se contesta queda sin preferencia.
export const guardarPreferencias = (respuestas) => peticion('/api/preferencias', enviar('PUT', respuestas));

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

export const obtenerEstadisticas = () => peticion('/api/estadisticas');

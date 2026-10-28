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
    throw new Error(mensaje ?? `Error del servidor (${respuesta.status})`);
  }
  return cuerpo;
}

const enviar = (metodo, datos) => ({ method: metodo, body: JSON.stringify(datos) });

// ---------- Autenticación ----------

export const iniciarSesion = (correo, contraseña) =>
  peticion('/api/auth/login', enviar('POST', { correo, contraseña }));

export const registrarse = (correo, contraseña) =>
  peticion('/api/auth/registro', enviar('POST', { correo, contraseña }));

// Invalida en el servidor todos los tokens de la cuenta, no solo el de este teléfono.
export const cerrarSesion = () => peticion('/api/auth/cerrar-sesion', { method: 'POST' });

// ---------- Armario ----------

export function listarPrendas(filtros = {}) {
  const parametros = new URLSearchParams();
  if (filtros.categoria) parametros.append('categoria', filtros.categoria);
  if (filtros.estado) parametros.append('estado', filtros.estado);
  return peticion(`/api/prendas?${parametros}`);
}

export async function subirPrenda(datos) {
  const formulario = new FormData();
  if (Platform.OS === 'web') {
    const blob = await (await fetch(datos.uriImagen)).blob();
    formulario.append('imagen', blob, datos.nombreImagen);
  } else {
    // En el SDK 57 el archivo debe ir como File de expo-file-system.
    formulario.append('imagen', new File(datos.uriImagen), datos.nombreImagen);
  }
  formulario.append('categoria', datos.categoria);
  formulario.append('color_principal', datos.color_principal);
  formulario.append('nivel_abrigo', String(datos.nivel_abrigo));
  formulario.append('impermeable', String(datos.impermeable));
  if (datos.subcategoria) formulario.append('subcategoria', datos.subcategoria);

  return peticion('/api/prendas', { method: 'POST', body: formulario });
}

export const obtenerPrenda = (prendaId) => peticion(`/api/prendas/${prendaId}`);

// estado: 'disponible', 'en_lavado' o 'archivada'.
export const cambiarEstadoPrenda = (prendaId, estado) =>
  peticion(`/api/prendas/${prendaId}/estado`, enviar('PATCH', { estado }));

export const eliminarPrenda = (prendaId) => peticion(`/api/prendas/${prendaId}`, { method: 'DELETE' });

// ---------- Recomendaciones ----------

// Los mejores atuendos con la prenda base, según el clima de esa ubicación.
export const obtenerRecomendaciones = (prendaBaseId, latitud, longitud) =>
  peticion('/api/recomendaciones', enviar('POST', { prenda_base_id: prendaBaseId, latitud, longitud }));

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

// ---------- Estadísticas ----------

export const obtenerEstadisticas = () => peticion('/api/estadisticas');

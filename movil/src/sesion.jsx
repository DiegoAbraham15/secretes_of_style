// Contexto de sesión: guarda el token y expone iniciar, registrar y cerrar sesión.
import * as SecureStore from 'expo-secure-store';
import { createContext, use, useEffect, useState } from 'react';
import { Platform } from 'react-native';

import * as api from './api';

const CLAVE_TOKEN = 'token_sesion';
const CLAVE_SERVIDOR = 'url_servidor';

// En el teléfono se usa almacenamiento cifrado; en web, localStorage.
const almacenDe = (clave) => ({
  leer: () => (Platform.OS === 'web' ? Promise.resolve(localStorage.getItem(clave)) : SecureStore.getItemAsync(clave)),
  guardar: (valor) => {
    if (Platform.OS === 'web') {
      if (valor) localStorage.setItem(clave, valor);
      else localStorage.removeItem(clave);
    } else if (valor) SecureStore.setItemAsync(clave, valor);
    else SecureStore.deleteItemAsync(clave);
  },
});
const almacen = almacenDe(CLAVE_TOKEN);
const almacenServidor = almacenDe(CLAVE_SERVIDOR);

const ContextoSesion = createContext(null);

// React exige que los hooks empiecen con "use".
export function useSesion() {
  const valor = use(ContextoSesion);
  if (!valor) throw new Error('useSesion debe usarse dentro de <ProveedorSesion />');
  return valor;
}

export function ProveedorSesion({ children }) {
  const [token, establecerToken] = useState(null);
  const [cargando, establecerCargando] = useState(true);
  // { token, correo, cuestionarioListo } de la última sesión consultada
  const [cuenta, establecerCuenta] = useState(null);

  const [urlServidor, establecerUrlServidor] = useState(api.obtenerUrlApi());

  // Al abrir la app, recupera la dirección del servidor y la sesión guardadas (la dirección primero: la sesión se
  // verifica contra ese servidor).
  useEffect(() => {
    almacenServidor
      .leer()
      .then((guardada) => {
        if (guardada) {
          api.establecerUrlApi(guardada);
          establecerUrlServidor(api.obtenerUrlApi());
        }
      })
      .catch(() => null)
      .then(() => almacen.leer())
      .then(establecerToken)
      .catch(() => null)
      .finally(() => establecerCargando(false));
  }, []);

  // El correo para el avatar del encabezado y si falta el cuestionario de estilo.
  useEffect(() => {
    if (!token) return;
    api
      .obtenerUsuario()
      .then((usuario) =>
        establecerCuenta({ token, correo: usuario.correo, cuestionarioListo: usuario.cuestionario_listo }),
      )
      // Sin conexión no se detiene a la persona con el cuestionario.
      .catch(() => establecerCuenta({ token, correo: null, cuestionarioListo: true }));
  }, [token]);

  function guardarToken(nuevoToken) {
    establecerToken(nuevoToken);
    almacen.guardar(nuevoToken);
  }

  api.establecerToken(token, () => guardarToken(null));

  const valor = {
    token,
    cargando,
    urlServidor,
    // Cambia a qué servidor habla la app (vacío = el predeterminado). Cierra la sesión: el token es de otro servidor.
    cambiarServidor: (url) => {
      api.establecerUrlApi(url);
      establecerUrlServidor(api.obtenerUrlApi());
      almacenServidor.guardar(api.obtenerUrlApi() === api.urlPredeterminada() ? null : api.obtenerUrlApi());
      guardarToken(null);
    },
    correo: cuenta?.token === token ? cuenta.correo : null, // al cambiar de cuenta no se ve el correo anterior
    cuestionarioListo: cuenta?.token === token ? cuenta.cuestionarioListo : null, // null: aún no se sabe
    marcarCuestionarioListo: () => establecerCuenta((actual) => ({ ...actual, cuestionarioListo: true })),
    iniciarSesion: async (correo, contraseña) =>
      guardarToken((await api.iniciarSesion(correo, contraseña)).token_acceso),
    registrarse: async (correo, contraseña) =>
      guardarToken((await api.registrarse(correo, contraseña)).token_acceso),
    // Si el servidor no responde, la sesión se cierra de todos modos en el teléfono.
    cerrarSesion: async () => {
      await api.cerrarSesion().catch(() => null);
      guardarToken(null);
    },
  };

  return <ContextoSesion value={valor}>{children}</ContextoSesion>;
}

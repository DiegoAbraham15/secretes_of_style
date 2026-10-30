// Contexto de sesión: guarda el token y expone iniciar, registrar y cerrar sesión.
import * as SecureStore from 'expo-secure-store';
import { createContext, use, useEffect, useState } from 'react';
import { Platform } from 'react-native';

import * as api from './api';

const CLAVE_TOKEN = 'token_sesion';

// En el teléfono se usa almacenamiento cifrado; en web, localStorage.
const almacen = {
  leer: () =>
    Platform.OS === 'web'
      ? Promise.resolve(localStorage.getItem(CLAVE_TOKEN))
      : SecureStore.getItemAsync(CLAVE_TOKEN),
  guardar: (valor) => {
    if (Platform.OS === 'web') {
      if (valor) localStorage.setItem(CLAVE_TOKEN, valor);
      else localStorage.removeItem(CLAVE_TOKEN);
    } else if (valor) SecureStore.setItemAsync(CLAVE_TOKEN, valor);
    else SecureStore.deleteItemAsync(CLAVE_TOKEN);
  },
};

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

  // Al abrir la app, recupera la sesión guardada.
  useEffect(() => {
    almacen
      .leer()
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

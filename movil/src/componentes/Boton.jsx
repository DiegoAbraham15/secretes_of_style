// Botón de acción. Primario: relleno. secundario: contorno. peligro: contorno rojo (eliminar).
// icono: componente de iconos.js que va antes del texto (decorativo: el texto ya lo dice).
// Al tocarlo se encoge un poco con un resorte (Presionable).
import { ActivityIndicator, Text } from 'react-native';

import { Presionable } from '../movimiento';
import { crearEstilos, espacio, fuentes, radio, tamañoIcono, useTema } from '../tema';

export function Boton({
  texto,
  alPresionar,
  secundario = false,
  peligro = false,
  icono: Icono,
  cargando = false,
  deshabilitado = false,
}) {
  const { colores } = useTema();
  const estilos = useEstilos();
  const inactivo = deshabilitado || cargando;
  const contorno = secundario || peligro;
  const color = peligro ? colores.error : contorno ? colores.primario : colores.sobrePrimario;

  return (
    <Presionable
      onPress={alPresionar}
      disabled={inactivo}
      accessibilityRole="button"
      accessibilityLabel={texto}
      accessibilityState={{ disabled: inactivo, busy: cargando }}
      style={[
        estilos.boton,
        contorno && estilos.contorno,
        peligro && { borderColor: colores.error },
        deshabilitado && !cargando && estilos.deshabilitado,
      ]}>
      {cargando ? (
        <ActivityIndicator color={color} />
      ) : (
        <>
          {Icono && <Icono color={color} size={tamañoIcono.s} weight="bold" />}
          <Text style={[estilos.texto, { color }]}>{texto}</Text>
        </>
      )}
    </Presionable>
  );
}

const useEstilos = crearEstilos(({ colores }) => ({
  boton: {
    minHeight: 52,
    borderRadius: radio.l,
    backgroundColor: colores.primario,
    flexDirection: 'row',
    gap: espacio.s,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: espacio.l,
  },
  contorno: { backgroundColor: colores.superficie, borderWidth: 1.5, borderColor: colores.primario },
  deshabilitado: { opacity: 0.45 },
  texto: { fontFamily: fuentes.negrita, fontSize: 15, letterSpacing: 0.6, textTransform: 'uppercase' },
}));

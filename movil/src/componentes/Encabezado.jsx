// Cabecera de cada pestaña, como la de una revista: el título grande en Bodoni y, a la derecha, el avatar
// de la cuenta (al tocarlo se puede cerrar sesión). Si se pasa children (p. ej. un buscador), va en la
// fila de arriba junto a la acción y el avatar, y el título baja a su propia línea.
// accion: { icono, etiqueta, alPresionar } — el ícono va en un círculo rosa.
import { Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { confirmar } from '../confirmar';
import { Presionable } from '../movimiento';
import { useSesion } from '../sesion';
import { crearEstilos, espacio, fuentes, tamañoIcono, useTema } from '../tema';

const TAMAÑO_CIRCULO = 44;

export function Encabezado({ titulo, children, accion }) {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const { correo, cerrarSesion } = useSesion();
  const { top } = useSafeAreaInsets();

  const salir = () =>
    confirmar(
      'Cerrar sesión',
      `${correo ? `Entraste como ${correo}. ` : ''}¿Quieres cerrar tu sesión? Se cerrará también en tus otros dispositivos.`,
      'Salir',
      cerrarSesion,
    );

  const textoTitulo = titulo && (
    <Text style={[texto.titulo, children ? null : estilos.tituloEnFila]} accessibilityRole="header">
      {titulo}
    </Text>
  );

  return (
    <View style={[estilos.cabecera, { paddingTop: top + espacio.s }]}>
      <View style={estilos.fila}>
        {children ? <View style={estilos.centro}>{children}</View> : textoTitulo}

        {accion && (
          <Presionable
            onPress={accion.alPresionar}
            accessibilityRole="button"
            accessibilityLabel={accion.etiqueta}
            escala={0.92}
            style={estilos.accion}>
            <accion.icono color={colores.sobrePrimario} size={tamañoIcono.m} weight="bold" />
          </Presionable>
        )}

        <Presionable
          onPress={salir}
          accessibilityRole="button"
          accessibilityLabel="Tu cuenta: cerrar sesión"
          escala={0.92}
          style={estilos.avatar}>
          <Text style={estilos.inicial}>{correo ? correo[0].toUpperCase() : ''}</Text>
        </Presionable>
      </View>

      {children && textoTitulo}
    </View>
  );
}

const useEstilos = crearEstilos(({ colores }) => ({
  cabecera: { gap: espacio.m, paddingHorizontal: espacio.m, paddingBottom: espacio.s, backgroundColor: colores.fondo },
  fila: { flexDirection: 'row', alignItems: 'center', gap: espacio.s + 4, minHeight: TAMAÑO_CIRCULO },
  centro: { flex: 1 },
  tituloEnFila: { flex: 1 },
  avatar: {
    width: TAMAÑO_CIRCULO,
    height: TAMAÑO_CIRCULO,
    borderRadius: TAMAÑO_CIRCULO / 2,
    backgroundColor: colores.texto,
    alignItems: 'center',
    justifyContent: 'center',
  },
  inicial: { fontFamily: fuentes.display, fontSize: 20, lineHeight: 24, color: colores.fondo },
  accion: {
    width: TAMAÑO_CIRCULO,
    height: TAMAÑO_CIRCULO,
    borderRadius: TAMAÑO_CIRCULO / 2,
    backgroundColor: colores.primario,
    alignItems: 'center',
    justifyContent: 'center',
  },
}));

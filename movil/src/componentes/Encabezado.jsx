// Cabecera de cada pantalla principal: título a la izquierda y, a la derecha, una acción opcional y el avatar
// de la cuenta (lleva a Perfil). Si se pasa children (p. ej. un buscador), va debajo del título.
// atras: muestra la flecha de regreso (pantallas que se abren desde Inicio, como Atuendos o Tiendas).
// accion: { icono, etiqueta, alPresionar }.
import { router } from 'expo-router';
import { Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { IconoAtras } from '../iconos';
import { Presionable } from '../movimiento';
import { useSesion } from '../sesion';
import { crearEstilos, espacio, fuentes, tamañoIcono, useTema } from '../tema';

const TAMAÑO_CIRCULO = 44;

export function Encabezado({ titulo, subtitulo, children, accion, atras = false }) {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const { correo } = useSesion();
  const { top } = useSafeAreaInsets();

  return (
    <View style={[estilos.cabecera, { paddingTop: top + espacio.s }]}>
      <View style={estilos.fila}>
        {atras && (
          <Presionable
            onPress={() => (router.canGoBack() ? router.back() : router.replace('/'))}
            accessibilityRole="button"
            accessibilityLabel="Regresar"
            escala={0.92}
            style={estilos.circuloNeutro}>
            <IconoAtras color={colores.texto} size={tamañoIcono.m} weight="bold" />
          </Presionable>
        )}

        <View style={estilos.titulos}>
          {titulo && (
            <Text style={texto.titulo} accessibilityRole="header" numberOfLines={1}>
              {titulo}
            </Text>
          )}
          {subtitulo && <Text style={texto.detalle}>{subtitulo}</Text>}
        </View>

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

        {!atras && (
          <Presionable
            onPress={() => router.push('/perfil')}
            accessibilityRole="button"
            accessibilityLabel="Tu perfil"
            escala={0.92}
            style={estilos.avatar}>
            <Text style={estilos.inicial}>{correo ? correo[0].toUpperCase() : ''}</Text>
          </Presionable>
        )}
      </View>

      {children}
    </View>
  );
}

const useEstilos = crearEstilos(({ colores, elevacion }) => ({
  cabecera: { gap: espacio.m, paddingHorizontal: espacio.m, paddingBottom: espacio.s, backgroundColor: colores.fondo },
  fila: { flexDirection: 'row', alignItems: 'center', gap: espacio.s + 4, minHeight: TAMAÑO_CIRCULO },
  titulos: { flex: 1, minWidth: 0 },
  avatar: {
    width: TAMAÑO_CIRCULO,
    height: TAMAÑO_CIRCULO,
    borderRadius: TAMAÑO_CIRCULO / 2,
    backgroundColor: colores.primarioSuave,
    alignItems: 'center',
    justifyContent: 'center',
  },
  inicial: { fontFamily: fuentes.negrita, fontSize: 18, lineHeight: 22, color: colores.primario },
  accion: {
    width: TAMAÑO_CIRCULO,
    height: TAMAÑO_CIRCULO,
    borderRadius: TAMAÑO_CIRCULO / 2,
    backgroundColor: colores.primario,
    alignItems: 'center',
    justifyContent: 'center',
    ...elevacion(1),
  },
  circuloNeutro: {
    width: TAMAÑO_CIRCULO,
    height: TAMAÑO_CIRCULO,
    borderRadius: TAMAÑO_CIRCULO / 2,
    backgroundColor: colores.superficie,
    alignItems: 'center',
    justifyContent: 'center',
    ...elevacion(1),
  },
}));

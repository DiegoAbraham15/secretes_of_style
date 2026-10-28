// Foto de una prenda con su nombre y sus datos debajo.
// seleccionada: borde primario y palomita (selector de prenda base del generador).
// Si la prenda no está disponible (en lavado o archivada), la foto se atenúa y lo dice encima.
import { Image } from 'expo-image';
import { Text, View } from 'react-native';

import { urlImagen } from '../api';
import { ETIQUETA_COLOR, ETIQUETA_ESTADO, HEX_COLOR, nombreDePrenda } from '../catalogos';
import { IconoImpermeable, IconoPalomita } from '../iconos';
import { Presionable } from '../movimiento';
import { crearEstilos, espacio, fuentes, radio, useTema } from '../tema';

export function TarjetaPrenda({ prenda, seleccionada = false, soloFoto = false, alPresionar }) {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const noDisponible = prenda.estado !== 'disponible';
  const descripcion = [
    nombreDePrenda(prenda),
    ETIQUETA_COLOR[prenda.color_principal],
    prenda.impermeable && 'impermeable',
    noDisponible && ETIQUETA_ESTADO[prenda.estado],
  ];

  return (
    <Presionable
      onPress={alPresionar}
      accessibilityRole="button"
      accessibilityLabel={descripcion.filter(Boolean).join(', ')}
      accessibilityState={{ selected: seleccionada }}>
      <View style={[estilos.marco, seleccionada && estilos.marcoSeleccionado]}>
        <Image
          source={{ uri: urlImagen(prenda.url_imagen) }}
          style={estilos.foto}
          contentFit="cover"
          cachePolicy="memory-disk"
          transition={200}
        />

        {/* Muestra del color de la prenda en la esquina de la foto */}
        <View style={[estilos.muestraFoto, { backgroundColor: HEX_COLOR[prenda.color_principal] }]} />

        {prenda.impermeable ? (
          <View style={estilos.impermeable}>
            <IconoImpermeable color={colores.primario} size={14} weight="bold" />
          </View>
        ) : null}

        {noDisponible && (
          <View style={estilos.velo}>
            <Text style={estilos.estado}>{ETIQUETA_ESTADO[prenda.estado]}</Text>
          </View>
        )}

        {seleccionada && (
          <View style={estilos.palomita}>
            <IconoPalomita color={colores.sobrePrimario} size={14} weight="bold" />
          </View>
        )}
      </View>

      <Text style={[estilos.nombre, seleccionada && { color: colores.primario }]} numberOfLines={1}>
        {nombreDePrenda(prenda)}
      </Text>
      <Text style={texto.nota} numberOfLines={1}>
        {ETIQUETA_COLOR[prenda.color_principal]} · abrigo {prenda.nivel_abrigo}
        {soloFoto ? '' : ' de 5'}
      </Text>
    </Presionable>
  );
}

const useEstilos = crearEstilos(({ colores, texto }) => ({
  marco: {
    borderRadius: radio.xl,
    backgroundColor: colores.superficieSuave,
    borderWidth: 2,
    borderColor: 'transparent',
    overflow: 'hidden',
  },
  marcoSeleccionado: { borderColor: colores.primario },
  // Espacio reservado con la proporción de la foto: la cuadrícula no salta al cargar.
  foto: { width: '100%', aspectRatio: 3 / 4 },
  muestraFoto: {
    position: 'absolute',
    top: espacio.s + 2,
    left: espacio.s + 2,
    width: 18,
    height: 18,
    borderRadius: 9,
    borderWidth: 2,
    borderColor: colores.superficie,
  },
  impermeable: {
    position: 'absolute',
    bottom: espacio.s,
    left: espacio.s,
    width: 26,
    height: 26,
    borderRadius: 13,
    backgroundColor: colores.superficie,
    alignItems: 'center',
    justifyContent: 'center',
  },
  velo: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: colores.velo,
    alignItems: 'center',
    justifyContent: 'center',
  },
  estado: {
    fontFamily: fuentes.negrita,
    fontSize: 12,
    letterSpacing: 0.6,
    textTransform: 'uppercase',
    color: colores.fondo,
    backgroundColor: colores.texto,
    paddingHorizontal: espacio.s + 2,
    paddingVertical: espacio.xs,
    borderRadius: radio.s,
    overflow: 'hidden',
  },
  palomita: {
    position: 'absolute',
    top: espacio.s,
    right: espacio.s,
    width: 26,
    height: 26,
    borderRadius: 13,
    backgroundColor: colores.primario,
    alignItems: 'center',
    justifyContent: 'center',
  },
  nombre: { ...texto.etiqueta, marginTop: espacio.s },
}));

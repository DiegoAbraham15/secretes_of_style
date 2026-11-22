// Una prenda como tarjeta de cuadrícula: foto grande, nombre con su color y el estado como píldora.
// Las que no están disponibles se ven atenuadas.
import { Text, View } from 'react-native';

import { ETIQUETA_ESTADO, HEX_COLOR, nombreConColor } from '../catalogos';
import { Presionable } from '../movimiento';
import { crearEstilos, espacio, fuentes, radio, useTema } from '../tema';
import { FotoPrenda } from './FotoPrenda';

export function TarjetaPrenda({ prenda, alPresionar, ancho }) {
  const { colores } = useTema();
  const estilos = useEstilos();
  const disponible = prenda.estado === 'disponible';
  const nombre = nombreConColor(prenda);
  const estado = {
    disponible: [colores.exitoSuave, colores.exito],
    en_lavado: [colores.avisoSuave, colores.aviso],
    archivada: [colores.superficieSuave, colores.textoSecundario],
  }[prenda.estado] ?? [colores.superficieSuave, colores.textoSecundario];

  return (
    <Presionable
      onPress={alPresionar}
      escala={0.96}
      accessibilityRole="button"
      accessibilityLabel={`${nombre}, ${ETIQUETA_ESTADO[prenda.estado]}`}
      style={[estilos.tarjeta, { width: ancho }]}>
      <View style={estilos.marco}>
        <FotoPrenda prenda={prenda} style={[estilos.foto, !disponible && { opacity: 0.45 }]} />
        <View style={[estilos.muestra, { backgroundColor: HEX_COLOR[prenda.color_principal] }]} />
      </View>
      <View style={estilos.datos}>
        <Text style={estilos.nombre} numberOfLines={1}>
          {nombre}
        </Text>
        <View style={[estilos.pildora, { backgroundColor: estado[0] }]}>
          <Text style={[estilos.textoEstado, { color: estado[1] }]}>{ETIQUETA_ESTADO[prenda.estado]}</Text>
        </View>
      </View>
    </Presionable>
  );
}

const useEstilos = crearEstilos(({ colores, tarjeta }) => ({
  tarjeta: { ...tarjeta, borderRadius: radio.m, overflow: 'visible' },
  marco: {
    aspectRatio: 1,
    margin: espacio.xs + 2,
    marginBottom: 0,
    borderRadius: radio.s,
    backgroundColor: colores.superficieSuave,
    overflow: 'hidden',
  },
  foto: { width: '100%', height: '100%' },
  muestra: {
    position: 'absolute',
    right: espacio.xs + 2,
    bottom: espacio.xs + 2,
    width: 14,
    height: 14,
    borderRadius: 7,
    borderWidth: 2,
    borderColor: colores.superficie,
  },
  datos: { paddingHorizontal: espacio.s, paddingVertical: espacio.s, gap: espacio.xs },
  nombre: { fontFamily: fuentes.media, fontSize: 13, lineHeight: 17, color: colores.texto },
  pildora: { alignSelf: 'flex-start', paddingHorizontal: espacio.s, paddingVertical: 2, borderRadius: radio.pastilla },
  textoEstado: { fontFamily: fuentes.media, fontSize: 11, lineHeight: 15 },
}));

// Una prenda como fila de lista: foto pequeña con la muestra de su color, el nombre con el color, sus datos,
// el estado con un punto de color (verde si está disponible) y una flecha a la derecha.
// conEstado: false quita el estado (al elegir prenda base todas están disponibles). seleccionada: palomita
// en lugar de la flecha. accion: texto en lugar de la flecha (p. ej. "Cambiar"). Va dentro de GrupoPrendas.
import { Image } from 'expo-image';
import { Text, View } from 'react-native';

import { urlImagen } from '../api';
import {
  ETIQUETA_COLOR,
  ETIQUETA_ESTADO,
  ETIQUETA_ESTAMPADO,
  ETIQUETA_ESTILO,
  HEX_COLOR,
  nombreDePrenda,
} from '../catalogos';
import { IconoIr, IconoPalomita } from '../iconos';
import { Presionable } from '../movimiento';
import { crearEstilos, espacio, fuentes, radio, useTema } from '../tema';

const TAMAÑO_FOTO = 64;

export function FilaPrenda({ prenda, ultima = false, conEstado = true, seleccionada = false, accion, alPresionar }) {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const disponible = prenda.estado === 'disponible';
  const colorEstado = { disponible: colores.exito, en_lavado: colores.acento }[prenda.estado] ?? colores.bordeControl;
  const nombre = `${nombreDePrenda(prenda)} ${ETIQUETA_COLOR[prenda.color_principal].toLowerCase()}`;
  const detalle = [
    `Abrigo ${prenda.nivel_abrigo} de 5`,
    ETIQUETA_ESTAMPADO[prenda.estampado]?.toLowerCase(),
    ETIQUETA_ESTILO[prenda.estilo]?.toLowerCase(),
    prenda.impermeable && 'impermeable',
  ]
    .filter(Boolean)
    .join(', ');

  return (
    <Presionable
      onPress={alPresionar}
      escala={0.98}
      accessibilityRole="button"
      accessibilityLabel={[accion, nombre, detalle, conEstado && ETIQUETA_ESTADO[prenda.estado]].filter(Boolean).join(', ')}
      accessibilityState={{ selected: seleccionada }}
      style={[estilos.fila, !ultima && estilos.separador]}>
      <View>
        <Image
          source={{ uri: urlImagen(prenda.url_imagen) }}
          style={[estilos.foto, !disponible && { opacity: 0.5 }]}
          contentFit="cover"
          cachePolicy="memory-disk"
          transition={200}
        />
        <View style={[estilos.muestra, { backgroundColor: HEX_COLOR[prenda.color_principal] }]} />
      </View>

      <View style={estilos.datos}>
        <Text style={estilos.nombre} numberOfLines={1}>
          {nombre}
        </Text>
        <Text style={texto.nota} numberOfLines={1}>
          {detalle}
        </Text>
        {conEstado && (
          <View style={estilos.estado}>
            <View style={[estilos.punto, { backgroundColor: colorEstado }]} />
            <Text style={[estilos.textoEstado, disponible && { color: colores.exito }]}>{ETIQUETA_ESTADO[prenda.estado]}</Text>
          </View>
        )}
      </View>

      {accion ? (
        <Text style={estilos.accion}>{accion}</Text>
      ) : seleccionada ? (
        <IconoPalomita color={colores.primario} size={18} weight="bold" />
      ) : (
        <IconoIr color={colores.textoSecundario} size={16} />
      )}
    </Presionable>
  );
}

const useEstilos = crearEstilos(({ colores, texto }) => ({
  fila: { flexDirection: 'row', alignItems: 'center', gap: espacio.s + 4, paddingVertical: espacio.s + 4 },
  // Línea fina entre una fila y la siguiente.
  separador: { borderBottomWidth: 1, borderBottomColor: colores.borde },
  foto: {
    width: TAMAÑO_FOTO,
    height: TAMAÑO_FOTO,
    borderRadius: radio.m,
    backgroundColor: colores.superficie,
  },
  muestra: {
    position: 'absolute',
    right: -4,
    bottom: -4,
    width: 18,
    height: 18,
    borderRadius: 9,
    borderWidth: 2,
    borderColor: colores.superficieSuave,
  },
  datos: { flex: 1, minWidth: 0, gap: 1 },
  nombre: { ...texto.cuerpoFuerte, fontFamily: fuentes.negrita, fontSize: 15, lineHeight: 20 },
  estado: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 2 },
  punto: { width: 8, height: 8, borderRadius: 4 },
  textoEstado: { fontFamily: fuentes.media, fontSize: 13, lineHeight: 18, color: colores.textoSecundario },
  accion: { fontFamily: fuentes.media, fontSize: 14, color: colores.primario },
}));

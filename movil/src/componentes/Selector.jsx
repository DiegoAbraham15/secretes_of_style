// Selector de una sola opción: cada opción es una pastilla que se puede tocar (mínimo 44 pt de alto).
// enLinea: las pastillas quedan en una sola fila que se desliza de lado.
// etiquetaGrupo: nombre del grupo para el lector de pantalla, si el título va fuera del selector.
import { Pressable, ScrollView, Text, View } from 'react-native';

import { crearEstilos, espacio, fuentes, presionado, radio } from '../tema';

export function Selector({ titulo, etiquetaGrupo = titulo, opciones, seleccionado, alCambiar, enLinea = false, estilo }) {
  const estilos = useEstilos();

  const pastillas = opciones.map((opcion) => {
    const activa = opcion.valor === seleccionado;
    return (
      <Pressable
        key={String(opcion.valor)}
        onPress={() => alCambiar(opcion.valor)}
        accessibilityRole="radio"
        accessibilityLabel={opcion.etiqueta}
        accessibilityState={{ selected: activa, checked: activa }}
        style={({ pressed }) => [estilos.pastilla, activa && estilos.pastillaActiva, pressed && presionado]}>
        {opcion.hex && <View style={[estilos.muestra, { backgroundColor: opcion.hex }]} />}
        <Text style={[estilos.etiqueta, activa && estilos.etiquetaActiva]}>{opcion.etiqueta}</Text>
      </Pressable>
    );
  });

  return (
    <View style={[{ marginBottom: espacio.l }, estilo]} accessibilityRole="radiogroup" accessibilityLabel={etiquetaGrupo}>
      {titulo && <Text style={estilos.titulo}>{titulo}</Text>}
      {enLinea ? (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={estilos.filaEnLinea}>
          {pastillas}
        </ScrollView>
      ) : (
        <View style={estilos.fila}>{pastillas}</View>
      )}
    </View>
  );
}

const useEstilos = crearEstilos(({ colores, texto }) => ({
  titulo: { ...texto.antetitulo, marginBottom: espacio.s },
  fila: { flexDirection: 'row', flexWrap: 'wrap', gap: espacio.s },
  filaEnLinea: { flexDirection: 'row', gap: espacio.s, paddingHorizontal: espacio.m },
  pastilla: {
    minHeight: 44,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: espacio.m,
    borderRadius: radio.pastilla,
    borderWidth: 1,
    borderColor: colores.borde,
    backgroundColor: colores.superficie,
  },
  pastillaActiva: { backgroundColor: colores.texto, borderColor: colores.texto },
  muestra: {
    width: 14,
    height: 14,
    borderRadius: 7,
    marginRight: espacio.s,
    borderWidth: 1,
    borderColor: colores.bordeControl,
  },
  etiqueta: { fontFamily: fuentes.media, fontSize: 14, color: colores.texto },
  etiquetaActiva: { color: colores.fondo },
}));

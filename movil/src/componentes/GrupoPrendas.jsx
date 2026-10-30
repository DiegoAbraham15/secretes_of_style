// Prendas en filas juntas dentro de un bloque suave. Con etiqueta lleva encabezado: el nombre del grupo y,
// a la derecha, el total o el enlace "Ver las N" si limite deja prendas fuera (lo atiende alVerTodas).
// compacto: encabezado pequeño, para cuando el grupo va dentro de un paso. El resto de las opciones
// (conEstado, accion) pasa a cada FilaPrenda; seleccionadaId marca la fila de esa prenda.
import { Pressable, Text, View } from 'react-native';

import { IconoIr } from '../iconos';
import { crearEstilos, espacio, fuentes, presionado, radio, tactil, useTema } from '../tema';
import { FilaPrenda } from './FilaPrenda';

// Con "Todas", cada categoría enseña sus primeras prendas y un enlace para ver el resto.
export const POR_GRUPO = 3;

export function GrupoPrendas({
  etiqueta,
  prendas,
  limite = prendas.length,
  compacto = false,
  seleccionadaId,
  alVerTodas,
  alPresionar,
  ...fila
}) {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const mostradas = prendas.slice(0, limite);

  return (
    <View style={estilos.grupo}>
      {etiqueta && (
        <View style={estilos.cabecera}>
          <Text style={[compacto ? estilos.tituloCompacto : texto.subtitulo, { flex: 1 }]} accessibilityRole="header">
            {etiqueta}
          </Text>
          {mostradas.length < prendas.length ? (
            <Pressable
              onPress={alVerTodas}
              accessibilityRole="button"
              accessibilityLabel={`Ver las ${prendas.length} prendas de ${etiqueta.toLowerCase()}`}
              hitSlop={12}
              style={({ pressed }) => [estilos.enlace, pressed && presionado]}>
              <Text style={estilos.textoEnlace}>Ver las {prendas.length}</Text>
              <IconoIr color={colores.primario} size={14} weight="bold" />
            </Pressable>
          ) : (
            <Text style={texto.nota}>
              {prendas.length} {prendas.length === 1 ? 'prenda' : 'prendas'}
            </Text>
          )}
        </View>
      )}

      <View style={estilos.filas}>
        {mostradas.map((prenda, i) => (
          <FilaPrenda
            key={prenda.id}
            prenda={prenda}
            seleccionada={prenda.id === seleccionadaId}
            ultima={i === mostradas.length - 1}
            alPresionar={() => alPresionar(prenda)}
            {...fila}
          />
        ))}
      </View>
    </View>
  );
}

const useEstilos = crearEstilos(({ colores }) => ({
  grupo: { gap: espacio.s + 4 },
  cabecera: { flexDirection: 'row', alignItems: 'center', gap: espacio.s },
  tituloCompacto: { fontFamily: fuentes.negrita, fontSize: 16, lineHeight: 24, color: colores.texto },
  enlace: { flexDirection: 'row', alignItems: 'center', gap: 2, minHeight: tactil },
  textoEnlace: { fontFamily: fuentes.media, fontSize: 14, color: colores.primario },
  filas: { paddingHorizontal: espacio.m, borderRadius: radio.l, backgroundColor: colores.superficieSuave },
}));

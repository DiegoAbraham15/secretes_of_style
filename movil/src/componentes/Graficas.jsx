// Gráficas de la pestaña Estadísticas, dibujadas con componentes de React Native.
// Cada dato usa la forma que le toca: el total es un número grande, los indicadores son una lista,
// lo que no tiene orden (categorías, colores) son barras y lo que sí lo tiene (abrigo) son columnas.
// Las barras son de un solo color y la mayor va resaltada: la longitud ya dice el valor, el color solo destaca.
import { useEffect, useState } from 'react';
import { Animated, Pressable, Text, View } from 'react-native';

import { IconoAbrir, IconoCerrar } from '../iconos';
import { useReducirMovimiento } from '../movimiento';
import { crearEstilos, duracion, espacio, fuentes, presionado, radio, tactil, useTema } from '../tema';

const ALTO_COLUMNAS = 96;

const porcentaje = (valor, total) => Math.round((100 * valor) / (total || 1));

// "12 de 36 prendas, 33 %": lo que se lee al tocar una barra o una columna.
const detalleDe = (dato, total, unidad) => `${dato.valor} de ${total} ${unidad}, ${porcentaje(dato.valor, total)} %`;

// Va de 0 a 1 cuando llegan los datos: las barras crecen desde su base. Se omite con "Reducir movimiento".
function useCrecer(repeticion) {
  const reducir = useReducirMovimiento();
  const [avance] = useState(() => new Animated.Value(0));

  useEffect(() => {
    avance.setValue(reducir ? 1 : 0);
    if (reducir) return undefined;
    const animacion = Animated.timing(avance, { toValue: 1, duration: duracion.lenta, useNativeDriver: true });
    animacion.start();
    return () => animacion.stop();
  }, [avance, repeticion, reducir]);

  return avance;
}

// Solo se resalta la mayor si es única: con empate ninguna destaca.
function resumirDatos(datos) {
  const maximo = Math.max(...datos.map((d) => d.valor), 1);
  return {
    maximo,
    total: datos.reduce((suma, d) => suma + d.valor, 0),
    hayUnaMayor: datos.filter((d) => d.valor === maximo).length === 1,
  };
}

// ---------- Total y hallazgo ----------

// Lo primero que se ve: el único bloque de color de la pantalla.
export function Resumen({ total, hallazgo }) {
  const estilos = useEstilos();
  return (
    <View style={estilos.resumen}>
      <View style={estilos.filaTotal} accessible accessibilityLabel={`${total} prendas en tu armario`}>
        <Text style={estilos.numeroTotal}>{total}</Text>
        <Text style={estilos.textoTotal}>{total === 1 ? 'prenda en tu armario' : 'prendas en tu armario'}</Text>
      </View>
      <Text style={estilos.hallazgo}>{hallazgo}</Text>
    </View>
  );
}

// ---------- Indicadores ----------

// Lista de datos sueltos: cuadro con un ícono o un color, título, explicación y el valor a la derecha.
// filas: [{ icono?, hex?, titulo, detalle, valor }]
export function Indicadores({ filas }) {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  return (
    <View style={estilos.bloque}>
      {filas.map((fila, i) => (
        <View
          key={fila.titulo}
          style={[estilos.indicador, i < filas.length - 1 && estilos.separador]}
          accessible
          accessibilityLabel={`${fila.detalle}: ${fila.titulo}, ${fila.valor}`}>
          <View style={[estilos.cuadro, fila.hex && { backgroundColor: fila.hex, borderWidth: 1, borderColor: colores.bordeControl }]}>
            {fila.icono && <fila.icono color={colores.primario} size={20} />}
          </View>
          <View style={estilos.datosIndicador}>
            <Text style={estilos.tituloIndicador} numberOfLines={1}>
              {fila.titulo}
            </Text>
            <Text style={texto.nota} numberOfLines={1}>
              {fila.detalle}
            </Text>
          </View>
          <Text style={estilos.valorIndicador}>{fila.valor}</Text>
        </View>
      ))}
    </View>
  );
}

// ---------- Sección ----------

// Título a la izquierda y, si se pasa, un dato a la derecha; debajo, la gráfica.
export function Seccion({ titulo, nota, children }) {
  const { texto } = useTema();
  const estilos = useEstilos();
  return (
    <View style={estilos.seccion}>
      <View style={estilos.cabeceraSeccion}>
        <Text style={[texto.subtitulo, { flex: 1 }]} accessibilityRole="header">
          {titulo}
        </Text>
        {nota && <Text style={texto.nota}>{nota}</Text>}
      </View>
      {children}
    </View>
  );
}

// ---------- Barras horizontales ----------

// datos: [{ etiqueta, valor, hex? }], de mayor a menor. hex: círculo con el color de la prenda junto al nombre.
// La barra más larga es la mayor; tocar una fila muestra su detalle. Con limite, el resto se abre con un enlace.
export function GraficaBarras({ datos, unidad, repeticion, limite = datos.length }) {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const avance = useCrecer(repeticion);
  const [seleccionada, establecerSeleccionada] = useState(null);
  const [abierta, establecerAbierta] = useState(false);
  const { maximo, total, hayUnaMayor } = resumirDatos(datos);
  const visibles = abierta ? datos : datos.slice(0, limite);

  return (
    <View style={estilos.bloque}>
      {visibles.map((dato) => {
        const esMayor = dato.valor === maximo && hayUnaMayor;
        const activa = dato.etiqueta === seleccionada;
        return (
          <Pressable
            key={dato.etiqueta}
            onPress={() => establecerSeleccionada(activa ? null : dato.etiqueta)}
            accessibilityRole="button"
            accessibilityState={{ selected: activa }}
            accessibilityLabel={`${dato.etiqueta}: ${detalleDe(dato, total, unidad)}${esMayor ? ', el mayor' : ''}`}
            style={({ pressed }) => [estilos.filaBarra, pressed && presionado]}>
            <View style={estilos.encabezadoBarra}>
              {dato.hex && <View style={[estilos.muestra, { backgroundColor: dato.hex }]} />}
              <Text style={[estilos.etiqueta, esMayor && estilos.etiquetaMayor]} numberOfLines={1}>
                {dato.etiqueta}
              </Text>
              <Text style={estilos.valor}>{dato.valor}</Text>
            </View>
            <Animated.View
              style={[
                estilos.barra,
                {
                  width: `${(100 * dato.valor) / maximo}%`,
                  backgroundColor: esMayor ? colores.primario : colores.secundario,
                  transform: [{ scaleX: avance }],
                },
              ]}
            />
            {activa && (
              <Text style={[texto.nota, { marginTop: espacio.xs }]} accessibilityLiveRegion="polite">
                {detalleDe(dato, total, unidad)}
              </Text>
            )}
          </Pressable>
        );
      })}

      {datos.length > limite && (
        <Pressable
          onPress={() => establecerAbierta(!abierta)}
          accessibilityRole="button"
          accessibilityState={{ expanded: abierta }}
          style={({ pressed }) => [estilos.enlace, pressed && presionado]}>
          <Text style={estilos.textoEnlace}>{abierta ? 'Ver menos' : `Ver los ${datos.length}`}</Text>
          {abierta ? (
            <IconoCerrar color={colores.primario} size={14} weight="bold" />
          ) : (
            <IconoAbrir color={colores.primario} size={14} weight="bold" />
          )}
        </Pressable>
      )}
    </View>
  );
}

// ---------- Columnas ----------

// Para datos con orden: se ve de un vistazo hacia qué lado se carga la distribución.
// datos: [{ corta, etiqueta, valor }]. inicio y fin explican los dos extremos del eje.
export function GraficaColumnas({ datos, unidad, repeticion, inicio, fin }) {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const avance = useCrecer(repeticion);
  const [seleccionada, establecerSeleccionada] = useState(null);
  const { maximo, total, hayUnaMayor } = resumirDatos(datos);
  const elegida = datos.find((d) => d.etiqueta === seleccionada);

  return (
    <View style={estilos.bloque}>
      <View style={estilos.columnas}>
        {datos.map((dato) => {
          const esMayor = dato.valor === maximo && hayUnaMayor;
          const activa = dato.etiqueta === seleccionada;
          return (
            <Pressable
              key={dato.etiqueta}
              onPress={() => establecerSeleccionada(activa ? null : dato.etiqueta)}
              accessibilityRole="button"
              accessibilityState={{ selected: activa }}
              accessibilityLabel={`${dato.etiqueta}: ${detalleDe(dato, total, unidad)}${esMayor ? ', el mayor' : ''}`}
              style={({ pressed }) => [estilos.columna, pressed && presionado]}>
              <Text style={[estilos.valorColumna, activa && estilos.etiquetaMayor]}>{dato.valor}</Text>
              <Animated.View
                style={[
                  estilos.barraColumna,
                  {
                    height: Math.max((ALTO_COLUMNAS * dato.valor) / maximo, 2),
                    backgroundColor: esMayor ? colores.primario : colores.secundario,
                    transform: [{ scaleY: avance }],
                  },
                ]}
              />
              <Text style={[texto.nota, activa && estilos.etiquetaMayor]}>{dato.corta}</Text>
            </Pressable>
          );
        })}
      </View>

      <View style={estilos.ejeColumnas}>
        <Text style={texto.nota}>{inicio}</Text>
        <Text style={texto.nota}>{fin}</Text>
      </View>
      {elegida && (
        <Text style={[texto.detalle, { marginBottom: espacio.s + 4, color: colores.texto }]} accessibilityLiveRegion="polite">
          {elegida.etiqueta}: {detalleDe(elegida, total, unidad)}
        </Text>
      )}
    </View>
  );
}

const useEstilos = crearEstilos(({ colores, texto }) => ({
  resumen: { padding: espacio.m, borderRadius: radio.l, backgroundColor: colores.primarioSuave, gap: espacio.s },
  filaTotal: { flexDirection: 'row', alignItems: 'flex-end', gap: espacio.s + 4 },
  numeroTotal: { fontFamily: fuentes.display, fontSize: 88, lineHeight: 96, letterSpacing: -3, color: colores.primario },
  textoTotal: { ...texto.cuerpo, flex: 1, paddingBottom: espacio.m },
  hallazgo: { fontFamily: fuentes.displayItalica, fontSize: 20, lineHeight: 28, color: colores.texto },

  // Bloque suave donde van las filas, igual que en el Armario.
  bloque: { paddingHorizontal: espacio.m, paddingVertical: espacio.xs, borderRadius: radio.l, backgroundColor: colores.superficieSuave },
  seccion: { gap: espacio.s + 4 },
  cabeceraSeccion: { flexDirection: 'row', alignItems: 'baseline', gap: espacio.s },

  indicador: { flexDirection: 'row', alignItems: 'center', gap: espacio.s + 4, paddingVertical: espacio.s + 4 },
  separador: { borderBottomWidth: 1, borderBottomColor: colores.borde },
  cuadro: {
    width: 40,
    height: 40,
    borderRadius: radio.m,
    backgroundColor: colores.primarioSuave,
    alignItems: 'center',
    justifyContent: 'center',
  },
  datosIndicador: { flex: 1, minWidth: 0 },
  tituloIndicador: { fontFamily: fuentes.negrita, fontSize: 15, lineHeight: 20, color: colores.texto },
  valorIndicador: { fontFamily: fuentes.display, fontSize: 28, lineHeight: 34, color: colores.texto },

  filaBarra: { minHeight: tactil, justifyContent: 'center', paddingVertical: espacio.s },
  encabezadoBarra: { flexDirection: 'row', alignItems: 'center', gap: espacio.s, marginBottom: 6 },
  muestra: { width: 14, height: 14, borderRadius: 7, borderWidth: 1, borderColor: colores.bordeControl },
  etiqueta: { ...texto.etiqueta, flex: 1, fontFamily: fuentes.regular, fontSize: 15 },
  etiquetaMayor: { fontFamily: fuentes.negrita, color: colores.texto },
  valor: { fontFamily: fuentes.negrita, fontSize: 15, color: colores.texto },
  barra: { height: 8, borderRadius: 4, minWidth: 4, transformOrigin: 'left' },
  enlace: { flexDirection: 'row', alignItems: 'center', gap: 4, minHeight: tactil, alignSelf: 'flex-start' },
  textoEnlace: { fontFamily: fuentes.media, fontSize: 14, color: colores.primario },

  columnas: { flexDirection: 'row', alignItems: 'flex-end', gap: espacio.s, paddingTop: espacio.s + 4 },
  columna: { flex: 1, alignItems: 'center', justifyContent: 'flex-end', minHeight: tactil, gap: espacio.xs },
  valorColumna: { fontFamily: fuentes.media, fontSize: 14, lineHeight: 20, color: colores.texto },
  barraColumna: { alignSelf: 'stretch', borderTopLeftRadius: 4, borderTopRightRadius: 4, transformOrigin: 'bottom' },
  ejeColumnas: { flexDirection: 'row', justifyContent: 'space-between', paddingTop: espacio.xs, paddingBottom: espacio.s },
}));

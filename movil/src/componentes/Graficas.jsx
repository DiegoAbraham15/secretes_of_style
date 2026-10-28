// Gráficas de la pestaña Estadísticas, dibujadas con componentes de React Native.
import { useEffect, useState } from 'react';
import { Animated, Pressable, Text, View } from 'react-native';

import { Aparecer, useReducirMovimiento } from '../movimiento';
import { crearEstilos, duracion, espacio, fuentes, presionado, radio, useTema } from '../tema';

const porcentaje = (valor, total) => Math.round((100 * valor) / (total || 1));

// ---------- Resumen en cuadrícula Bento ----------

// Celdas de distinto tamaño (estilo Apple): el total grande arriba, el color más usado alto a la
// izquierda y dos indicadores chicos a la derecha. Entran en cascada.
// color: { etiqueta, hex } del color más usado (o null).
export function ResumenBento({ total, color, impermeables, guardados }) {
  const { colores, texto } = useTema();
  const estilos = useEstilos();

  return (
    <View style={estilos.bento}>
      <Aparecer indice={0}>
        <View style={estilos.heroe} accessible accessibilityLabel={`${total} prendas en tu armario`}>
          <Text style={[texto.antetitulo, { color: colores.sobrePrimario, opacity: 0.85 }]}>Tu armario</Text>
          <Text style={estilos.numeroHeroe}>{total}</Text>
          <Text style={[texto.cuerpoFuerte, { color: colores.sobrePrimario }]}>
            {total === 1 ? 'prenda' : 'prendas'}
          </Text>
        </View>
      </Aparecer>

      <View style={estilos.filaBento}>
        <Aparecer indice={1} estilo={{ flex: 1.15 }}>
          <View
            style={[estilos.celda, { flex: 1, justifyContent: 'space-between' }]}
            accessible
            accessibilityLabel={`Color más usado: ${color?.etiqueta ?? 'ninguno'}`}>
            <View style={[estilos.muestraGrande, { backgroundColor: color?.hex ?? colores.superficieSuave }]} />
            <View>
              <Text style={texto.subtitulo}>{color?.etiqueta ?? 'Ninguno'}</Text>
              <Text style={texto.nota}>color más usado</Text>
            </View>
          </View>
        </Aparecer>

        <View style={estilos.columnaBento}>
          {[
            { valor: impermeables, etiqueta: 'impermeables' },
            { valor: guardados, etiqueta: 'atuendos guardados' },
          ].map((celda, i) => (
            <Aparecer key={celda.etiqueta} indice={i + 2}>
              <View style={estilos.celda} accessible accessibilityLabel={`${celda.valor} ${celda.etiqueta}`}>
                <Text style={estilos.numero}>{celda.valor}</Text>
                <Text style={texto.nota}>{celda.etiqueta}</Text>
              </View>
            </Aparecer>
          ))}
        </View>
      </View>
    </View>
  );
}

// ---------- Anotación del hallazgo ----------

export function Hallazgo({ children }) {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  return (
    <View style={estilos.hallazgo}>
      <Text style={[texto.antetitulo, { color: colores.primario, marginBottom: espacio.xs }]}>Lo más importante</Text>
      <Text style={estilos.textoHallazgo}>{children}</Text>
    </View>
  );
}

// ---------- Gráfica de barras horizontales ----------

// datos: [{ etiqueta, valor, color? }]. color: pinta la barra (p. ej. el color de la prenda).
// pregunta: lo que responde la gráfica. repeticion: cambia para volver a animar.
export function GraficaBarras({ titulo, pregunta, datos, unidad, repeticion }) {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const reducir = useReducirMovimiento();
  const [seleccionada, establecerSeleccionada] = useState(null);
  const [avance] = useState(() => new Animated.Value(0)); // va de 0 a 1 durante la animación

  const total = datos.reduce((suma, d) => suma + d.valor, 0);
  const maximo = Math.max(...datos.map((d) => d.valor), 1);
  // Solo se destaca la mayor si es única: con empate ninguna barra se marca como "Mayor".
  const hayUnaMayor = datos.filter((d) => d.valor === maximo).length === 1;
  const usaColores = datos.some((d) => d.color);

  // Animación de entrada: las barras crecen desde la izquierda con scaleX (transform, no el ancho, así
  // corre en el hilo nativo). Se omite si el usuario redujo el movimiento.
  useEffect(() => {
    avance.setValue(reducir ? 1 : 0);
    if (reducir) return undefined;
    const animacion = Animated.timing(avance, { toValue: 1, duration: duracion.lenta, useNativeDriver: true });
    animacion.start();
    return () => animacion.stop();
  }, [avance, repeticion, reducir]);

  const elegida = datos.find((d) => d.etiqueta === seleccionada);

  return (
    <View style={estilos.tarjeta}>
      <Text style={texto.subtitulo}>{titulo}</Text>
      {pregunta && <Text style={[texto.detalle, { marginTop: 2 }]}>{pregunta}</Text>}

      <View style={{ marginTop: espacio.m, gap: espacio.s }}>
        {datos.map((dato) => {
          const esMaximo = dato.valor === maximo && hayUnaMayor;
          const activa = dato.etiqueta === seleccionada;
          const relleno = dato.color ?? (esMaximo ? colores.primario : colores.secundario);

          return (
            <Pressable
              key={dato.etiqueta}
              onPress={() => establecerSeleccionada(activa ? null : dato.etiqueta)}
              accessibilityRole="button"
              accessibilityState={{ selected: activa }}
              accessibilityLabel={
                `${dato.etiqueta}: ${dato.valor} ${unidad}, ${porcentaje(dato.valor, total)} por ciento` +
                (esMaximo ? ', el mayor' : '')
              }
              style={({ pressed }) => [estilos.fila, activa && estilos.filaActiva, pressed && presionado]}>
              {/* Encabezado de la barra: nombre a la izquierda, cantidad y porcentaje a la derecha */}
              <View style={estilos.encabezadoFila}>
                {dato.color && <View style={[estilos.muestra, { backgroundColor: dato.color }]} />}
                <Text style={[estilos.etiqueta, esMaximo && estilos.etiquetaFuerte]} numberOfLines={1}>
                  {dato.etiqueta}
                </Text>
                {esMaximo && <Text style={estilos.insignia}>Mayor</Text>}
                <Text style={estilos.valor}>{dato.valor}</Text>
                <Text style={estilos.porcentaje}>{porcentaje(dato.valor, total)} %</Text>
              </View>

              {/* La pista es el 100 % del armario; la barra rellena la parte que le toca */}
              <View style={estilos.pista}>
                <Animated.View
                  style={[
                    estilos.barra,
                    { width: `${porcentaje(dato.valor, total)}%`, backgroundColor: relleno },
                    dato.valor > 0 && { minWidth: 6 },
                    dato.color && estilos.barraDeColor,
                    { transform: [{ scaleX: avance }] },
                  ]}
                />
              </View>
            </Pressable>
          );
        })}
      </View>

      {/* Detalle del dato que se tocó, o cómo leer la gráfica */}
      <View style={estilos.pie} accessibilityLiveRegion="polite">
        <Text style={[texto.detalle, elegida && { color: colores.texto }]}>
          {elegida
            ? `${elegida.etiqueta}: ${elegida.valor} de ${total} ${unidad} (${porcentaje(elegida.valor, total)} %).` +
              (elegida.valor === maximo ? (hayUnaMayor ? ' Es lo que más tienes.' : ' Empata en el primer lugar.') : '')
            : usaColores
              ? `Cada barra va del color de la prenda. La barra llena serían tus ${total} ${unidad}. Toca una para ver el detalle.`
              : `${hayUnaMayor ? 'La barra marcada como «Mayor» es la más alta.' : 'Hay un empate en el primer lugar.'} La barra llena serían tus ${total} ${unidad}. Toca una para ver el detalle.`}
        </Text>
      </View>
    </View>
  );
}

const useEstilos = crearEstilos(({ colores, texto, tarjeta }) => ({
  bento: { gap: espacio.s + 4 },
  heroe: { ...tarjeta, backgroundColor: colores.primario, borderWidth: 0, padding: espacio.l },
  numeroHeroe: {
    fontFamily: fuentes.negra,
    fontSize: 72,
    lineHeight: 76,
    letterSpacing: -3,
    color: colores.sobrePrimario,
    marginTop: espacio.xs,
  },
  filaBento: { flexDirection: 'row', gap: espacio.s + 4 },
  columnaBento: { flex: 1, gap: espacio.s + 4 },
  celda: { ...tarjeta, padding: espacio.m, gap: espacio.xs },
  numero: { fontFamily: fuentes.negra, fontSize: 36, lineHeight: 40, letterSpacing: -1, color: colores.texto },
  muestraGrande: {
    width: 48,
    height: 48,
    borderRadius: 24,
    borderWidth: 1,
    borderColor: colores.bordeControl,
    marginBottom: espacio.l,
  },

  hallazgo: { ...tarjeta, backgroundColor: colores.primarioSuave, borderWidth: 0, padding: espacio.m, marginVertical: espacio.l },
  textoHallazgo: { ...texto.cuerpoFuerte, fontSize: 17, lineHeight: 25 },

  tarjeta: { ...tarjeta, padding: espacio.m, marginBottom: espacio.m },
  fila: { borderRadius: radio.m, padding: espacio.s, margin: -espacio.s, minHeight: 44 },
  filaActiva: { backgroundColor: colores.superficieSuave },
  encabezadoFila: { flexDirection: 'row', alignItems: 'center', marginBottom: 6 },
  muestra: {
    width: 14,
    height: 14,
    borderRadius: 7,
    marginRight: espacio.s,
    borderWidth: 1,
    borderColor: colores.bordeControl,
  },
  etiqueta: { ...texto.etiqueta, flexShrink: 1, fontFamily: fuentes.regular, fontSize: 15 },
  etiquetaFuerte: { fontFamily: fuentes.negrita },
  insignia: {
    marginLeft: espacio.s,
    fontFamily: fuentes.negrita,
    fontSize: 12,
    color: colores.primario,
    backgroundColor: colores.primarioSuave,
    paddingHorizontal: espacio.s,
    paddingVertical: 2,
    borderRadius: radio.pastilla,
    overflow: 'hidden',
  },
  valor: { marginLeft: 'auto', paddingLeft: espacio.s, fontFamily: fuentes.negrita, fontSize: 15, color: colores.texto },
  porcentaje: { ...texto.nota, width: 48, textAlign: 'right' },
  pista: { height: 12, borderRadius: 6, backgroundColor: colores.superficieSuave, overflow: 'hidden' },
  barra: { height: 12, borderRadius: 6, transformOrigin: 'left' },
  barraDeColor: { borderWidth: 1, borderColor: colores.bordeControl },
  pie: {
    marginTop: espacio.m,
    paddingTop: espacio.m,
    borderTopWidth: 1,
    borderTopColor: colores.superficieSuave,
    minHeight: 44,
  },
}));

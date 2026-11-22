// Segmentación con K-means, prendas atípicas y mapa PCA en la pestaña Estadísticas.
// Cada grupo tiene un número y un color fijos (colores.grupos del tema, máximo 4). El número va siempre
// dentro de la marca, así el grupo no depende solo del color. Tocar una prenda abre su detalle.
import { router } from 'expo-router';
import { useState } from 'react';
import { Pressable, ScrollView, Text, View } from 'react-native';

import { nombreConColor } from '../catalogos';
import { IconoIr } from '../iconos';
import { Presionable } from '../movimiento';
import { crearEstilos, espacio, fuentes, radio, tactil, useTema } from '../tema';
import { FotoPrenda } from './FotoPrenda';

const ALTO_MAPA = 280;
const TAMAÑO_PUNTO = 20;
const MARGEN_MAPA = 24; // que ningún punto (con su desplazamiento) se salga del lienzo
const SEPARACION_IGUALES = 9; // prendas idénticas caen en el mismo lugar: se reparten en un círculo de este radio

const abrirPrenda = (id) => router.push(`/prenda/${id}`);

// ---------- Marca de grupo ----------

function MarcaGrupo({ numero, tamaño = 24 }) {
  const { colores } = useTema();
  const estilos = useEstilos();
  return (
    <View
      style={[
        estilos.marca,
        { width: tamaño, height: tamaño, borderRadius: tamaño / 2, backgroundColor: colores.grupos[numero - 1] },
      ]}>
      <Text style={[estilos.numeroMarca, { color: colores.sobreGrupos[numero - 1], fontSize: Math.round(tamaño * 0.5) }]}>
        {numero}
      </Text>
    </View>
  );
}

// ---------- Tus grupos de ropa (K-means) ----------

// grupos: [{ numero, nombre, prendas: [id] }]; prendas: { id: prenda }. Es también la leyenda del mapa.
export function GruposDeRopa({ grupos, prendas }) {
  const { colores } = useTema();
  const estilos = useEstilos();
  return (
    <View style={estilos.bloque}>
      {grupos.map((grupo, i) => (
        <View key={grupo.numero} style={[estilos.grupo, i < grupos.length - 1 && estilos.separador]}>
          <View
            style={estilos.cabeceraGrupo}
            accessible
            accessibilityLabel={`Grupo ${grupo.numero}: ${grupo.nombre}, ${grupo.prendas.length} prendas`}>
            <MarcaGrupo numero={grupo.numero} />
            <Text style={estilos.nombreGrupo} numberOfLines={2}>
              {grupo.nombre}
            </Text>
            <Text style={[estilos.cuenta, { color: colores.texto }]}>{grupo.prendas.length}</Text>
          </View>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={estilos.tira}>
            {grupo.prendas.map((id) => (
              <Presionable
                key={id}
                onPress={() => abrirPrenda(id)}
                accessibilityRole="button"
                accessibilityLabel={nombreConColor(prendas[id])}>
                <FotoPrenda prenda={prendas[id]} style={estilos.miniatura} />
              </Presionable>
            ))}
          </ScrollView>
        </View>
      ))}
    </View>
  );
}

// ---------- Mapa de tu armario (PCA) ----------

// Lugar de cada punto en el lienzo. Las prendas idénticas se reparten alrededor de su lugar para que se vea cada una.
function repartir(puntos, enX, enY) {
  const porLugar = {};
  puntos.forEach((punto) => (porLugar[`${punto.x},${punto.y}`] ??= []).push(punto));
  return Object.values(porLugar).flatMap((iguales) =>
    iguales.map((punto, i) => {
      const angulo = (2 * Math.PI * i) / iguales.length;
      const radioCirculo = iguales.length > 1 ? SEPARACION_IGUALES : 0;
      return { punto, x: enX(punto.x) + radioCirculo * Math.cos(angulo), y: enY(punto.y) + radioCirculo * Math.sin(angulo) };
    }),
  );
}

// mapa: { conservado, eje_x: { positivo, negativo }, eje_y, puntos: [{ id, grupo, x, y }] }
export function MapaArmario({ mapa, grupos, prendas }) {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const [ancho, establecerAncho] = useState(0);
  const [elegida, establecerElegida] = useState(null);

  const xs = mapa.puntos.map((p) => p.x);
  const ys = mapa.puntos.map((p) => p.y);
  const [minX, maxX, minY, maxY] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const enX = (x) => MARGEN_MAPA + ((x - minX) / (maxX - minX || 1)) * (ancho - 2 * MARGEN_MAPA);
  const enY = (y) => MARGEN_MAPA + ((maxY - y) / (maxY - minY || 1)) * (ALTO_MAPA - 2 * MARGEN_MAPA); // arriba = PC2 alto
  // La elegida se dibuja al final para que quede encima de las demás.
  const lugares = repartir(mapa.puntos, enX, enY).sort((a, b) => (a.punto.id === elegida) - (b.punto.id === elegida));
  const puntoElegido = mapa.puntos.find((p) => p.id === elegida);
  const grupoElegido = puntoElegido && grupos.find((g) => g.numero === puntoElegido.grupo);

  return (
    <View style={estilos.bloque}>
      <Text style={[texto.nota, estilos.ejeVerticalTexto]}>↑ {mapa.eje_y.positivo}</Text>
      <View
        style={[estilos.lienzo, { height: ALTO_MAPA }]}
        onLayout={(evento) => establecerAncho(evento.nativeEvent.layout.width)}
        accessibilityLabel={`Mapa de tus prendas: hacia la derecha, ${mapa.eje_x.positivo}; hacia arriba, ${mapa.eje_y.positivo}`}>
        {ancho > 0 && (
          <>
            {/* Los ejes pasan por el promedio del armario (0 en PCA). */}
            <View style={[estilos.lineaVertical, { left: enX(0) }]} />
            <View style={[estilos.lineaHorizontal, { top: enY(0) }]} />
            {lugares.map(({ punto, x, y }) => {
              const activa = punto.id === elegida;
              return (
                <Pressable
                  key={punto.id}
                  onPress={() => establecerElegida(activa ? null : punto.id)}
                  accessibilityRole="button"
                  accessibilityState={{ selected: activa }}
                  accessibilityLabel={`${nombreConColor(prendas[punto.id])}, grupo ${punto.grupo}`}
                  style={[estilos.objetivo, { left: x - tactil / 2, top: y - tactil / 2 }]}>
                  <View
                    style={[
                      estilos.punto,
                      { backgroundColor: colores.grupos[punto.grupo - 1] },
                      activa && { borderColor: colores.texto, transform: [{ scale: 1.3 }] },
                    ]}>
                    <Text style={[estilos.numeroPunto, { color: colores.sobreGrupos[punto.grupo - 1] }]}>{punto.grupo}</Text>
                  </View>
                </Pressable>
              );
            })}
          </>
        )}
      </View>
      <Text style={[texto.nota, estilos.ejeVerticalTexto]}>↓ {mapa.eje_y.negativo}</Text>
      <View style={estilos.ejeHorizontalTexto}>
        <Text style={[texto.nota, { flex: 1 }]}>← {mapa.eje_x.negativo}</Text>
        <Text style={[texto.nota, { flex: 1, textAlign: 'right' }]}>{mapa.eje_x.positivo} →</Text>
      </View>

      {puntoElegido ? (
        <Presionable
          onPress={() => abrirPrenda(elegida)}
          escala={0.98}
          accessibilityRole="button"
          accessibilityLabel={`Ver ${nombreConColor(prendas[elegida])}`}
          style={estilos.elegida}>
          <FotoPrenda prenda={prendas[elegida]} style={estilos.fotoFila} />
          <View style={estilos.datosFila}>
            <Text style={estilos.nombrePrenda} numberOfLines={1}>
              {nombreConColor(prendas[elegida])}
            </Text>
            <View style={estilos.filaGrupo}>
              <MarcaGrupo numero={grupoElegido.numero} tamaño={16} />
              <Text style={[texto.nota, { flex: 1 }]} numberOfLines={1}>
                {grupoElegido.nombre}
              </Text>
            </View>
          </View>
          <IconoIr color={colores.textoSecundario} size={16} />
        </Presionable>
      ) : (
        <Text style={[texto.nota, estilos.ayuda]}>Toca un punto para ver qué prenda es.</Text>
      )}
    </View>
  );
}

// ---------- Prendas que no encajan (atípicas) ----------

// lista: [{ id, grupo }], de la más alejada de su grupo a la menos.
export function NoEncajan({ lista, grupos, prendas }) {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  return (
    <View style={estilos.bloque}>
      {lista.map((item, i) => {
        const prenda = prendas[item.id];
        const grupo = grupos.find((g) => g.numero === item.grupo);
        return (
          <Presionable
            key={item.id}
            onPress={() => abrirPrenda(item.id)}
            escala={0.98}
            accessibilityRole="button"
            accessibilityLabel={`${nombreConColor(prenda)}: distinta al resto del grupo ${grupo.numero}, ${grupo.nombre}`}
            style={[estilos.fila, i < lista.length - 1 && estilos.separador]}>
            <FotoPrenda prenda={prenda} style={estilos.fotoFila} />
            <View style={estilos.datosFila}>
              <Text style={estilos.nombrePrenda} numberOfLines={1}>
                {nombreConColor(prenda)}
              </Text>
              <View style={estilos.filaGrupo}>
                <MarcaGrupo numero={grupo.numero} tamaño={16} />
                <Text style={[texto.nota, { flex: 1 }]} numberOfLines={2}>
                  Distinta al resto de «{grupo.nombre}»
                </Text>
              </View>
            </View>
            <IconoIr color={colores.textoSecundario} size={16} />
          </Presionable>
        );
      })}
    </View>
  );
}

const useEstilos = crearEstilos(({ colores, texto, bloque, separador }) => ({
  bloque,
  separador,

  marca: { alignItems: 'center', justifyContent: 'center' },
  numeroMarca: { fontFamily: fuentes.negrita, includeFontPadding: false },

  grupo: { paddingVertical: espacio.s + 4, gap: espacio.s + 4 },
  cabeceraGrupo: { flexDirection: 'row', alignItems: 'center', gap: espacio.s + 4 },
  nombreGrupo: { flex: 1, fontFamily: fuentes.negrita, fontSize: 15, lineHeight: 20, color: colores.texto },
  cuenta: { fontFamily: fuentes.display, fontSize: 24, lineHeight: 30 },
  tira: { gap: espacio.s },
  miniatura: { width: 56, height: 56, borderRadius: radio.s, backgroundColor: colores.superficie },

  lienzo: { marginHorizontal: -espacio.xs },
  lineaVertical: { position: 'absolute', top: 0, bottom: 0, width: 1, backgroundColor: colores.borde },
  lineaHorizontal: { position: 'absolute', left: 0, right: 0, height: 1, backgroundColor: colores.borde },
  objetivo: { position: 'absolute', width: tactil, height: tactil, alignItems: 'center', justifyContent: 'center' },
  punto: {
    width: TAMAÑO_PUNTO,
    height: TAMAÑO_PUNTO,
    borderRadius: TAMAÑO_PUNTO / 2,
    borderWidth: 2,
    borderColor: colores.superficieSuave, // anillo del color del fondo: separa los puntos que se enciman
    alignItems: 'center',
    justifyContent: 'center',
  },
  numeroPunto: { fontFamily: fuentes.negrita, fontSize: 10, lineHeight: 12, includeFontPadding: false },
  ejeVerticalTexto: { paddingTop: espacio.s },
  ejeHorizontalTexto: { flexDirection: 'row', gap: espacio.m, paddingBottom: espacio.s },
  ayuda: { paddingBottom: espacio.s + 4 },

  elegida: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.s + 4,
    paddingVertical: espacio.s + 4,
    borderTopWidth: 1,
    borderTopColor: colores.borde,
  },
  fila: { flexDirection: 'row', alignItems: 'center', gap: espacio.s + 4, paddingVertical: espacio.s + 4 },
  fotoFila: { width: 48, height: 48, borderRadius: radio.s, backgroundColor: colores.superficie },
  datosFila: { flex: 1, minWidth: 0, gap: 4 },
  nombrePrenda: { ...texto.cuerpoFuerte, fontFamily: fuentes.negrita, fontSize: 15, lineHeight: 20 },
  filaGrupo: { flexDirection: 'row', alignItems: 'center', gap: 6 },
}));

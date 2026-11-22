// ¿Vale la pena comprarla? Para una prenda de tu lista de Tiendas, el servidor la vuelve una prenda "virtual" con lo
// que vio la IA y cuenta con A* cuántos looks arma con tu ropa disponible (sin clima: lo que importa es si combina
// con tu armario). La compara con las prendas de esa categoría que ya tienes, busca si ya tienes una parecida y
// muestra dos looks de ejemplo ordenados con tus gustos. No se guarda nada ni cuenta como voto.
import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Text, View } from 'react-native';

import { valeLaPena } from '../../api';
import { HEX_COLOR, nombreConColor } from '../../catalogos';
import { FotoPrenda } from '../../componentes/FotoPrenda';
import { Indicadores } from '../../componentes/Graficas';
import { Perchero } from '../../componentes/Perchero';
import { IconoArmario, IconoAtuendos, IconoAviso, IconoBuenaCompra, IconoValeLaPena } from '../../iconos';
import { Aparecer } from '../../movimiento';
import { crearEstilos, espacio, fuentes, presionado, radio, tamañoIcono, useTema } from '../../tema';

const VEREDICTOS = {
  vale_la_pena: { titulo: 'Vale la pena', icono: IconoBuenaCompra },
  piensalo: { titulo: 'Piénsalo', icono: IconoValeLaPena },
  no_combina: { titulo: 'No combina con tu ropa', icono: IconoAviso },
};
const LAS_TUYAS = {
  parte_superior: 'partes de arriba',
  parte_inferior: 'partes de abajo',
  calzado: 'pares de zapatos',
  abrigo: 'abrigos',
  accesorio: 'accesorios',
};

export default function PantallaValeLaPena() {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const { id } = useLocalSearchParams();
  const [analisis, establecerAnalisis] = useState(null);
  const [error, establecerError] = useState(null);

  useEffect(() => {
    valeLaPena(id)
      .then(establecerAnalisis)
      .catch((e) => establecerError(e.message));
  }, [id]);

  if (error || !analisis) {
    return (
      <View style={estilos.centro}>
        {error ? (
          <Text style={[texto.cuerpo, { color: colores.error, textAlign: 'center' }]} accessibilityRole="alert">
            {error}
          </Text>
        ) : (
          <>
            <ActivityIndicator color={colores.primario} />
            <Text style={texto.detalle}>Armando looks con tu ropa…</Text>
          </>
        )}
      </View>
    );
  }

  const { prenda } = analisis;
  const veredicto = VEREDICTOS[analisis.veredicto];
  const tuyas = LAS_TUYAS[prenda.categoria];
  const filas = [
    {
      icono: IconoAtuendos,
      titulo: 'Looks con tu ropa',
      detalle: 'Armados con A* y tu ropa',
      valor: analisis.looks_tope ? `${analisis.looks}+` : analisis.looks,
    },
    {
      icono: IconoArmario,
      titulo: `Tus ${tuyas}`,
      detalle: analisis.comparadas ? `Looks en promedio (tienes ${analisis.comparadas})` : 'No tienes ninguno',
      valor: analisis.promedio_categoria === null ? '—' : Math.round(analisis.promedio_categoria),
    },
    {
      icono: IconoValeLaPena,
      titulo: 'Parecidas que ya tienes',
      detalle: 'Misma categoría y color',
      valor: analisis.parecidas.length,
    },
    {
      hex: HEX_COLOR[prenda.color_principal],
      titulo: 'Su color combina con',
      detalle: `De tus ${analisis.otras_prendas} prendas de otras categorías`,
      valor: analisis.combina_con,
    },
  ];

  return (
    <ScrollView style={estilos.pantalla} contentContainerStyle={estilos.contenido}>
      <Aparecer>
        <View style={estilos.cabecera}>
          <FotoPrenda prenda={prenda} style={estilos.foto} accessibilityLabel="Foto de la prenda de la tienda" />
          <View style={{ flex: 1, gap: espacio.xs }}>
            <Text style={texto.nota}>{nombreConColor(prenda)}</Text>
            <View style={estilos.fila} accessibilityRole="header">
              <veredicto.icono
                color={analisis.veredicto === 'no_combina' ? colores.error : colores.primario}
                size={tamañoIcono.m}
                weight="fill"
              />
              <Text style={estilos.veredicto}>{veredicto.titulo}</Text>
            </View>
            <Text style={[texto.detalle, { color: colores.texto }]}>{analisis.mensaje}</Text>
            {analisis.colorimetria && <Text style={texto.nota}>{analisis.colorimetria.texto}</Text>}
          </View>
        </View>
      </Aparecer>

      <Aparecer indice={1}>
        <Indicadores filas={filas} />
      </Aparecer>

      {analisis.parecidas.length > 0 && (
        <Aparecer indice={2} estilo={{ gap: espacio.s }}>
          <Text style={texto.subtitulo} accessibilityRole="header">
            Las parecidas que ya tienes
          </Text>
          <View style={estilos.fotos}>
            {analisis.parecidas.map((parecida) => (
              <Pressable
                key={parecida.id}
                onPress={() => router.push(`/prenda/${parecida.id}`)}
                accessibilityRole="button"
                accessibilityLabel={`${nombreConColor(parecida)}. Abrir`}
                style={({ pressed }) => pressed && presionado}>
                <FotoPrenda prenda={parecida} style={estilos.miniatura} />
              </Pressable>
            ))}
          </View>
        </Aparecer>
      )}

      {analisis.ejemplos.length > 0 && (
        <View style={{ gap: espacio.s }}>
          <Text style={texto.subtitulo} accessibilityRole="header">
            Así la usarías
          </Text>
          <Text style={texto.detalle}>Los looks que más van con tus gustos, armados con tu ropa.</Text>
          {analisis.ejemplos.map((ejemplo, indice) => (
            <Aparecer key={ejemplo.elementos.map((e) => e.prenda.id).join('-')} indice={indice + 3}>
              <Perchero
                sugerencia={ejemplo}
                numero={indice + 1}
                cuando="cualquier día"
                etiquetaBase="De la tienda"
                conProbador={false}
              />
            </Aparecer>
          ))}
        </View>
      )}

      <Text style={[texto.nota, { color: colores.textoSecundario }]}>
        Se calcula con tu ropa disponible, sin contar el clima, y no se guarda nada. Si la IA se equivocó de prenda o
        color, vuelve a tomarle foto.
      </Text>
    </ScrollView>
  );
}

const useEstilos = crearEstilos(({ colores }) => ({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  contenido: { padding: espacio.m, gap: espacio.l, paddingBottom: espacio.xxl },
  centro: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: espacio.s, padding: espacio.l, backgroundColor: colores.fondo },
  cabecera: { flexDirection: 'row', gap: espacio.m, alignItems: 'flex-start' },
  foto: { width: 104, aspectRatio: 3 / 4, borderRadius: radio.m, backgroundColor: colores.superficieSuave },
  fila: { flexDirection: 'row', alignItems: 'center', gap: espacio.s },
  veredicto: { fontFamily: fuentes.negrita, fontSize: 22, lineHeight: 28, color: colores.texto, flexShrink: 1 },
  fotos: { flexDirection: 'row', flexWrap: 'wrap', gap: espacio.s },
  miniatura: { width: 64, aspectRatio: 3 / 4, borderRadius: radio.s, backgroundColor: colores.superficieSuave },
}));

// Una cápsula guardada: sus prendas como checklist de equipaje (se marcan al meterlas a la maleta) y sus looks,
// recalculados con tu armario de hoy (si borraste o mandaste a lavar una prenda, se nota).
import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Text, View } from 'react-native';

import { eliminarCapsula, marcarEmpacadas, obtenerCapsula } from '../../../api';
import { nombreConColor } from '../../../catalogos';
import { Boton } from '../../../componentes/Boton';
import { FotoPrenda } from '../../../componentes/FotoPrenda';
import { TiraLook } from '../../../componentes/TiraLook';
import { confirmar } from '../../../confirmar';
import { IconoEliminar, IconoPalomita } from '../../../iconos';
import { vibrar } from '../../../movimiento';
import { crearEstilos, espacio, presionado, radio, tactil, useTema } from '../../../tema';

const LOOKS_VISIBLES = 20;

export default function PantallaCapsulaGuardada() {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const { id } = useLocalSearchParams();
  const [capsula, establecerCapsula] = useState(null);
  const [error, establecerError] = useState(null);

  useEffect(() => {
    obtenerCapsula(id)
      .then(establecerCapsula)
      .catch((e) => establecerError(e.message));
  }, [id]);

  // La marca se ve de inmediato y se revierte si el servidor no la guarda.
  async function alternar(prendaId) {
    const anterior = capsula.empacadas;
    const empacadas = anterior.includes(prendaId) ? anterior.filter((i) => i !== prendaId) : [...anterior, prendaId];
    vibrar.seleccion();
    establecerCapsula({ ...capsula, empacadas });
    try {
      establecerCapsula(await marcarEmpacadas(capsula.id, empacadas));
    } catch (e) {
      establecerCapsula({ ...capsula, empacadas: anterior });
      establecerError(e.message);
    }
  }

  if (!capsula) {
    return error ? (
      <Text style={[texto.cuerpo, { color: colores.error, margin: espacio.l }]}>{error}</Text>
    ) : (
      <ActivityIndicator color={colores.primario} style={{ marginTop: espacio.xxl }} />
    );
  }

  const porId = Object.fromEntries(capsula.prendas.map((p) => [p.id, p]));
  const listas = capsula.empacadas.length;
  const total = capsula.prendas.length;

  return (
    <ScrollView style={estilos.pantalla} contentContainerStyle={estilos.contenido}>
      <Text style={texto.titulo}>{capsula.nombre}</Text>
      <Text style={texto.detalle}>
        {total} prendas · {capsula.looks} looks
        {capsula.detalles?.lugar ? ` · ${capsula.detalles.lugar}, ${capsula.detalles.dias} días` : ''}
      </Text>

      <View style={{ gap: espacio.s }}>
        <View style={estilos.cabecera}>
          <Text style={[texto.subtitulo, { flex: 1 }]} accessibilityRole="header">
            {capsula.escenario === 'viaje' ? 'Tu maleta' : 'Tus prendas'}
          </Text>
          <Text style={texto.nota} accessibilityLiveRegion="polite">
            {listas} de {total} {capsula.escenario === 'viaje' ? 'empacadas' : 'listas'}
          </Text>
        </View>
        <View style={estilos.barra}>
          <View style={[estilos.relleno, { width: `${total ? (100 * listas) / total : 0}%` }]} />
        </View>
        {capsula.prendas.map((prenda) => {
          const marcada = capsula.empacadas.includes(prenda.id);
          return (
            <Pressable
              key={prenda.id}
              onPress={() => alternar(prenda.id)}
              accessibilityRole="checkbox"
              accessibilityState={{ checked: marcada }}
              accessibilityLabel={nombreConColor(prenda)}
              style={({ pressed }) => [estilos.fila, pressed && presionado]}>
              <View style={[estilos.casilla, marcada && estilos.casillaMarcada]}>
                {marcada && <IconoPalomita color={colores.sobrePrimario} size={14} weight="bold" />}
              </View>
              <FotoPrenda prenda={prenda} style={estilos.foto} />
              <Text style={[texto.cuerpo, { flex: 1 }, marcada && { color: colores.textoSecundario, textDecorationLine: 'line-through' }]}>
                {nombreConColor(prenda)}
              </Text>
            </Pressable>
          );
        })}
      </View>

      {capsula.combinaciones.length > 0 && (
        <View style={{ gap: espacio.s }}>
          <Text style={texto.subtitulo} accessibilityRole="header">
            Sus looks
          </Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: espacio.s }}>
            {capsula.combinaciones.slice(0, LOOKS_VISIBLES).map((ids, indice) => (
              <TiraLook key={ids.join('-')} titulo={`Look ${indice + 1}`} prendas={ids.map((i) => porId[i]).filter(Boolean)} ancho={210} />
            ))}
          </ScrollView>
        </View>
      )}

      {error && (
        <Text style={[texto.detalle, { color: colores.error }]} accessibilityRole="alert">
          {error}
        </Text>
      )}
      <Boton
        texto="Borrar cápsula"
        icono={IconoEliminar}
        peligro
        alPresionar={() =>
          confirmar('Borrar cápsula', '¿Borrar esta cápsula? Tus prendas siguen en el armario.', 'Borrar', async () => {
            await eliminarCapsula(capsula.id);
            router.back();
          })
        }
      />
    </ScrollView>
  );
}

const useEstilos = crearEstilos(({ colores }) => ({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  contenido: { padding: espacio.m, gap: espacio.l, paddingBottom: espacio.xxl },
  cabecera: { flexDirection: 'row', alignItems: 'center' },
  barra: { height: 6, borderRadius: 3, backgroundColor: colores.superficieSuave, overflow: 'hidden' },
  relleno: { height: '100%', backgroundColor: colores.exito },
  fila: { flexDirection: 'row', alignItems: 'center', gap: espacio.s + 4, minHeight: tactil },
  casilla: { width: 26, height: 26, borderRadius: radio.s + 2, borderWidth: 2, borderColor: colores.bordeControl, alignItems: 'center', justifyContent: 'center' },
  casillaMarcada: { backgroundColor: colores.primario, borderColor: colores.primario },
  foto: { width: 44, height: 44, borderRadius: radio.s, backgroundColor: colores.superficieSuave },
}));

// Cápsula de ropa: con un botón, el servidor elige de tu armario 15 prendas para el mes (o 10 para un viaje) que
// juntas arman la mayor cantidad de looks válidos (colores que combinan, sin dos estampados, aptos para el clima y la
// ocasión), equilibrando neutros y colores de acento. Ves las prendas, todos los looks y la guardas; en un viaje
// se vuelve tu checklist de equipaje.
import { router, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Text, View } from 'react-native';

import { buscarLugares, generarCapsula, guardarCapsula, listarCapsulas } from '../../api';
import { CATEGORIAS, OCASIONES } from '../../catalogos';
import { Boton } from '../../componentes/Boton';
import { Campo } from '../../componentes/Campo';
import { FotoPrenda } from '../../componentes/FotoPrenda';
import { Selector } from '../../componentes/Selector';
import { TiraLook } from '../../componentes/TiraLook';
import { IconoBuscar, IconoCapsula, IconoGuardados, IconoIr, IconoUbicacion } from '../../iconos';
import { Aparecer, vibrar } from '../../movimiento';
import { crearEstilos, espacio, fuentes, presionado, radio, tamañoIcono, useTema } from '../../tema';

const ESCENARIOS = [
  { valor: 'mensual', etiqueta: 'Del mes · 15 prendas' },
  { valor: 'viaje', etiqueta: 'Viaje · 10 prendas' },
];
const DURACIONES = [3, 5, 7].map((n) => ({ valor: n, etiqueta: `${n} días` }));
const LOOKS_VISIBLES = 20;

export default function PantallaCapsula() {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const [escenario, establecerEscenario] = useState('mensual');
  const [ocasion, establecerOcasion] = useState('diario');
  const [dias, establecerDias] = useState(5);
  const [busqueda, establecerBusqueda] = useState('');
  const [lugares, establecerLugares] = useState(null);
  const [lugar, establecerLugar] = useState(null);
  const [resultado, establecerResultado] = useState(null);
  const [nombre, establecerNombre] = useState('');
  const [ocupado, establecerOcupado] = useState(null); // 'armando' | 'guardando' | 'buscando'
  const [guardadas, establecerGuardadas] = useState([]);
  const [error, establecerError] = useState(null);

  useFocusEffect(
    useCallback(() => {
      listarCapsulas()
        .then(establecerGuardadas)
        .catch(() => {});
    }, []),
  );

  const cambiar = (establecer) => (valor) => {
    establecer(valor);
    establecerResultado(null);
  };

  async function buscar() {
    if (busqueda.trim().length < 2) return;
    establecerOcupado('buscando');
    try {
      establecerLugares(await buscarLugares(busqueda.trim()));
    } catch (e) {
      establecerError(e.message);
    } finally {
      establecerOcupado(null);
    }
  }

  async function armar() {
    establecerOcupado('armando');
    establecerError(null);
    try {
      const datos = { escenario, ocasion };
      if (escenario === 'viaje') Object.assign(datos, { latitud: lugar.latitud, longitud: lugar.longitud, lugar: lugar.nombre, dias });
      const nuevo = await generarCapsula(datos);
      establecerResultado(nuevo);
      establecerNombre(escenario === 'viaje' ? `Viaje a ${lugar.nombre}` : nuevo.nombre);
      vibrar.exito();
    } catch (e) {
      establecerError(e.message);
    } finally {
      establecerOcupado(null);
    }
  }

  async function guardar() {
    establecerOcupado('guardando');
    try {
      const capsula = await guardarCapsula({
        nombre: nombre.trim() || resultado.nombre,
        escenario,
        prenda_ids: resultado.prendas.map((p) => p.id),
        detalles: resultado.detalles,
      });
      router.replace(`/capsulas/${capsula.id}`);
    } catch (e) {
      establecerError(e.message);
      establecerOcupado(null);
    }
  }

  const porId = Object.fromEntries((resultado?.prendas ?? []).map((p) => [p.id, p]));

  return (
    <ScrollView style={estilos.pantalla} contentContainerStyle={estilos.contenido} keyboardShouldPersistTaps="handled">
      <Text style={texto.detalle}>
        Elegimos de tu armario pocas prendas que juntas arman muchos looks: colores que combinan, aptas para el clima y
        con algo de color.
      </Text>
      <Selector titulo="¿Para qué?" opciones={ESCENARIOS} seleccionado={escenario} alCambiar={cambiar(establecerEscenario)} enLinea estilo={{ marginBottom: 0 }} />
      <Selector titulo="Ocasión" opciones={OCASIONES} seleccionado={ocasion} alCambiar={cambiar(establecerOcasion)} enLinea estilo={{ marginBottom: 0 }} />

      {escenario === 'viaje' && (
        <View style={{ gap: espacio.s }}>
          <Text style={texto.antetitulo}>¿A dónde vas?</Text>
          {lugar ? (
            <Pressable onPress={() => cambiar(establecerLugar)(null)} accessibilityRole="button" style={({ pressed }) => [estilos.elegido, pressed && presionado]}>
              <IconoUbicacion color={colores.primario} size={tamañoIcono.s} />
              <Text style={[texto.cuerpoFuerte, { flex: 1 }]}>{[lugar.nombre, lugar.region].filter(Boolean).join(', ')}</Text>
              <Text style={estilos.enlace}>Cambiar</Text>
            </Pressable>
          ) : (
            <>
              <Campo
                icono={IconoBuscar}
                value={busqueda}
                onChangeText={establecerBusqueda}
                onSubmitEditing={buscar}
                placeholder="Ciudad, por ejemplo Toluca"
                returnKeyType="search"
                accessibilityLabel="Ciudad de destino"
                derecha={ocupado === 'buscando' ? <ActivityIndicator color={colores.primario} /> : null}
              />
              {lugares?.length === 0 && <Text style={texto.nota}>No encontramos ese lugar.</Text>}
              {lugares?.map((opcion) => (
                <Pressable
                  key={`${opcion.latitud},${opcion.longitud}`}
                  onPress={() => {
                    cambiar(establecerLugar)(opcion);
                    establecerLugares(null);
                  }}
                  accessibilityRole="button"
                  style={({ pressed }) => [estilos.opcion, pressed && presionado]}>
                  <IconoUbicacion color={colores.textoSecundario} size={tamañoIcono.s} />
                  <Text style={[texto.cuerpo, { flex: 1 }]}>{[opcion.nombre, opcion.region, opcion.pais].filter(Boolean).join(', ')}</Text>
                </Pressable>
              ))}
            </>
          )}
          <Selector titulo="¿Cuántos días?" opciones={DURACIONES} seleccionado={dias} alCambiar={cambiar(establecerDias)} enLinea estilo={{ marginBottom: 0 }} />
        </View>
      )}

      <Boton
        texto="Armar cápsula"
        icono={IconoCapsula}
        alPresionar={armar}
        cargando={ocupado === 'armando'}
        deshabilitado={escenario === 'viaje' && !lugar}
      />
      {error && (
        <Text style={[texto.detalle, { color: colores.error }]} accessibilityRole="alert">
          {error}
        </Text>
      )}

      {resultado && (
        <Aparecer estilo={{ gap: espacio.m }}>
          <View style={estilos.resumen}>
            <Text style={estilos.cifra}>{resultado.looks}</Text>
            <View style={{ flex: 1 }}>
              <Text style={texto.cuerpoFuerte}>looks con {resultado.prendas.length} prendas</Text>
              <Text style={texto.nota}>
                {resultado.neutros} neutras y {resultado.acentos} de color
                {resultado.con_abrigo ? ' · el clima pide abrigo' : ''}
              </Text>
            </View>
          </View>
          {resultado.sugerencia && <Text style={texto.detalle}>{resultado.sugerencia}</Text>}
          {resultado.prendas.length === 0 && (
            <Text style={texto.detalle}>No hay prendas disponibles que sirvan para este clima y ocasión.</Text>
          )}

          {CATEGORIAS.map((categoria) => {
            const lista = resultado.prendas.filter((p) => p.categoria === categoria.valor);
            if (lista.length === 0) return null;
            return (
              <View key={categoria.valor} style={{ gap: espacio.s }}>
                <Text style={texto.antetitulo}>
                  {categoria.etiqueta} · {lista.length}
                </Text>
                <View style={estilos.cuadricula}>
                  {lista.map((prenda) => (
                    <FotoPrenda key={prenda.id} prenda={prenda} style={estilos.celda} />
                  ))}
                </View>
              </View>
            );
          })}

          {resultado.combinaciones.length > 0 && (
            <>
              <Text style={texto.subtitulo} accessibilityRole="header">
                Tus looks
              </Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={estilos.carrusel}>
                {resultado.combinaciones.slice(0, LOOKS_VISIBLES).map((ids, indice) => (
                  <TiraLook key={ids.join('-')} titulo={`Look ${indice + 1}`} prendas={ids.map((id) => porId[id])} ancho={210} />
                ))}
              </ScrollView>
              {resultado.looks > LOOKS_VISIBLES && (
                <Text style={texto.nota}>Y {resultado.looks - LOOKS_VISIBLES} looks más con las mismas prendas.</Text>
              )}
            </>
          )}

          {resultado.prendas.length > 0 && (
            <View style={{ gap: espacio.s }}>
              <Campo value={nombre} onChangeText={establecerNombre} maxLength={60} placeholder="Nombre de la cápsula" accessibilityLabel="Nombre de la cápsula" />
              <Boton
                texto={escenario === 'viaje' ? 'Guardar y hacer mi checklist' : 'Guardar cápsula'}
                icono={IconoGuardados}
                alPresionar={guardar}
                cargando={ocupado === 'guardando'}
              />
            </View>
          )}
        </Aparecer>
      )}

      {guardadas.length > 0 && (
        <View style={{ gap: espacio.s }}>
          <Text style={texto.subtitulo} accessibilityRole="header">
            Tus cápsulas
          </Text>
          {guardadas.map((capsula) => (
            <Pressable
              key={capsula.id}
              onPress={() => router.push(`/capsulas/${capsula.id}`)}
              accessibilityRole="button"
              style={({ pressed }) => [estilos.fila, pressed && presionado]}>
              <View style={{ flex: 1 }}>
                <Text style={texto.cuerpoFuerte}>{capsula.nombre}</Text>
                <Text style={texto.nota}>
                  {capsula.prendas.length} prendas · {capsula.looks} looks
                  {capsula.escenario === 'viaje' ? ` · ${capsula.empacadas.length} empacadas` : ''}
                </Text>
              </View>
              <IconoIr color={colores.textoSecundario} size={tamañoIcono.s} />
            </Pressable>
          ))}
        </View>
      )}
    </ScrollView>
  );
}

const useEstilos = crearEstilos(({ colores, tarjeta }) => ({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  contenido: { padding: espacio.m, gap: espacio.m, paddingBottom: espacio.xxl },
  elegido: { flexDirection: 'row', alignItems: 'center', gap: espacio.s, padding: espacio.m, borderRadius: radio.l, backgroundColor: colores.superficieSuave },
  enlace: { fontFamily: fuentes.media, fontSize: 14, color: colores.primario },
  opcion: { flexDirection: 'row', alignItems: 'center', gap: espacio.s, minHeight: 44, paddingHorizontal: espacio.s },
  resumen: { flexDirection: 'row', alignItems: 'center', gap: espacio.m, padding: espacio.m, borderRadius: radio.l, backgroundColor: colores.primarioSuave },
  cifra: { fontFamily: fuentes.negrita, fontSize: 40, lineHeight: 46, color: colores.primario },
  cuadricula: { flexDirection: 'row', flexWrap: 'wrap', gap: espacio.s },
  celda: { width: '31%', aspectRatio: 3 / 4, borderRadius: radio.m, backgroundColor: colores.superficieSuave },
  carrusel: { gap: espacio.s, paddingRight: espacio.m },
  fila: { ...tarjeta, flexDirection: 'row', alignItems: 'center', gap: espacio.s, padding: espacio.m },
}));

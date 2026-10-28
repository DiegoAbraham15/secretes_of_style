import { router, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { ActivityIndicator, FlatList, Text, View } from 'react-native';

import { listarPrendas } from '../../../api';
import { CATEGORIAS } from '../../../catalogos';
import { Selector } from '../../../componentes/Selector';
import { TarjetaPrenda } from '../../../componentes/TarjetaPrenda';
import { IconoAgregar, IconoArmario } from '../../../iconos';
import { Aparecer, Presionable } from '../../../movimiento';
import { crearEstilos, espacio, tamañoIcono, useTema } from '../../../tema';

const FILTROS = [{ valor: 'todas', etiqueta: 'Todas' }, ...CATEGORIAS];
const TAMAÑO_BOTON_AGREGAR = 60;

export default function PantallaArmario() {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const [prendas, establecerPrendas] = useState([]);
  const [filtro, establecerFiltro] = useState('todas');
  const [cargando, establecerCargando] = useState(true);
  const [recargando, establecerRecargando] = useState(false); // al deslizar hacia abajo
  const [error, establecerError] = useState(null);

  const cargar = useCallback(async () => {
    establecerError(null);
    try {
      establecerPrendas(await listarPrendas({ categoria: filtro === 'todas' ? null : filtro }));
    } catch (e) {
      establecerError(e.message);
    } finally {
      establecerCargando(false);
    }
  }, [filtro]);

  // Recarga cada vez que la pantalla vuelve a verse (p. ej. después de agregar o cambiar una prenda).
  useFocusEffect(
    useCallback(() => {
      cargar();
    }, [cargar]),
  );

  async function recargar() {
    establecerRecargando(true);
    await cargar();
    establecerRecargando(false);
  }

  const vacio = filtro === 'todas';

  return (
    <View style={estilos.pantalla}>
      <FlatList
        data={cargando || error ? [] : prendas}
        keyExtractor={(prenda) => String(prenda.id)}
        numColumns={2}
        columnWrapperStyle={estilos.columnas}
        contentContainerStyle={estilos.lista}
        onRefresh={recargar}
        refreshing={recargando}
        ListHeaderComponent={
          <Selector
            opciones={FILTROS}
            seleccionado={filtro}
            alCambiar={establecerFiltro}
            enLinea
            estilo={estilos.filtros}
          />
        }
        renderItem={({ item, index }) => (
          // Las prendas entran en cascada (solo las primeras esperan; las demás aparecen al hacer scroll).
          <Aparecer indice={index} estilo={estilos.celda}>
            <TarjetaPrenda prenda={item} alPresionar={() => router.push(`/prenda/${item.id}`)} />
          </Aparecer>
        )}
        ListEmptyComponent={
          cargando ? (
            <ActivityIndicator color={colores.primario} style={{ marginTop: espacio.xxl }} />
          ) : error ? (
            <Text style={[texto.cuerpo, estilos.mensaje, { color: colores.error }]}>{error}</Text>
          ) : (
            <View style={estilos.vacio}>
              <View style={estilos.circuloVacio}>
                <IconoArmario color={colores.primario} size={tamañoIcono.l} />
              </View>
              <Text style={[texto.subtitulo, { textAlign: 'center' }]}>
                {vacio ? 'Tu armario está vacío' : 'Nada en esta categoría'}
              </Text>
              <Text style={[texto.detalle, { textAlign: 'center' }]}>
                {vacio
                  ? 'Toca el botón + para agregar tu primera prenda.'
                  : 'Agrega una prenda de esta categoría con el botón +.'}
              </Text>
            </View>
          )
        }
        ListFooterComponent={
          prendas.length > 0 && !cargando ? (
            <Text style={[texto.nota, { paddingHorizontal: espacio.m }]}>
              Toca una prenda para marcarla en lavado, archivarla o eliminarla.
            </Text>
          ) : null
        }
      />

      <Presionable
        onPress={() => router.push('/nueva-prenda')}
        accessibilityRole="button"
        accessibilityLabel="Agregar prenda"
        escala={0.92}
        estiloExterno={estilos.posicionAgregar}
        style={estilos.agregar}>
        <IconoAgregar color={colores.sobrePrimario} size={tamañoIcono.l} weight="bold" />
      </Presionable>
    </View>
  );
}

const useEstilos = crearEstilos(({ colores }) => ({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  // Espacio abajo para que el botón + no tape la última fila.
  lista: { paddingBottom: TAMAÑO_BOTON_AGREGAR + espacio.xxl, gap: espacio.l },
  filtros: { marginTop: espacio.s, marginBottom: 0 },
  columnas: { gap: espacio.m, paddingHorizontal: espacio.m },
  celda: { flex: 1, maxWidth: '50%' },
  mensaje: { marginTop: espacio.xl, paddingHorizontal: espacio.m },
  vacio: { alignItems: 'center', gap: espacio.s, marginTop: espacio.xxl, paddingHorizontal: espacio.xl },
  circuloVacio: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: colores.primarioSuave,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: espacio.s,
  },
  posicionAgregar: { position: 'absolute', right: espacio.l, bottom: espacio.l },
  agregar: {
    width: TAMAÑO_BOTON_AGREGAR,
    height: TAMAÑO_BOTON_AGREGAR,
    borderRadius: TAMAÑO_BOTON_AGREGAR / 2,
    backgroundColor: colores.primario,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: colores.sombra,
    shadowOpacity: 0.3,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 6 },
    elevation: 6,
  },
}));

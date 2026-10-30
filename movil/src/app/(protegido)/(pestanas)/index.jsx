import { router, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { ActivityIndicator, FlatList, Pressable, Text, TextInput, View } from 'react-native';

import { listarPrendas } from '../../../api';
import { CATEGORIAS, ETIQUETA_CATEGORIA, ETIQUETA_COLOR, ETIQUETA_ESTAMPADO, nombreDePrenda } from '../../../catalogos';
import { Encabezado } from '../../../componentes/Encabezado';
import { GrupoPrendas, POR_GRUPO } from '../../../componentes/GrupoPrendas';
import { Selector } from '../../../componentes/Selector';
import { IconoAgregar, IconoArmario, IconoBuscar, IconoLimpiar } from '../../../iconos';
import { Aparecer } from '../../../movimiento';
import { crearEstilos, espacio, espacioBarra, fuentes, presionado, radio, tactil, tamañoIcono, useTema } from '../../../tema';

const FILTROS = [{ valor: 'todas', etiqueta: 'Todas' }, ...CATEGORIAS];

// Sin acentos ni mayúsculas, para que "cafe" encuentre "Café".
const normalizar = (texto) => texto.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

// Lo que se puede buscar de una prenda: su nombre, categoría, color y estampado.
const textoDe = (prenda) =>
  normalizar(
    [
      nombreDePrenda(prenda),
      ETIQUETA_CATEGORIA[prenda.categoria],
      ETIQUETA_COLOR[prenda.color_principal],
      ETIQUETA_ESTAMPADO[prenda.estampado],
    ].join(' '),
  );

export default function PantallaArmario() {
  const { colores, texto, oscuro } = useTema();
  const estilos = useEstilos();
  const [prendas, establecerPrendas] = useState([]);
  const [filtro, establecerFiltro] = useState('todas');
  const [busqueda, establecerBusqueda] = useState('');
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

  const vacio = filtro === 'todas' && !busqueda;
  const visibles = busqueda ? prendas.filter((p) => textoDe(p).includes(normalizar(busqueda.trim()))) : prendas;
  const resumido = filtro === 'todas' && !busqueda;
  const grupos = CATEGORIAS.map((categoria) => ({
    ...categoria,
    prendas: visibles.filter((p) => p.categoria === categoria.valor),
  })).filter((grupo) => grupo.prendas.length > 0);

  return (
    <View style={estilos.pantalla}>
      <Encabezado
        titulo="Mi armario"
        accion={{ icono: IconoAgregar, etiqueta: 'Agregar prenda', alPresionar: () => router.push('/nueva-prenda') }}>
        <View style={estilos.buscador}>
          <IconoBuscar color={colores.textoSecundario} size={tamañoIcono.s} />
          <TextInput
            value={busqueda}
            onChangeText={establecerBusqueda}
            placeholder="Busca: jeans, rojo, floral"
            placeholderTextColor={colores.textoSecundario}
            returnKeyType="search"
            autoCorrect={false}
            keyboardAppearance={oscuro ? 'dark' : 'light'}
            accessibilityLabel="Buscar en tu armario"
            style={estilos.textoBuscador}
          />
          {busqueda !== '' && (
            <Pressable
              onPress={() => establecerBusqueda('')}
              accessibilityRole="button"
              accessibilityLabel="Borrar búsqueda"
              hitSlop={12}
              style={({ pressed }) => pressed && presionado}>
              <IconoLimpiar color={colores.textoSecundario} size={tamañoIcono.s} />
            </Pressable>
          )}
        </View>
      </Encabezado>

      <FlatList
        data={cargando || error ? [] : grupos}
        keyExtractor={(grupo) => grupo.valor}
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
          // Los grupos entran en cascada.
          <Aparecer indice={index} estilo={estilos.grupo}>
            <GrupoPrendas
              etiqueta={item.etiqueta}
              prendas={item.prendas}
              limite={resumido ? POR_GRUPO : undefined}
              alVerTodas={() => establecerFiltro(item.valor)}
              alPresionar={(prenda) => router.push(`/prenda/${prenda.id}`)}
            />
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
                {vacio
                  ? 'Tu armario está vacío'
                  : busqueda
                    ? `Nada coincide con "${busqueda.trim()}"`
                    : 'Nada en esta categoría'}
              </Text>
              <Text style={[texto.detalle, { textAlign: 'center' }]}>
                {vacio
                  ? 'Toca el botón + de arriba para agregar tu primera prenda.'
                  : busqueda
                    ? 'Prueba con un color, un tipo de prenda o un estampado.'
                    : 'Agrega una prenda de esta categoría con el botón + de arriba.'}
              </Text>
            </View>
          )
        }
        ListFooterComponent={
          visibles.length > 0 && !cargando ? (
            <Text style={[texto.nota, { paddingHorizontal: espacio.m }]}>
              Toca una prenda para marcarla en lavado, archivarla o eliminarla.
            </Text>
          ) : null
        }
      />
    </View>
  );
}

const useEstilos = crearEstilos(({ colores }) => ({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  // Espacio abajo para que la barra de pestañas no tape el último grupo.
  lista: { paddingBottom: espacioBarra, gap: espacio.l },
  filtros: { marginTop: espacio.m, marginBottom: 0 },
  grupo: { paddingHorizontal: espacio.m },
  buscador: {
    minHeight: tactil,
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.s,
    paddingHorizontal: espacio.m,
    borderRadius: radio.pastilla,
    borderWidth: 1,
    borderColor: colores.borde,
    backgroundColor: colores.superficieSuave,
  },
  textoBuscador: { flex: 1, minWidth: 0, minHeight: tactil, fontFamily: fuentes.regular, fontSize: 15, color: colores.texto },
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
}));

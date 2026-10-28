import { Image } from 'expo-image';
import * as Location from 'expo-location';
import { useFocusEffect } from 'expo-router';
import { useCallback, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Text, useWindowDimensions, View } from 'react-native';

import { guardarAtuendo, listarPrendas, obtenerRecomendaciones, urlImagen } from '../../../api';
import {
  CATEGORIAS,
  ETIQUETA_CATEGORIA,
  ETIQUETA_COLOR,
  HEX_COLOR,
  UBICACION_RESPALDO,
  nombreDePrenda,
} from '../../../catalogos';
import { Perchero } from '../../../componentes/Perchero';
import { Selector } from '../../../componentes/Selector';
import { TarjetaClima } from '../../../componentes/TarjetaClima';
import { TarjetaPrenda } from '../../../componentes/TarjetaPrenda';
import { IconoAviso } from '../../../iconos';
import { Aparecer, Presionable, useReducirMovimiento, vibrar } from '../../../movimiento';
import { crearEstilos, espacio, fuentes, presionado, radio, tamañoIcono, useTema } from '../../../tema';

// Encabezado numerado de cada paso del flujo.
function Paso({ numero, titulo, estilo }) {
  const { colores, texto } = useTema();
  return (
    <View style={[{ paddingHorizontal: espacio.m }, estilo]}>
      <Text style={[texto.antetitulo, { color: colores.primario }]}>Paso {numero}</Text>
      <Text style={texto.titulo} accessibilityRole="header">
        {titulo}
      </Text>
    </View>
  );
}

async function obtenerUbicacion() {
  try {
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== 'granted') return { ...UBICACION_RESPALDO, aproximada: true };
    const { coords } = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
    return { latitud: coords.latitude, longitud: coords.longitude, aproximada: false };
  } catch {
    return { ...UBICACION_RESPALDO, aproximada: true };
  }
}

export default function PantallaGenerador() {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const reducirMovimiento = useReducirMovimiento(); // con "Reducir movimiento" el salto a los atuendos no se anima
  const [prendas, establecerPrendas] = useState([]);
  const [base, establecerBase] = useState(null);
  const [ubicacion, establecerUbicacion] = useState(null);
  const [resultado, establecerResultado] = useState(null);
  const [generando, establecerGenerando] = useState(false);
  const [error, establecerError] = useState(null);
  const [guardadas, establecerGuardadas] = useState([]); // índices de sugerencias ya guardadas
  const [guardando, establecerGuardando] = useState(null);
  const [filtro, establecerFiltro] = useState('todas'); // categoría que se ve en el selector de prendas
  const [eligiendo, establecerEligiendo] = useState(true); // false: el selector se pliega tras elegir
  const { width } = useWindowDimensions();
  const pantalla = useRef(null);
  const desplazar = useRef(false); // true desde que se elige una prenda hasta mostrar los atuendos

  // Cuadrícula que se adapta al ancho: 3 columnas en el teléfono, más en pantallas anchas.
  const anchoUtil = Math.min(width, 1100) - espacio.m * 2;
  const columnas = Math.max(3, Math.min(8, Math.floor(anchoUtil / 150)));
  const anchoTarjeta = (anchoUtil - espacio.m * (columnas - 1)) / columnas;

  useFocusEffect(
    useCallback(() => {
      listarPrendas({ estado: 'disponible' })
        .then(establecerPrendas)
        .catch((e) => establecerError(e.message));
    }, []),
  );

  async function generar(prendaBase) {
    vibrar.seleccion();
    establecerBase(prendaBase);
    establecerEligiendo(false);
    establecerGuardadas([]);
    establecerError(null);
    establecerGenerando(true);
    desplazar.current = true;
    try {
      // La ubicación se pide solo la primera vez y después se reutiliza.
      const donde = ubicacion ?? (await obtenerUbicacion());
      establecerUbicacion(donde);
      establecerResultado(await obtenerRecomendaciones(prendaBase.id, donde.latitud, donde.longitud));
    } catch (e) {
      establecerResultado(null);
      establecerError(e.message);
    } finally {
      establecerGenerando(false);
    }
  }

  async function guardar(indice) {
    establecerGuardando(indice);
    try {
      await guardarAtuendo(resultado.sugerencias[indice], resultado.clima);
      establecerGuardadas([...guardadas, indice]);
      vibrar.exito();
    } catch (e) {
      establecerError(e.message);
    } finally {
      establecerGuardando(null);
    }
  }

  // Cada vez que cambia el bloque de resultados (se pliega el selector, aparece "Consultando…" y luego
  // los atuendos) la pantalla baja hasta él, para que no haya que buscarlos.
  function alMedirResultados(evento) {
    if (!desplazar.current) return;
    pantalla.current?.scrollTo({
      y: Math.max(0, evento.nativeEvent.layout.y - espacio.s),
      animated: !reducirMovimiento,
    });
    if (!generando) desplazar.current = false; // ya llegaron los atuendos (o el error)
  }

  const filtros = [
    { valor: 'todas', etiqueta: `Todas (${prendas.length})` },
    ...CATEGORIAS.filter((c) => prendas.some((p) => p.categoria === c.valor)),
  ];
  // Si la categoría elegida se quedó sin prendas, se vuelve a mostrar todo.
  const filtroActivo = filtros.some((f) => f.valor === filtro) ? filtro : 'todas';
  const visibles = filtroActivo === 'todas' ? prendas : prendas.filter((p) => p.categoria === filtroActivo);

  const avisos = resultado
    ? [
        ...resultado.avisos,
        ...resultado.categorias_faltantes.map(
          (c) => `Te falta ${ETIQUETA_CATEGORIA[c].toLowerCase()} que sirva para este clima y combine con tu prenda.`,
        ),
      ]
    : [];

  return (
    <ScrollView ref={pantalla} style={estilos.pantalla} contentContainerStyle={{ paddingBottom: espacio.xxl }}>
      <Paso numero={1} titulo="Elige una prenda base" estilo={{ marginTop: espacio.s }} />

      {prendas.length === 0 ? (
        <Text style={[texto.cuerpo, estilos.margen, { color: colores.textoSecundario, marginTop: espacio.s }]}>
          Agrega prendas en la pestaña Armario para armar atuendos.
        </Text>
      ) : base && !eligiendo ? (
        /* Selector plegado: la prenda elegida y un botón para cambiarla */
        <Aparecer>
          <View style={estilos.elegida}>
            <Image
              source={{ uri: urlImagen(base.url_imagen) }}
              style={estilos.fotoElegida}
              contentFit="cover"
              cachePolicy="memory-disk"
            />
            <View style={{ flex: 1 }}>
              <Text style={[texto.antetitulo, { color: colores.primario }]}>Tu prenda base</Text>
              <View style={estilos.filaNombre}>
                <View style={[estilos.muestra, { backgroundColor: HEX_COLOR[base.color_principal] }]} />
                <Text style={estilos.nombreElegida} numberOfLines={1}>
                  {nombreDePrenda(base)} {ETIQUETA_COLOR[base.color_principal].toLowerCase()}
                </Text>
              </View>
              <Text style={texto.nota}>
                Abrigo {base.nivel_abrigo} de 5{base.impermeable ? ' · impermeable' : ''}
              </Text>
            </View>
            <Presionable
              onPress={() => establecerEligiendo(true)}
              accessibilityRole="button"
              accessibilityLabel="Cambiar prenda base"
              style={estilos.botonCambiar}>
              <Text style={estilos.textoCambiar}>Cambiar</Text>
            </Presionable>
          </View>
        </Aparecer>
      ) : (
        <>
          <Text style={[texto.detalle, estilos.indicacion]}>
            Toca la prenda que quieres usar hoy. Armaremos atuendos que combinen con ella y con el clima.
          </Text>
          {/* Filtro por categoría: solo aparecen las categorías que tienen prendas */}
          <Selector
            opciones={filtros}
            seleccionado={filtroActivo}
            alCambiar={establecerFiltro}
            enLinea
            estilo={{ marginBottom: espacio.m }}
          />
          <View style={[estilos.cuadricula, { width: anchoUtil }]}>
            {visibles.map((prenda, indice) => (
              <Aparecer key={prenda.id} indice={indice} estilo={{ width: anchoTarjeta }}>
                <TarjetaPrenda
                  prenda={prenda}
                  soloFoto
                  seleccionada={prenda.id === base?.id}
                  alPresionar={() => generar(prenda)}
                />
              </Aparecer>
            ))}
          </View>
          {base && (
            <Pressable
              onPress={() => establecerEligiendo(false)}
              accessibilityRole="button"
              style={({ pressed }) => [estilos.enlace, pressed && presionado]}>
              <Text style={estilos.textoEnlace}>Seguir con {nombreDePrenda(base).toLowerCase()}</Text>
            </Pressable>
          )}
        </>
      )}

      <View onLayout={alMedirResultados}>
        {error && (
          <Text style={[texto.cuerpo, estilos.margen, { color: colores.error, marginTop: espacio.l }]}>{error}</Text>
        )}

        {generando && (
          <View style={estilos.cargando} accessibilityLiveRegion="polite">
            <ActivityIndicator color={colores.primario} />
            <Text style={texto.detalle}>Consultando el clima y armando atuendos</Text>
          </View>
        )}

        {resultado && !generando && (
          <>
            <Paso numero={2} titulo="El clima ahora" estilo={estilos.paso} />
            {/* El clima y luego cada atuendo entran en cascada: muestran que los atuendos salen del clima */}
            <Aparecer estilo={estilos.margen}>
              <TarjetaClima clima={resultado.clima} ubicacionAproximada={ubicacion?.aproximada} />

              {avisos.map((aviso) => (
                <View key={aviso} style={estilos.aviso}>
                  <IconoAviso color={colores.primario} size={tamañoIcono.s} />
                  <Text style={[texto.detalle, { flex: 1, color: colores.texto }]}>{aviso}</Text>
                </View>
              ))}
            </Aparecer>

            <Paso numero={3} titulo="Tus atuendos" estilo={estilos.paso} />
            <View style={estilos.margen}>
              {resultado.sugerencias.length === 0 && (
                <Text style={[texto.cuerpo, { color: colores.textoSecundario, marginBottom: espacio.l }]}>
                  No hay un atuendo completo con esta prenda. Prueba con otra o agrega prendas que combinen con ella.
                </Text>
              )}
              {resultado.sugerencias.map((sugerencia, indice) => (
                <Aparecer key={sugerencia.elementos.map((e) => e.prenda.id).join('-')} indice={indice + 1}>
                  <Perchero
                    sugerencia={sugerencia}
                    numero={indice + 1}
                    etiqueta={indice === 0 ? 'La mejor opción' : undefined}
                    destacado={indice === 0}
                    guardada={guardadas.includes(indice)}
                    guardando={guardando === indice}
                    alGuardar={() => guardar(indice)}
                  />
                </Aparecer>
              ))}
            </View>
          </>
        )}
      </View>
    </ScrollView>
  );
}

const useEstilos = crearEstilos(({ colores, texto, tarjeta }) => ({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  indicacion: { marginHorizontal: espacio.m, marginTop: espacio.xs, marginBottom: espacio.m },
  cuadricula: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    columnGap: espacio.m,
    rowGap: espacio.l,
    marginHorizontal: espacio.m,
    marginBottom: espacio.m,
  },
  enlace: { minHeight: 44, justifyContent: 'center', paddingHorizontal: espacio.m, alignSelf: 'flex-start' },
  textoEnlace: { fontFamily: fuentes.negrita, fontSize: 15, color: colores.primario },
  elegida: {
    ...tarjeta,
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.m,
    marginHorizontal: espacio.m,
    marginTop: espacio.m,
    padding: espacio.m - 4,
    borderWidth: 2,
    borderColor: colores.primario,
  },
  fotoElegida: { width: 64, height: 80, borderRadius: radio.l, backgroundColor: colores.superficieSuave },
  filaNombre: { flexDirection: 'row', alignItems: 'center', gap: 6, marginVertical: 2 },
  muestra: { width: 12, height: 12, borderRadius: 6, borderWidth: 1, borderColor: colores.bordeControl },
  nombreElegida: { ...texto.cuerpoFuerte, flex: 1 },
  botonCambiar: {
    minHeight: 44,
    justifyContent: 'center',
    paddingHorizontal: espacio.m,
    borderRadius: radio.pastilla,
    backgroundColor: colores.primarioSuave,
  },
  textoCambiar: { fontFamily: fuentes.negrita, fontSize: 14, color: colores.primario },
  margen: { paddingHorizontal: espacio.m },
  paso: { marginTop: espacio.xl, marginBottom: espacio.m },
  cargando: { alignItems: 'center', gap: espacio.s, paddingVertical: espacio.xxl },
  aviso: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: espacio.s,
    backgroundColor: colores.primarioSuave,
    borderRadius: radio.l,
    padding: espacio.m,
    marginTop: espacio.s,
  },
}));

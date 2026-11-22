import * as Location from 'expo-location';
import { router, useFocusEffect } from 'expo-router';
import { useCallback, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Text, View } from 'react-native';

import {
  explicarAtuendo,
  fechaDeHoy,
  guardarAtuendo,
  listarPrendas,
  listarUsos,
  obtenerLookDelDia,
  obtenerRecomendaciones,
  quitarUso,
  registrarUso,
  votarAtuendo,
} from '../../../api';
import {
  CATEGORIAS,
  ETIQUETA_CATEGORIA,
  OCASIONES,
  UBICACION_RESPALDO,
  nombreDePrenda,
} from '../../../catalogos';
import { Boton } from '../../../componentes/Boton';
import { Encabezado } from '../../../componentes/Encabezado';
import { GrupoPrendas, POR_GRUPO } from '../../../componentes/GrupoPrendas';
import { Perchero } from '../../../componentes/Perchero';
import { Selector } from '../../../componentes/Selector';
import { TarjetaClima } from '../../../componentes/TarjetaClima';
import { IconoAviso, IconoCapsula, IconoSorprendeme, IconoViaje } from '../../../iconos';
import { Aparecer, useReducirMovimiento, vibrar } from '../../../movimiento';
import { crearEstilos, espacio, espacioBarra, fuentes, presionado, radio, tamañoIcono, useTema } from '../../../tema';

// Encabezado de cada paso: los pasos son una secuencia, así que llevan su número en un círculo.
function Paso({ numero, titulo, estilo }) {
  const estilos = useEstilos();
  return (
    <View style={[estilos.paso, estilo]}>
      <View style={estilos.circuloPaso}>
        <Text style={estilos.numeroPaso}>{numero}</Text>
      </View>
      <Text style={estilos.tituloPaso} accessibilityRole="header" accessibilityLabel={`Paso ${numero}: ${titulo}`}>
        {titulo}
      </Text>
    </View>
  );
}

// Identifica un atuendo por sus prendas, igual que el servidor.
const firmaDe = (sugerencia) =>
  sugerencia.elementos
    .map((e) => e.prenda.id)
    .sort((a, b) => a - b)
    .join('-');

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
  const [ocasion, establecerOcasion] = useState('diario');
  const [explicaciones, establecerExplicaciones] = useState({}); // índice → { texto } o { error }
  const [explicando, establecerExplicando] = useState(null);
  const [votos, establecerVotos] = useState({}); // firma → 1 o -1, lo votado en esta pantalla
  const [erroresVoto, establecerErroresVoto] = useState({}); // firma → mensaje
  const [usadoHoy, establecerUsadoHoy] = useState(null); // firma de lo que se registró hoy con "Me lo puse"
  const [usando, establecerUsando] = useState(null); // firma que se está registrando
  const pantalla = useRef(null);
  const desplazar = useRef(false); // true desde que se elige una prenda hasta mostrar los atuendos

  useFocusEffect(
    useCallback(() => {
      listarPrendas({ estado: 'disponible' })
        .then(establecerPrendas)
        .catch((e) => establecerError(e.message));
      // Lo que ya se marcó hoy (también desde Guardados), para pintar "Te lo pusiste hoy".
      listarUsos(fechaDeHoy())
        .then((usos) => {
          const deHoy = usos.find((uso) => uso.fecha === fechaDeHoy());
          establecerUsadoHoy(deHoy ? firmaDe(deHoy) : null);
        })
        .catch(() => {});
    }, []),
  );

  // Pide los atuendos (con una prenda base o el look del día) y deja la pantalla lista para mostrarlos.
  async function armar(pedir) {
    vibrar.seleccion();
    establecerGuardadas([]);
    establecerExplicaciones({});
    establecerVotos({});
    establecerErroresVoto({});
    establecerError(null);
    establecerGenerando(true);
    desplazar.current = true;
    try {
      // La ubicación se pide solo la primera vez y después se reutiliza.
      const donde = ubicacion ?? (await obtenerUbicacion());
      establecerUbicacion(donde);
      establecerResultado(await pedir(donde));
    } catch (e) {
      establecerResultado(null);
      establecerError(e.message);
    } finally {
      establecerGenerando(false);
    }
  }

  function generar(prendaBase, ocasionElegida = ocasion) {
    establecerBase(prendaBase);
    establecerEligiendo(false);
    armar((donde) => obtenerRecomendaciones(prendaBase.id, donde.latitud, donde.longitud, ocasionElegida));
  }

  // "Sorpréndeme": la app elige todo, sin prenda base. Pedirlo otra vez da otra opción, porque el look que se
  // mostró sin corazón pierde puntos.
  function sorprender(ocasionElegida = ocasion) {
    establecerBase(null);
    establecerEligiendo(true);
    armar((donde) => obtenerLookDelDia(donde.latitud, donde.longitud, ocasionElegida));
  }

  // Con atuendos en pantalla, cambiar la ocasión los vuelve a armar.
  function cambiarOcasion(nueva) {
    if (nueva === ocasion) return;
    establecerOcasion(nueva);
    if (resultado?.del_dia) sorprender(nueva);
    else if (base) generar(base, nueva);
  }

  // "Me lo puse hoy": un look por día (marcar otro lo reemplaza); tocarlo otra vez lo deshace. Si es un look
  // completo, el servidor también le pone corazón.
  async function usar(sugerencia) {
    const firma = firmaDe(sugerencia);
    establecerUsando(firma);
    establecerError(null);
    try {
      if (usadoHoy === firma) {
        await quitarUso(fechaDeHoy());
        establecerUsadoHoy(null);
      } else {
        await registrarUso(sugerencia.elementos.map((e) => e.prenda.id));
        establecerUsadoHoy(firma);
        establecerVotos((actuales) => ({ ...actuales, [firma]: 1 }));
        vibrar.exito();
      }
    } catch (e) {
      establecerError(e.message);
    } finally {
      establecerUsando(null);
    }
  }

  async function explicar(indice) {
    establecerExplicando(indice);
    try {
      const { explicacion } = await explicarAtuendo(
        resultado.sugerencias[indice],
        ubicacion.latitud,
        ubicacion.longitud,
        resultado.ocasion,
      );
      establecerExplicaciones((anteriores) => ({ ...anteriores, [indice]: { texto: explicacion } }));
    } catch (e) {
      establecerExplicaciones((anteriores) => ({ ...anteriores, [indice]: { error: e.message } }));
    } finally {
      establecerExplicando(null);
    }
  }

  // El corazón se pinta de inmediato y se revierte si falla. Los looks no se mueven: el nuevo orden se ve al generar otra vez.
  async function alternarCorazon(sugerencia) {
    const firma = firmaDe(sugerencia);
    const anterior = votos[firma] ?? sugerencia.voto ?? null;
    const meGusta = anterior !== 1;
    const nuevo = meGusta ? 1 : -1;
    vibrar.seleccion();
    establecerVotos((actuales) => ({ ...actuales, [firma]: nuevo }));
    establecerErroresVoto((actuales) => ({ ...actuales, [firma]: null }));
    try {
      await votarAtuendo(sugerencia, meGusta);
    } catch (e) {
      establecerVotos((actuales) => ({ ...actuales, [firma]: anterior }));
      establecerErroresVoto((actuales) => ({ ...actuales, [firma]: e.message }));
    }
  }

  async function guardar(indice) {
    establecerGuardando(indice);
    try {
      await guardarAtuendo(resultado.sugerencias[indice], resultado.clima);
      establecerGuardadas([...guardadas, indice]);
      // Guardar cuenta como darle corazón: el servidor ya registró el voto.
      establecerVotos((actuales) => ({ ...actuales, [firmaDe(resultado.sugerencias[indice])]: 1 }));
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
  const grupos = CATEGORIAS.filter((c) => filtroActivo === 'todas' || c.valor === filtroActivo)
    .map((categoria) => ({ ...categoria, prendas: prendas.filter((p) => p.categoria === categoria.valor) }))
    .filter((grupo) => grupo.prendas.length > 0);

  const avisos = resultado
    ? [
        ...resultado.avisos,
        ...resultado.categorias_faltantes.map(
          (c) => `Te falta ${ETIQUETA_CATEGORIA[c].toLowerCase()} que sirva para este clima y combine con tu prenda.`,
        ),
      ]
    : [];

  return (
    <View style={estilos.pantalla}>
      <Encabezado
        titulo="Atuendos de hoy"
        accion={{ icono: IconoViaje, etiqueta: 'Armar la maleta de un viaje', alPresionar: () => router.push('/viaje') }}
      />
      <ScrollView ref={pantalla} style={estilos.pantalla} contentContainerStyle={{ paddingBottom: espacioBarra }}>
        <Paso numero={1} titulo="Elige la ocasión" estilo={{ marginTop: espacio.m }} />
        <Selector opciones={OCASIONES} seleccionado={ocasion} alCambiar={cambiarOcasion} enLinea estilo={{ marginBottom: 0 }} />

        {prendas.length > 0 && (
          <View style={[estilos.margen, estilos.sorpresa]}>
            <Text style={texto.detalle}>
              ¿Sin tiempo? La app arma tu look de hoy con el clima, tus gustos y sin repetir lo que te pusiste estos
              días.
            </Text>
            <Boton
              texto={resultado?.del_dia ? 'Otra opción' : 'Sorpréndeme'}
              icono={IconoSorprendeme}
              secundario={Boolean(base)}
              alPresionar={() => sorprender()}
              cargando={generando && !base}
            />
            {/* Más formas de planear: la maleta día por día o una cápsula que arma muchos looks con pocas prendas */}
            <View style={estilos.atajos}>
              <View style={{ flex: 1 }}>
                <Boton texto="Maleta de viaje" icono={IconoViaje} secundario alPresionar={() => router.push('/viaje')} />
              </View>
              <View style={{ flex: 1 }}>
                <Boton texto="Cápsula" icono={IconoCapsula} secundario alPresionar={() => router.push('/capsula')} />
              </View>
            </View>
          </View>
        )}

        <Paso numero={2} titulo="O elige tu prenda base" estilo={estilos.separacionPaso} />
        {prendas.length === 0 ? (
          <Text style={[texto.cuerpo, estilos.margen, { color: colores.textoSecundario }]}>
            Agrega prendas en la pestaña Armario para armar atuendos.
          </Text>
        ) : base && !eligiendo ? (
          /* Selector plegado: la prenda elegida y la opción de cambiarla */
          <Aparecer estilo={estilos.margen}>
            <GrupoPrendas
              prendas={[base]}
              conEstado={false}
              accion="Cambiar"
              alPresionar={() => establecerEligiendo(true)}
            />
          </Aparecer>
        ) : (
          <>
            <Text style={[texto.detalle, estilos.indicacion]}>
              Toca la prenda que quieres usar hoy. Los atuendos se arman con ella y con el clima.
            </Text>
            {/* Filtro por categoría: solo aparecen las categorías que tienen prendas */}
            <Selector
              opciones={filtros}
              seleccionado={filtroActivo}
              alCambiar={establecerFiltro}
              enLinea
              estilo={{ marginBottom: espacio.s }}
            />
            {grupos.map((grupo, indice) => (
              <Aparecer key={grupo.valor} indice={indice} estilo={estilos.grupo}>
                <GrupoPrendas
                  etiqueta={grupo.etiqueta}
                  prendas={grupo.prendas}
                  limite={filtroActivo === 'todas' ? POR_GRUPO : undefined}
                  compacto
                  conEstado={false}
                  seleccionadaId={base?.id}
                  alVerTodas={() => establecerFiltro(grupo.valor)}
                  alPresionar={(prenda) => generar(prenda)}
                />
              </Aparecer>
            ))}
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
              <Paso numero={3} titulo="El clima ahora" estilo={estilos.separacionPaso} />
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

              <Paso
                numero={4}
                titulo={resultado.del_dia ? 'Tu look de hoy' : 'Tus atuendos'}
                estilo={estilos.separacionPaso}
              />
              <View style={estilos.margen}>
                {resultado.sugerencias.length > 0 && (
                  <Text style={[texto.detalle, { marginBottom: espacio.s + 4 }]}>
                    Dale corazón a lo que te guste y te recomendaremos looks parecidos. Guardar un look también cuenta; los
                    que dejes sin corazón cuentan como que no te gustaron. Si te pones uno, toca «Me lo puse hoy»: así no
                    te lo repetimos mañana y ves en Estadísticas qué usas.
                  </Text>
                )}
                {resultado.sugerencias.length === 0 && !resultado.del_dia && (
                  <Text style={[texto.cuerpo, { color: colores.textoSecundario, marginBottom: espacio.l }]}>
                    No hay un atuendo completo con esta prenda. Prueba con otra o agrega prendas que combinen con ella.
                  </Text>
                )}
                {resultado.sugerencias.map((sugerencia, indice) => (
                  <Aparecer key={sugerencia.elementos.map((e) => e.prenda.id).join('-')} indice={indice + 1}>
                    <Perchero
                      sugerencia={sugerencia}
                      numero={indice + 1}
                      titulo={resultado.del_dia ? 'Look de hoy' : undefined}
                      etiquetaBase={resultado.del_dia ? 'La base' : undefined}
                      etiqueta={resultado.del_dia ? 'Elegido para ti' : indice === 0 ? 'La mejor opción' : undefined}
                      destacado={indice === 0}
                      guardada={guardadas.includes(indice)}
                      guardando={guardando === indice}
                      alGuardar={() => guardar(indice)}
                      alExplicar={() => explicar(indice)}
                      explicando={explicando === indice}
                      explicacion={explicaciones[indice]}
                      conCorazon={(votos[firmaDe(sugerencia)] ?? sugerencia.voto) === 1}
                      alCorazon={() => alternarCorazon(sugerencia)}
                      errorVoto={erroresVoto[firmaDe(sugerencia)]}
                      alUsar={() => usar(sugerencia)}
                      usado={usadoHoy === firmaDe(sugerencia)}
                      usando={usando === firmaDe(sugerencia)}
                    />
                  </Aparecer>
                ))}
              </View>
            </>
          )}
        </View>
      </ScrollView>
    </View>
  );
}

const useEstilos = crearEstilos(({ colores, texto }) => ({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  indicacion: { marginHorizontal: espacio.m, marginBottom: espacio.s + 4 },
  enlace: { minHeight: 44, justifyContent: 'center', paddingHorizontal: espacio.m, alignSelf: 'flex-start' },
  textoEnlace: { fontFamily: fuentes.negrita, fontSize: 15, color: colores.primario },
  margen: { paddingHorizontal: espacio.m },
  grupo: { paddingHorizontal: espacio.m, marginBottom: espacio.s + 4 },
  paso: { flexDirection: 'row', alignItems: 'center', gap: espacio.s + 2, paddingHorizontal: espacio.m, marginBottom: espacio.s + 4 },
  circuloPaso: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: colores.texto,
    alignItems: 'center',
    justifyContent: 'center',
  },
  numeroPaso: { fontFamily: fuentes.negrita, fontSize: 14, lineHeight: 20, color: colores.fondo },
  tituloPaso: { ...texto.subtitulo, flex: 1 },
  separacionPaso: { marginTop: espacio.l },
  sorpresa: { gap: espacio.s + 4, marginTop: espacio.m },
  atajos: { flexDirection: 'row', gap: espacio.s },
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

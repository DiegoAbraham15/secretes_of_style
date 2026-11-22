import { router, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Text, View } from 'react-native';

import { obtenerEstadisticas, obtenerEvaluacionIA, obtenerGruposDelArmario } from '../../../api';
import { ETIQUETA_CATEGORIA, ETIQUETA_COLOR, HEX_COLOR, NIVELES_ABRIGO, nombreConColor } from '../../../catalogos';
import { Encabezado } from '../../../componentes/Encabezado';
import { FotoPrenda } from '../../../componentes/FotoPrenda';
import { GraficaBarras, GraficaColumnas, Indicadores, Resumen, Seccion } from '../../../componentes/Graficas';
import { Selector } from '../../../componentes/Selector';
import { GruposDeRopa, MapaArmario, NoEncajan } from '../../../componentes/GruposArmario'; // SEGMENTACIÓN Y PCA
import { IconoGuardados, IconoImpermeable, IconoMeLoPuse, IconoValeLaPena } from '../../../iconos';
import { Aparecer } from '../../../movimiento';
import { crearEstilos, espacio, espacioBarra, presionado, radio, useTema } from '../../../tema';

const TITULO = 'Estadísticas';
const COLORES_VISIBLES = 5; // los demás se abren con "Ver los N"
const SIN_USAR_VISIBLES = 8; // fotos de prendas sin usar; el resto se cuenta
// Tres vistas para no tener una sola pantalla larguísima.
const VISTAS = [
  { valor: 'uso', etiqueta: 'Uso' },
  { valor: 'armario', etiqueta: 'Armario' },
  { valor: 'ia', etiqueta: 'IA' },
];
const pesos = (n) => `$${Number(n).toLocaleString('es-MX', { maximumFractionDigits: 2 })}`;

// CNN y evaluación: cada sistema de /api/votos/evaluacion con su nombre para la persona.
const SISTEMAS = [
  ['sistema_actual', 'Lo que usa la app'],
  ['sistema_sin_cnn', 'La app sin la red neuronal'],
  ['cnn', 'Red neuronal (CNN)'],
  ['parecido', 'Parecido con tus corazones'],
  ['perceptron', 'Perceptrón'],
  ['regla_fija', 'Solo tu cuestionario'],
];

export default function PantallaEstadisticas() {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const [datos, establecerDatos] = useState(null);
  const [error, establecerError] = useState(null);
  const [repeticion, establecerRepeticion] = useState(0); // cambia para que las barras se animen de nuevo
  const [grupos, establecerGrupos] = useState(null); // SEGMENTACIÓN Y PCA: grupos, mapa y prendas que no encajan
  const [evaluacion, establecerEvaluacion] = useState(null); // CNN y evaluación: qué tan bien ordena cada sistema
  const [vista, establecerVista] = useState('uso');

  // Se actualiza cada vez que se abre la pestaña, y las barras vuelven a crecer.
  useFocusEffect(
    useCallback(() => {
      obtenerEstadisticas()
        .then((respuesta) => {
          establecerDatos(respuesta);
          establecerRepeticion((n) => n + 1);
        })
        .catch((e) => establecerError(e.message));
      // SEGMENTACIÓN Y PCA: si falla, la pestaña se ve igual que antes, sin estas secciones.
      obtenerGruposDelArmario()
        .then(establecerGrupos)
        .catch(() => establecerGrupos(null));
      // CNN y evaluación: igual, si falla no se muestra la sección.
      obtenerEvaluacionIA()
        .then(establecerEvaluacion)
        .catch(() => establecerEvaluacion(null));
    }, []),
  );

  if (error || !datos) {
    return (
      <View style={estilos.pantalla}>
        <Encabezado titulo={TITULO} />
        {error ? (
          <Text style={[texto.cuerpo, estilos.mensaje, { color: colores.error }]}>{error}</Text>
        ) : (
          <ActivityIndicator color={colores.primario} style={{ marginTop: espacio.xxl }} />
        )}
      </View>
    );
  }

  const { indicadores } = datos;
  const colorMasUsado = indicadores.color_mas_usado;

  // Cada gráfica recibe sus datos ya con las etiquetas en español.
  // Categorías y colores van de mayor a menor; el nivel de abrigo conserva su orden del 1 al 5.
  const porCategoria = Object.entries(datos.por_categoria)
    .map(([categoria, valor]) => ({ etiqueta: ETIQUETA_CATEGORIA[categoria], valor }))
    .sort((a, b) => b.valor - a.valor);
  const porColor = Object.entries(datos.por_color).map(([color, valor]) => ({
    etiqueta: ETIQUETA_COLOR[color],
    valor,
    hex: HEX_COLOR[color],
  }));
  const porNivel = NIVELES_ABRIGO.map((nivel) => ({
    corta: nivel.valor,
    etiqueta: nivel.etiqueta.replace(/^\d /, ''), // "1 Muy fresca": el número ya va bajo la columna
    valor: datos.por_nivel_abrigo[nivel.valor],
  }));

  const colorEmpatado = porColor.filter((c) => c.valor === datos.por_color[colorMasUsado]).length > 1;
  const indicadoresDelArmario = [
    colorMasUsado
      ? {
          hex: HEX_COLOR[colorMasUsado],
          titulo: ETIQUETA_COLOR[colorMasUsado],
          detalle: colorEmpatado ? 'Color que más tienes, con empate' : 'Color que más tienes',
          valor: datos.por_color[colorMasUsado],
        }
      : { icono: IconoGuardados, titulo: 'Ninguno', detalle: 'Color que más tienes', valor: 0 },
    { icono: IconoImpermeable, titulo: 'Impermeables', detalle: 'Listas para la lluvia', valor: indicadores.impermeables },
    { icono: IconoGuardados, titulo: 'Atuendos guardados', detalle: 'En tu pestaña Guardados', valor: indicadores.atuendos_guardados },
  ];

  return (
    <View style={estilos.pantalla}>
      <Encabezado titulo={TITULO} />
      <ScrollView style={estilos.pantalla} contentContainerStyle={estilos.contenido}>
        <Selector opciones={VISTAS} seleccionado={vista} alCambiar={establecerVista} enLinea estilo={estilos.vistas} />

        {vista === 'uso' &&
          (indicadores.total_prendas > 0 ? (
            <>
              <UsoReal analitica={datos.analitica} />
              <LoQueUsas uso={datos.uso} repeticion={repeticion} />
            </>
          ) : (
            <Text style={[texto.cuerpo, { color: colores.textoSecundario }]}>
              Agrega tus prendas en la pestaña Armario y marca «Me lo puse hoy» para ver qué usas.
            </Text>
          ))}

        {vista === 'armario' && (
          <Aparecer>
            <Resumen total={indicadores.total_prendas} hallazgo={datos.hallazgo} />
          </Aparecer>
        )}

        {vista === 'armario' && (indicadores.total_prendas > 0 ? (
          <>
            <Aparecer indice={1}>
              <Indicadores filas={indicadoresDelArmario} />
            </Aparecer>
            <Aparecer indice={2}>
              <Seccion titulo="Por categoría" nota="Toca para ver el detalle">
                <GraficaBarras datos={porCategoria} unidad="prendas" repeticion={repeticion} />
              </Seccion>
            </Aparecer>
            <Seccion titulo="Por color" nota={`${porColor.length} ${porColor.length === 1 ? 'color' : 'colores'}`}>
              <GraficaBarras datos={porColor} unidad="prendas" repeticion={repeticion} limite={COLORES_VISIBLES} />
            </Seccion>
            <Seccion titulo="Por nivel de abrigo">
              <GraficaColumnas
                datos={porNivel}
                unidad="prendas"
                repeticion={repeticion}
                inicio="Para calor"
                fin="Para frío"
              />
            </Seccion>

            {/* SEGMENTACIÓN Y PCA: K-means, PCA y prendas atípicas */}
            {grupos?.listo ? (
              <>
                <Seccion titulo="Tus grupos de ropa" nota={`${grupos.grupos.length} grupos`}>
                  <Text style={texto.detalle}>
                    La IA (K-means) juntó tus prendas parecidas por abrigo, tono, formalidad y color, sin que le
                    dijeras cómo.
                  </Text>
                  <GruposDeRopa grupos={grupos.grupos} prendas={grupos.prendas} />
                </Seccion>
                <Seccion titulo="Mapa de tu armario" nota={`Conserva el ${Math.round(grupos.mapa.conservado * 100)} %`}>
                  <Text style={texto.detalle}>
                    Cada punto es una prenda con el número de su grupo: las parecidas quedan cerca (PCA).
                  </Text>
                  <MapaArmario mapa={grupos.mapa} grupos={grupos.grupos} prendas={grupos.prendas} />
                </Seccion>
                {grupos.no_encajan.length > 0 && (
                  <Seccion titulo="No encajan en su grupo">
                    <Text style={texto.detalle}>
                      Son las más distintas al resto de su grupo: revisa que sus datos estén bien o combínalas con
                      cuidado.
                    </Text>
                    <NoEncajan lista={grupos.no_encajan} grupos={grupos.grupos} prendas={grupos.prendas} />
                  </Seccion>
                )}
              </>
            ) : (
              grupos && (
                <Text style={[texto.nota, { color: colores.textoSecundario }]}>
                  Con {grupos.minimo} prendas o más verás tus grupos de ropa y el mapa de tu armario.
                </Text>
              )
            )}
          </>
        ) : (
          <Text style={[texto.cuerpo, { color: colores.textoSecundario }]}>
            Las gráficas aparecen cuando agregas tu primera prenda en la pestaña Armario.
          </Text>
        ))}

        {vista === 'ia' &&
          (evaluacion ? (
            <ComoAprende evaluacion={evaluacion} repeticion={repeticion} />
          ) : (
            <ActivityIndicator color={colores.primario} />
          ))}
      </ScrollView>
    </View>
  );
}

// Semáforo de rotación: activas (≤ 30 días), poco usadas (≤ 90), nuevas sin uso y candidatas a donar o vender.
const SEMAFORO = [
  ['activas', 'Activas', 'Usadas en los últimos 30 días', 'exito'],
  ['poco_usadas', 'Poco usadas', 'Su última vez fue hace 1 a 3 meses', 'acento'],
  ['candidatas', 'Candidatas a donar o vender', 'Más de 90 días sin usarse', 'error'],
  ['nuevas', 'Nuevas', 'Todavía sin estrenar en la app', 'textoSecundario'],
];

// Lo que se usa de verdad: aprovechamiento, semáforo y costo por puesta (precio ÷ veces usada).
function UsoReal({ analitica }) {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const cpu = analitica.costo_por_uso;
  const filasCosto = (lista) =>
    lista.map((f) => ({
      hex: HEX_COLOR[f.prenda.color_principal],
      titulo: nombreConColor(f.prenda),
      detalle: f.veces ? `Usada ${f.veces} ${f.veces === 1 ? 'vez' : 'veces'} · ${pesos(f.prenda.precio_compra)}` : `Sin usar · ${pesos(f.prenda.precio_compra)}`,
      valor: pesos(f.costo_por_uso),
    }));

  return (
    <>
      <Indicadores
        filas={[
          { icono: IconoMeLoPuse, titulo: `${analitica.aprovechamiento['30']} %`, detalle: 'Del armario usado en 30 días', valor: '30 d' },
          { icono: IconoMeLoPuse, titulo: `${analitica.aprovechamiento['90']} %`, detalle: 'Del armario usado en 90 días', valor: '90 d' },
          { icono: IconoValeLaPena, titulo: pesos(cpu.invertido), detalle: `Invertido en ${cpu.prendas_con_precio} prendas con precio`, valor: cpu.prendas_con_precio },
        ]}
      />

      <Seccion titulo="Rotación de tu armario">
        {SEMAFORO.map(([clave, titulo, explicacion, color]) => {
          const lista = analitica.rotacion[clave];
          if (lista.length === 0) return null;
          return (
            <View key={clave} style={{ gap: espacio.s }}>
              <View style={estilos.filaSemaforo}>
                <View style={[estilos.luz, { backgroundColor: colores[color] }]} />
                <View style={{ flex: 1 }}>
                  <Text style={texto.cuerpoFuerte}>
                    {titulo} · {lista.length}
                  </Text>
                  <Text style={texto.nota}>{explicacion}</Text>
                </View>
              </View>
              <View style={estilos.fotos}>
                {lista.slice(0, SIN_USAR_VISIBLES).map(({ prenda, dias_sin_usar: dias }) => (
                  <Pressable
                    key={prenda.id}
                    onPress={() => router.push(`/prenda/${prenda.id}`)}
                    accessibilityRole="button"
                    accessibilityLabel={`${nombreConColor(prenda)}${dias != null ? `, sin usar hace ${dias} días` : ''}. Abrir`}
                    style={({ pressed }) => pressed && presionado}>
                    <FotoPrenda prenda={prenda} style={estilos.foto} />
                  </Pressable>
                ))}
                {lista.length > SIN_USAR_VISIBLES && (
                  <View style={[estilos.foto, estilos.mas]}>
                    <Text style={texto.cuerpoFuerte}>+{lista.length - SIN_USAR_VISIBLES}</Text>
                  </View>
                )}
              </View>
            </View>
          );
        })}
        {analitica.rotacion.candidatas.length > 0 && (
          <Text style={[texto.nota, { color: colores.textoSecundario }]}>
            Antes de donarlas, prueba el reto de la semana en el Armario: te arma looks con ellas.
          </Text>
        )}
      </Seccion>

      <Seccion titulo="Costo por puesta" nota={cpu.prendas_con_precio ? 'precio ÷ veces usada' : null}>
        {cpu.prendas_con_precio === 0 ? (
          <Text style={texto.detalle}>
            Agrega el precio en «Editar datos» de tus prendas y verás cuánto te cuesta cada vez que te las pones.
          </Text>
        ) : (
          <>
            {cpu.mas_rentables.length > 0 && (
              <>
                <Text style={texto.antetitulo}>Las que mejor aprovechas</Text>
                <Indicadores filas={filasCosto(cpu.mas_rentables)} />
              </>
            )}
            <Text style={texto.antetitulo}>Las que menos has amortizado</Text>
            <Indicadores filas={filasCosto(cpu.menos_amortizadas)} />
          </>
        )}
      </Seccion>
    </>
  );
}

// "Me lo puse hoy": en los últimos 30 días, qué parte del armario usas, lo que más te pones y lo que no.
function LoQueUsas({ uso, repeticion }) {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const veces = (n) => `${n} ${n === 1 ? 'vez' : 'veces'}`;
  const masUsadas = uso.mas_usadas.map(({ prenda, veces: n }) => ({
    etiqueta: nombreConColor(prenda),
    valor: n,
    detalle: `${veces(n)} en ${uso.dias_registrados} ${uso.dias_registrados === 1 ? 'día registrado' : 'días registrados'}`,
  }));
  const faltan = uso.minimo - uso.dias_registrados;

  return (
    <Seccion titulo="Lo que usas" nota={`Últimos ${uso.dias} días`}>
      {uso.dias_registrados === 0 ? (
        <Text style={texto.detalle}>
          Toca «Me lo puse hoy» en un look (en Atuendos o en Guardados) y aquí verás qué usas y qué se queda en el clóset.
        </Text>
      ) : (
        <>
          <Text style={texto.detalle}>
            En {uso.dias_registrados} {uso.dias_registrados === 1 ? 'día registrado' : 'días registrados'} te pusiste el{' '}
            {uso.porcentaje_usado} % de tu armario. Lo que más usas:
          </Text>
          <GraficaBarras datos={masUsadas} unidad="veces" repeticion={repeticion} />
          {!uso.listo ? (
            <Text style={[texto.nota, { color: colores.textoSecundario }]}>
              Registra {faltan} {faltan === 1 ? 'día más' : 'días más'} para ver qué no te pones.
            </Text>
          ) : (
            uso.sin_usar.length > 0 && (
              <View style={{ gap: espacio.s }}>
                <Text style={texto.cuerpoFuerte}>Sin usar en {uso.dias} días · {uso.sin_usar.length}</Text>
                <View style={estilos.fotos}>
                  {uso.sin_usar.slice(0, SIN_USAR_VISIBLES).map((prenda) => (
                    <Pressable
                      key={prenda.id}
                      onPress={() => router.push(`/prenda/${prenda.id}`)}
                      accessibilityRole="button"
                      accessibilityLabel={`${nombreConColor(prenda)}, sin usar. Abrir`}
                      style={({ pressed }) => pressed && presionado}>
                      <FotoPrenda prenda={prenda} style={estilos.foto} />
                    </Pressable>
                  ))}
                  {uso.sin_usar.length > SIN_USAR_VISIBLES && (
                    <View style={[estilos.foto, estilos.mas]}>
                      <Text style={texto.cuerpoFuerte}>+{uso.sin_usar.length - SIN_USAR_VISIBLES}</Text>
                    </View>
                  )}
                </View>
                <Text style={[texto.nota, { color: colores.textoSecundario }]}>
                  Pruébalas como prenda base en Atuendos, o piensa si todavía las quieres.
                </Text>
              </View>
            )
          )}
        </>
      )}
    </Seccion>
  );
}

// CNN y evaluación: con tus votos reales, de cada 100 pares (un look con corazón y uno sin), cuántos pone bien
// cada sistema (el "orden" promedio de 20 divisiones). 50 es lo que saldría al azar.
function ComoAprende({ evaluacion, repeticion }) {
  const { colores, texto } = useTema();
  const promedio = evaluacion.promedio_20_divisiones;
  const cnn = evaluacion.cnn_entrenada;
  const bosque = cnn?.comparacion.find((fila) => fila.modelo === 'Random Forest');
  const barras =
    evaluacion.listo &&
    SISTEMAS.filter(([clave]) => promedio[clave])
      .map(([clave, etiqueta]) => {
        const valor = Math.round(promedio[clave].orden * 100);
        return { etiqueta, valor, detalle: `Pone bien ${valor} de cada 100 pares; al azar serían 50` };
      })
      .sort((a, b) => b.valor - a.valor);

  return (
    <Seccion titulo="Cómo aprende tus gustos" nota={evaluacion.listo ? `${evaluacion.datos.votos_validos} votos` : null}>
      {barras ? (
        <>
          <Text style={texto.detalle}>
            Con tus votos: de cada 100 pares (un look con corazón y uno sin), cuántos pone bien cada sistema. Al
            azar serían 50.
          </Text>
          <GraficaBarras datos={barras} unidad="pares" repeticion={repeticion} />
          <Text style={[texto.nota, { color: colores.textoSecundario }]}>{evaluacion.conclusion}</Text>
        </>
      ) : (
        <Text style={texto.detalle}>{evaluacion.mensaje}</Text>
      )}
      {cnn && (
        <Text style={[texto.nota, { color: colores.textoSecundario }]}>
          La red neuronal se entrenó con {cnn.looks_simulados.toLocaleString('es-MX')} looks simulados: con personas que
          nunca vio ordena bien {Math.round(cnn.auc * 100)} de cada 100 pares
          {bosque ? ` (un Random Forest, ${Math.round(bosque.auc * 100)})` : ''}.
        </Text>
      )}
    </Seccion>
  );
}

const useEstilos = crearEstilos(({ colores }) => ({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  contenido: { padding: espacio.m, paddingTop: espacio.s, paddingBottom: espacioBarra, gap: espacio.l },
  mensaje: { margin: espacio.l },
  vistas: { marginBottom: 0, marginHorizontal: -espacio.m },
  filaSemaforo: { flexDirection: 'row', alignItems: 'center', gap: espacio.s + 4 },
  luz: { width: 14, height: 14, borderRadius: 7 },
  fotos: { flexDirection: 'row', flexWrap: 'wrap', gap: espacio.s },
  foto: { width: 56, height: 56, borderRadius: radio.m, backgroundColor: colores.superficieSuave },
  mas: { alignItems: 'center', justifyContent: 'center' },
}));

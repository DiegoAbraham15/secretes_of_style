// Tu colorimetría: la estación de color (Primavera, Verano, Otoño o Invierno) y la paleta que te favorece.
// Dos caminos que se combinan: 5 preguntas visuales y una selfie con luz natural (el motor mide el color de tu piel
// y tu cabello; la foto no se guarda). Con el resultado, los looks muestran "Va con tus colores" y, si se activa
// "Priorizar", suben los que llevan tu paleta cerca del rostro. "¿Vale la pena?" también lo toma en cuenta.
import { useEffect, useState } from 'react';
import { ActivityIndicator, ScrollView, Switch, Text, View } from 'react-native';

import {
  analizarSelfie,
  borrarColorimetria,
  contestarColorimetria,
  obtenerColorimetria,
  obtenerPreguntasColor,
  priorizarColorimetria,
} from '../../api';
import { ETIQUETA_COLOR, HEX_COLOR } from '../../catalogos';
import { Boton } from '../../componentes/Boton';
import { Selector } from '../../componentes/Selector';
import { confirmar } from '../../confirmar';
import { elegirFoto } from '../../fotos';
import { IconoCamara, IconoEliminar, IconoPaleta, IconoPersona, IconoPrivado } from '../../iconos';
import { Aparecer, vibrar } from '../../movimiento';
import { crearEstilos, espacio, fuentes, radio, tactil, tamañoIcono, useTema } from '../../tema';

const SUBTONO = { calido: 'cálido', frio: 'frío', neutro: 'neutro' };

function Circulos({ colores: lista, tamaño = 28 }) {
  const estilos = useEstilos();
  return (
    <View style={estilos.circulos}>
      {lista.map((hex) => (
        <View key={hex} style={[estilos.circulo, { width: tamaño, height: tamaño, borderRadius: tamaño / 2, backgroundColor: hex }]} />
      ))}
    </View>
  );
}

export default function PantallaColorimetria() {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const [perfil, establecerPerfil] = useState(undefined); // undefined: cargando; null: sin diagnóstico
  const [preguntas, establecerPreguntas] = useState([]);
  const [respuestas, establecerRespuestas] = useState({});
  const [contestando, establecerContestando] = useState(false);
  const [ocupado, establecerOcupado] = useState(null); // 'cuestionario' | 'selfie' | 'probador'
  const [error, establecerError] = useState(null);

  useEffect(() => {
    Promise.all([obtenerColorimetria(), obtenerPreguntasColor()])
      .then(([actual, lista]) => {
        establecerPerfil(actual);
        establecerPreguntas(lista);
        establecerContestando(!actual);
        if (actual?.respuestas) establecerRespuestas(actual.respuestas);
      })
      .catch((e) => establecerError(e.message));
  }, []);

  async function hacer(tipo, accion) {
    establecerOcupado(tipo);
    establecerError(null);
    try {
      establecerPerfil(await accion());
      establecerContestando(false);
      vibrar.exito();
    } catch (e) {
      vibrar.aviso();
      establecerError(e.message);
    } finally {
      establecerOcupado(null);
    }
  }

  async function selfie() {
    let uri;
    try {
      uri = await elegirFoto(true, false);
    } catch (e) {
      establecerError(e.message);
      return;
    }
    if (uri) hacer('selfie', () => analizarSelfie(uri));
  }

  const completas = preguntas.length > 0 && preguntas.every((p) => respuestas[p.clave]);

  if (perfil === undefined && !error) {
    return <ActivityIndicator color={colores.primario} style={{ marginTop: espacio.xxl }} />;
  }

  return (
    <ScrollView style={estilos.pantalla} contentContainerStyle={estilos.contenido}>
      {perfil && !contestando && (
        <Aparecer estilo={estilos.resultado}>
          <Text style={texto.nota}>Tu estación de color</Text>
          <Text style={estilos.estacion} accessibilityRole="header">
            {perfil.nombre}
          </Text>
          <Text style={[texto.detalle, { color: colores.texto }]}>
            {perfil.descripcion} Subtono {SUBTONO[perfil.subtono]}, contraste {perfil.contraste}.
          </Text>
          <Circulos colores={perfil.paleta_hex} />
          <Text style={texto.antetitulo}>De tu armario, te favorecen</Text>
          <View style={estilos.chips}>
            {perfil.paleta.map((c) => (
              <View key={c} style={estilos.chip}>
                <View style={[estilos.punto, { backgroundColor: HEX_COLOR[c] }]} />
                <Text style={texto.etiqueta}>{ETIQUETA_COLOR[c]}</Text>
              </View>
            ))}
          </View>
          <Text style={texto.antetitulo}>Mejor lejos del rostro</Text>
          <View style={estilos.chips}>
            {perfil.evitar.map((c) => (
              <View key={c} style={[estilos.chip, estilos.chipEvitar]}>
                <View style={[estilos.punto, { backgroundColor: HEX_COLOR[c] }]} />
                <Text style={[texto.etiqueta, { color: colores.textoSecundario }]}>{ETIQUETA_COLOR[c]}</Text>
              </View>
            ))}
          </View>
          {perfil.medidas && (
            <View style={estilos.medidas}>
              <Text style={texto.nota}>Medido en tu selfie: piel</Text>
              <View style={[estilos.punto, { backgroundColor: perfil.piel_hex ?? colores.borde }]} />
              <Text style={texto.nota}>· {perfil.metodo === 'ambos' ? 'combinado con tus respuestas' : 'solo selfie'}</Text>
            </View>
          )}
          <View style={estilos.interruptor}>
            <View style={{ flex: 1 }}>
              <Text style={texto.cuerpoFuerte}>Priorizar mis colores</Text>
              <Text style={texto.detalle}>Los looks con tu paleta cerca del rostro salen primero</Text>
            </View>
            <Switch
              value={perfil.priorizar}
              onValueChange={(valor) => hacer('priorizar', () => priorizarColorimetria(valor))}
              accessibilityLabel="Priorizar mis colores en los looks"
              trackColor={{ true: colores.primario, false: colores.bordeControl }}
            />
          </View>
        </Aparecer>
      )}

      {contestando ? (
        <View style={{ gap: espacio.s }}>
          <Text style={texto.subtitulo} accessibilityRole="header">
            5 preguntas rápidas
          </Text>
          <Text style={[texto.detalle, { marginBottom: espacio.s }]}>Contesta frente a un espejo, con luz natural.</Text>
          {preguntas.map((pregunta) => (
            <Selector
              key={pregunta.clave}
              titulo={pregunta.pregunta}
              opciones={pregunta.opciones}
              seleccionado={respuestas[pregunta.clave]}
              alCambiar={(valor) => establecerRespuestas((r) => ({ ...r, [pregunta.clave]: valor }))}
            />
          ))}
          <Boton
            texto={completas ? 'Ver mi estación' : `Contesta las ${preguntas.length} preguntas`}
            icono={IconoPaleta}
            alPresionar={() => hacer('cuestionario', () => contestarColorimetria(respuestas))}
            cargando={ocupado === 'cuestionario'}
            deshabilitado={!completas}
          />
          {perfil && <Boton texto="Cancelar" secundario alPresionar={() => establecerContestando(false)} />}
        </View>
      ) : (
        <Boton texto="Repetir el cuestionario" icono={IconoPaleta} secundario alPresionar={() => establecerContestando(true)} />
      )}

      <View style={estilos.selfie}>
        <Text style={texto.cuerpoFuerte}>Más precisión con una selfie</Text>
        <Text style={texto.detalle}>
          De frente, con luz natural y sin filtros ni maquillaje fuerte. Medimos el color de tu piel y tu cabello y lo
          combinamos con tus respuestas.
        </Text>
        <View style={estilos.privado}>
          <IconoPrivado color={colores.primario} size={tamañoIcono.s} />
          <Text style={[texto.nota, { flex: 1 }]}>La foto no se guarda: solo los colores medidos.</Text>
        </View>
        {ocupado === 'selfie' || ocupado === 'probador' ? (
          <View style={estilos.cargando} accessibilityLiveRegion="polite">
            <ActivityIndicator color={colores.primario} />
            <Text style={texto.detalle}>Midiendo el color de tu piel…</Text>
          </View>
        ) : (
          <View style={{ gap: espacio.s }}>
            <Boton texto="Tomar una selfie" icono={IconoCamara} secundario alPresionar={selfie} />
            <Boton texto="Usar mi foto del probador" icono={IconoPersona} secundario alPresionar={() => hacer('probador', () => analizarSelfie(null))} />
          </View>
        )}
      </View>

      {error && (
        <Text style={[texto.detalle, { color: colores.error }]} accessibilityRole="alert">
          {error}
        </Text>
      )}

      {perfil && (
        <Boton
          texto="Borrar mi diagnóstico"
          icono={IconoEliminar}
          peligro
          alPresionar={() =>
            confirmar('Borrar tu colorimetría', 'Los looks dejarán de marcar tus colores.', 'Borrar', async () => {
              await borrarColorimetria();
              establecerPerfil(null);
              establecerRespuestas({});
              establecerContestando(true);
            })
          }
        />
      )}
    </ScrollView>
  );
}

const useEstilos = crearEstilos(({ colores, tarjeta }) => ({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  contenido: { padding: espacio.m, gap: espacio.l, paddingBottom: espacio.xxl },
  resultado: { ...tarjeta, padding: espacio.m, gap: espacio.s + 4 },
  estacion: { fontFamily: fuentes.displayItalica, fontSize: 40, lineHeight: 48, color: colores.texto },
  circulos: { flexDirection: 'row', flexWrap: 'wrap', gap: espacio.s },
  circulo: { borderWidth: 1, borderColor: colores.borde },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: espacio.s },
  chip: { flexDirection: 'row', alignItems: 'center', gap: espacio.xs + 2, paddingHorizontal: espacio.s + 4, minHeight: 32, borderRadius: radio.pastilla, backgroundColor: colores.superficieSuave },
  chipEvitar: { backgroundColor: colores.superficie, borderWidth: 1, borderColor: colores.borde },
  punto: { width: 12, height: 12, borderRadius: 6, borderWidth: 1, borderColor: colores.bordeControl },
  medidas: { flexDirection: 'row', alignItems: 'center', gap: espacio.xs + 2 },
  interruptor: { flexDirection: 'row', alignItems: 'center', gap: espacio.s, minHeight: tactil },
  selfie: { gap: espacio.s, padding: espacio.m, borderRadius: radio.l, backgroundColor: colores.superficieSuave },
  privado: { flexDirection: 'row', alignItems: 'center', gap: espacio.s },
  cargando: { flexDirection: 'row', alignItems: 'center', gap: espacio.s, minHeight: tactil },
}));

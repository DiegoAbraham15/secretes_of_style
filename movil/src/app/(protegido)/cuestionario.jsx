import { useState } from 'react';
import { Pressable, ScrollView, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { guardarPreferencias } from '../../api';
import { PREGUNTAS_ESTILO } from '../../catalogos';
import { Boton } from '../../componentes/Boton';
import { Selector } from '../../componentes/Selector';
import { vibrar } from '../../movimiento';
import { useSesion } from '../../sesion';
import { crearEstilos, espacio, fuentes, presionado, tactil, useTema } from '../../tema';

// Cuatro preguntas que se hacen una sola vez, para que los primeros atuendos ya vayan con la persona.
// Lo que no conteste queda como "sin preferencia" en el servidor.
export default function PantallaCuestionario() {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const { top, bottom } = useSafeAreaInsets();
  const { marcarCuestionarioListo } = useSesion();
  const [respuestas, establecerRespuestas] = useState({});
  const [enviando, establecerEnviando] = useState(false);
  const [error, establecerError] = useState(null);

  async function terminar(datos) {
    establecerEnviando(true);
    establecerError(null);
    try {
      await guardarPreferencias(datos);
      vibrar.exito();
      marcarCuestionarioListo(); // las rutas protegidas llevan solas al armario
    } catch (e) {
      establecerError(e.message);
      establecerEnviando(false);
    }
  }

  return (
    <ScrollView
      style={estilos.pantalla}
      contentContainerStyle={[estilos.contenido, { paddingTop: top + espacio.l, paddingBottom: bottom + espacio.l }]}>
      <View style={{ gap: espacio.xs }}>
        <Text style={texto.titulo} accessibilityRole="header">
          Cuéntanos tu estilo
        </Text>
        <Text style={texto.detalle}>Con esto tus primeros atuendos ya irán contigo. Después aprenderemos de tus corazones.</Text>
      </View>

      {PREGUNTAS_ESTILO.map((pregunta) => (
        <View key={pregunta.clave} style={{ gap: espacio.s + 4 }}>
          <Text style={texto.subtitulo} accessibilityRole="header">
            {pregunta.titulo}
          </Text>
          <Selector
            etiquetaGrupo={pregunta.titulo}
            opciones={pregunta.opciones}
            seleccionado={respuestas[pregunta.clave]}
            alCambiar={(valor) => establecerRespuestas({ ...respuestas, [pregunta.clave]: valor })}
            estilo={{ marginBottom: 0 }}
          />
        </View>
      ))}

      <View style={{ gap: espacio.xs }}>
        {error && (
          <Text style={[texto.detalle, { color: colores.error, marginBottom: espacio.s }]} accessibilityRole="alert">
            {error}
          </Text>
        )}
        <Boton texto="Empezar" alPresionar={() => terminar(respuestas)} cargando={enviando} />
        <Pressable
          onPress={() => terminar({})}
          disabled={enviando}
          accessibilityRole="button"
          style={({ pressed }) => [estilos.omitir, pressed && presionado]}>
          <Text style={estilos.textoOmitir}>Omitir por ahora</Text>
        </Pressable>
      </View>
    </ScrollView>
  );
}

const useEstilos = crearEstilos(({ colores }) => ({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  contenido: { paddingHorizontal: espacio.m, gap: espacio.l },
  omitir: { minHeight: tactil, alignItems: 'center', justifyContent: 'center' },
  textoOmitir: { fontFamily: fuentes.media, fontSize: 15, color: colores.primario },
}));

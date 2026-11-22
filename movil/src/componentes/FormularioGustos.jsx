// Las cuatro preguntas de estilo (colores, ropa, estampados y accesorios). Las usan el cuestionario del
// principio y "Tus gustos", donde se pueden cambiar después.
// respuestas: { clave: valor }; alCambiar(respuestasNuevas).
import { Text, View } from 'react-native';

import { PREGUNTAS_ESTILO } from '../catalogos';
import { espacio, useTema } from '../tema';
import { Selector } from './Selector';

export function FormularioGustos({ respuestas, alCambiar }) {
  const { texto } = useTema();
  return PREGUNTAS_ESTILO.map((pregunta) => (
    <View key={pregunta.clave} style={{ gap: espacio.s + 4 }}>
      <Text style={texto.subtitulo} accessibilityRole="header">
        {pregunta.titulo}
      </Text>
      <Selector
        etiquetaGrupo={pregunta.titulo}
        opciones={pregunta.opciones}
        seleccionado={respuestas[pregunta.clave]}
        alCambiar={(valor) => alCambiar({ ...respuestas, [pregunta.clave]: valor })}
        estilo={{ marginBottom: 0 }}
      />
    </View>
  ));
}

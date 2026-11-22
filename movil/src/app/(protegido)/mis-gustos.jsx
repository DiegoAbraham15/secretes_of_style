// Tus gustos: las mismas preguntas del cuestionario del principio, con lo que contestaste, para cambiarlo.
// Al guardar, el servidor recalcula los pesos del perceptrón sin borrar tus corazones; la red neuronal (CNN)
// también recibe estas respuestas, así que cambian sobre todo tus looks cuando todavía no hay corazones.
import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, ScrollView, Text, View } from 'react-native';

import { guardarPreferencias, obtenerPreferencias } from '../../api';
import { Boton } from '../../componentes/Boton';
import { FormularioGustos } from '../../componentes/FormularioGustos';
import { vibrar } from '../../movimiento';
import { crearEstilos, espacio, useTema } from '../../tema';

const PREGUNTAS = ['paleta', 'ropa', 'estampados', 'accesorios'];

export default function PantallaMisGustos() {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const [respuestas, establecerRespuestas] = useState(null);
  const [guardando, establecerGuardando] = useState(false);
  const [error, establecerError] = useState(null);

  useEffect(() => {
    obtenerPreferencias()
      .then((preferencias) =>
        establecerRespuestas(Object.fromEntries(PREGUNTAS.map((clave) => [clave, preferencias[clave]]))),
      )
      .catch((e) => (e.estado === 404 ? establecerRespuestas({}) : establecerError(e.message)));
  }, []);

  async function guardar() {
    establecerGuardando(true);
    establecerError(null);
    try {
      await guardarPreferencias(respuestas);
      vibrar.exito();
      router.back();
    } catch (e) {
      establecerError(e.message);
      establecerGuardando(false);
    }
  }

  if (!respuestas) {
    return (
      <View style={estilos.pantalla}>
        {error ? (
          <Text style={[texto.cuerpo, { margin: espacio.l, color: colores.error }]}>{error}</Text>
        ) : (
          <ActivityIndicator color={colores.primario} style={{ marginTop: espacio.xxl }} />
        )}
      </View>
    );
  }

  return (
    <ScrollView style={estilos.pantalla} contentContainerStyle={estilos.contenido}>
      <Text style={texto.detalle}>
        Cambia lo que quieras. Tus corazones se conservan: con estas respuestas cambian sobre todo tus primeros looks.
      </Text>

      <FormularioGustos respuestas={respuestas} alCambiar={establecerRespuestas} />

      <View style={{ gap: espacio.xs }}>
        {error && (
          <Text style={[texto.detalle, { color: colores.error, marginBottom: espacio.s }]} accessibilityRole="alert">
            {error}
          </Text>
        )}
        <Boton texto="Guardar" alPresionar={guardar} cargando={guardando} />
      </View>
    </ScrollView>
  );
}

const useEstilos = crearEstilos(({ colores }) => ({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  contenido: { padding: espacio.m, paddingBottom: espacio.xxl, gap: espacio.l },
}));

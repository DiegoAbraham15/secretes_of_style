// El probador virtual de un look: el botón "Probármelo" y, debajo, la foto de la persona con el look puesto.
// La imagen la genera la IA del servidor (CatVTON) y tarda: la prueba se forma en una fila y aquí se consulta
// cada pocos segundos en qué va. Si la persona no ha subido su foto, la manda a "Tu foto".
// sugerencia: { elementos: [{ prenda }] }, igual en un look del generador que en uno guardado.
import { Image } from 'expo-image';
import { router } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, Text, View } from 'react-native';

import { consultarPrueba, imagenPrivada, pedirPrueba } from '../api';
import { IconoPersona, IconoProbar, IconoReintentar } from '../iconos';
import { vibrar } from '../movimiento';
import { crearEstilos, espacio, fuentes, presionado, radio, tamañoIcono, useTema } from '../tema';
import { Boton } from './Boton';

const CADA_CUANTO_MS = 2500; // cada cuánto se pregunta en qué va la prueba

// Lo que se ve mientras se genera: el lugar en la fila o la prenda que se está vistiendo.
function textoDeAvance(prueba) {
  if (!prueba) return 'Pidiendo tu prueba…';
  if (prueba.estado === 'procesando') {
    return prueba.pasos > 1
      ? `Vistiendo la prenda ${Math.min(prueba.paso + 1, prueba.pasos)} de ${prueba.pasos}…`
      : 'Vistiendo tu foto…';
  }
  if (prueba.delante > 0) {
    return `En la fila: ${prueba.delante} ${prueba.delante === 1 ? 'prueba va' : 'pruebas van'} antes que la tuya`;
  }
  return 'Preparando el probador…';
}

export function Probador({ sugerencia }) {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  // null: sin pedir. { cargando: true, prueba }: en la fila o generándose. { prueba }: lista.
  // { error, sinFoto }: no se pudo (sinFoto si falta subir la foto).
  const [estado, establecerEstado] = useState(null);
  const [oculta, establecerOculta] = useState(false);
  const montado = useRef(true);
  const temporizador = useRef(null);

  useEffect(
    () => () => {
      montado.current = false;
      clearTimeout(temporizador.current);
    },
    [],
  );

  // Revisa la prueba y, si todavía no termina, vuelve a preguntar en un momento.
  function seguir(prueba) {
    if (!montado.current) return;
    if (prueba.estado === 'lista') {
      vibrar.exito();
      establecerEstado({ prueba });
    } else if (prueba.estado === 'error') {
      vibrar.aviso();
      establecerEstado({ error: prueba.error ?? 'No se pudo generar la imagen.' });
    } else {
      establecerEstado({ cargando: true, prueba });
      temporizador.current = setTimeout(async () => {
        try {
          seguir(await consultarPrueba(prueba.id));
        } catch (e) {
          if (montado.current) establecerEstado({ error: e.message });
        }
      }, CADA_CUANTO_MS);
    }
  }

  async function probar() {
    clearTimeout(temporizador.current);
    establecerOculta(false);
    establecerEstado({ cargando: true });
    try {
      seguir(await pedirPrueba(sugerencia));
    } catch (e) {
      if (montado.current) establecerEstado({ error: e.message, sinFoto: e.estado === 409 });
    }
  }

  if (!estado || oculta) {
    return (
      <Boton
        texto={oculta ? 'Ver mi prueba' : 'Probármelo'}
        icono={IconoProbar}
        secundario
        alPresionar={oculta ? () => establecerOculta(false) : probar}
      />
    );
  }

  if (estado.cargando) {
    return (
      <View style={estilos.aviso} accessibilityLiveRegion="polite">
        <ActivityIndicator color={colores.primario} />
        <View style={{ flex: 1 }}>
          <Text style={[texto.detalle, { color: colores.texto }]}>{textoDeAvance(estado.prueba)}</Text>
          <Text style={texto.nota}>Puede tardar unos minutos. Mientras, puedes ver los demás looks.</Text>
        </View>
      </View>
    );
  }

  if (estado.error) {
    return (
      <View style={estilos.bloque}>
        <Text style={[texto.detalle, { color: estado.sinFoto ? colores.texto : colores.error }]} accessibilityRole="alert">
          {estado.sinFoto
            ? 'Para probarte los looks, primero sube una foto tuya de cuerpo completo.'
            : estado.error}
        </Text>
        {estado.sinFoto ? (
          <Boton texto="Subir mi foto" icono={IconoPersona} secundario alPresionar={() => router.push('/tu-foto')} />
        ) : (
          <Boton texto="Intentar de nuevo" icono={IconoReintentar} secundario alPresionar={probar} />
        )}
      </View>
    );
  }

  const { prueba } = estado;
  return (
    <View style={estilos.bloque}>
      <Image
        source={imagenPrivada(prueba.url)}
        style={estilos.imagen}
        contentFit="cover"
        cachePolicy="memory-disk"
        transition={300}
        accessibilityLabel="Tu foto con este look puesto"
      />
      <Text style={texto.nota}>
        Así se te vería. El calzado y los accesorios no aparecen en la prueba
        {prueba.segundos ? ` (lista en ${Math.round(prueba.segundos)} s)` : ''}.
      </Text>
      <Pressable
        onPress={() => establecerOculta(true)}
        accessibilityRole="button"
        hitSlop={8}
        style={({ pressed }) => [estilos.ocultar, pressed && presionado]}>
        <IconoProbar color={colores.primario} size={tamañoIcono.s - 4} weight="bold" />
        <Text style={estilos.textoOcultar}>Ocultar prueba</Text>
      </Pressable>
    </View>
  );
}

const useEstilos = crearEstilos(({ colores }) => ({
  bloque: { gap: espacio.s + 4 },
  aviso: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.s + 4,
    padding: espacio.m,
    borderRadius: radio.m,
    backgroundColor: colores.primarioSuave,
  },
  // La foto de la persona va completa, en el mismo 3:4 con el que se subió.
  imagen: { width: '100%', aspectRatio: 3 / 4, borderRadius: radio.m, backgroundColor: colores.superficieSuave },
  ocultar: { flexDirection: 'row', alignItems: 'center', gap: espacio.xs + 2, alignSelf: 'flex-start' },
  textoOcultar: { fontFamily: fuentes.media, fontSize: 14, color: colores.primario },
}));

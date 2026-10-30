import { Image } from 'expo-image';
import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, ScrollView, Text, View } from 'react-native';

import {
  cambiarEstadoPrenda,
  cambiarEstiloPrenda,
  detectarEstiloPrenda,
  eliminarPrenda,
  obtenerPrenda,
  urlImagen,
} from '../../../api';
import {
  ESTADOS,
  ESTAMPADOS,
  ESTILOS,
  ETIQUETA_CATEGORIA,
  ETIQUETA_COLOR,
  ETIQUETA_ESTAMPADO,
  ETIQUETA_ESTILO,
  HEX_COLOR,
  NIVELES_ABRIGO,
  nombreDePrenda,
} from '../../../catalogos';
import { Boton } from '../../../componentes/Boton';
import { Selector } from '../../../componentes/Selector';
import { confirmar } from '../../../confirmar';
import { IconoEliminar, IconoIA } from '../../../iconos';
import { Aparecer, vibrar } from '../../../movimiento';
import { crearEstilos, espacio, radio, useTema } from '../../../tema';

const EXPLICACION_ESTADO = {
  disponible: 'Aparece en tus atuendos.',
  en_lavado: 'No aparece en tus atuendos hasta que la vuelvas a marcar como disponible.',
  archivada: 'Se queda en tu armario, pero ya no aparece en tus atuendos.',
};

export default function PantallaPrenda() {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const { id } = useLocalSearchParams();
  const [prenda, establecerPrenda] = useState(null);
  const [error, establecerError] = useState(null);
  const [cambiando, establecerCambiando] = useState(false);
  const [eliminando, establecerEliminando] = useState(false);
  const [detectando, establecerDetectando] = useState(false);

  useEffect(() => {
    obtenerPrenda(id)
      .then(establecerPrenda)
      .catch((e) => establecerError(e.message));
  }, [id]);

  async function cambiarEstado(estado) {
    if (estado === prenda.estado || cambiando) return;
    establecerCambiando(true);
    establecerError(null);
    try {
      establecerPrenda(await cambiarEstadoPrenda(prenda.id, estado));
      vibrar.seleccion();
    } catch (e) {
      establecerError(e.message);
    } finally {
      establecerCambiando(false);
    }
  }

  // Estampado y estilo se guardan juntos; la búsqueda los usa para los estampados y la ocasión.
  async function cambiarEstilo(cambios) {
    if (cambiando) return;
    const nuevo = { estampado: prenda.estampado, estilo: prenda.estilo, ...cambios };
    establecerCambiando(true);
    establecerError(null);
    try {
      establecerPrenda(await cambiarEstiloPrenda(prenda.id, nuevo.estampado, nuevo.estilo));
      vibrar.seleccion();
    } catch (e) {
      establecerError(e.message);
    } finally {
      establecerCambiando(false);
    }
  }

  async function detectarConIA() {
    establecerDetectando(true);
    establecerError(null);
    try {
      establecerPrenda(await detectarEstiloPrenda(prenda.id));
      vibrar.exito();
    } catch (e) {
      establecerError(e.message);
    } finally {
      establecerDetectando(false);
    }
  }

  function eliminar() {
    const pregunta =
      `¿Eliminar "${nombreDePrenda(prenda)}" de tu armario? ` + 'También se quitará de tus atuendos guardados.';
    confirmar('Eliminar prenda', pregunta, 'Eliminar', async () => {
      establecerEliminando(true);
      establecerError(null);
      try {
        await eliminarPrenda(prenda.id);
        vibrar.aviso();
        router.back();
      } catch (e) {
        establecerError(e.message);
        establecerEliminando(false);
      }
    });
  }

  if (!prenda) {
    return error ? (
      <Text style={[texto.cuerpo, estilos.mensaje, { color: colores.error }]}>{error}</Text>
    ) : (
      <ActivityIndicator color={colores.primario} style={{ marginTop: espacio.xxl }} />
    );
  }

  const detalles = [
    ETIQUETA_CATEGORIA[prenda.categoria],
    ETIQUETA_ESTILO[prenda.estilo]?.toLowerCase(),
    prenda.estampado !== 'liso' && ETIQUETA_ESTAMPADO[prenda.estampado]?.toLowerCase(),
    `abrigo ${NIVELES_ABRIGO[prenda.nivel_abrigo - 1].etiqueta.slice(2).toLowerCase()} (${prenda.nivel_abrigo} de 5)`,
    prenda.impermeable && 'impermeable',
  ];

  return (
    <ScrollView style={estilos.pantalla} contentContainerStyle={estilos.contenido}>
      <Aparecer estilo={estilos.zonaFoto}>
        <View style={estilos.marcoFoto}>
          <Image
            source={{ uri: urlImagen(prenda.url_imagen) }}
            style={estilos.foto}
            contentFit="cover"
            transition={200}
          />
          <View style={[estilos.muestraFoto, { backgroundColor: HEX_COLOR[prenda.color_principal] }]} />
        </View>

        <Text style={estilos.nombre}>
          {nombreDePrenda(prenda)} {ETIQUETA_COLOR[prenda.color_principal].toLowerCase()}
        </Text>
        <Text style={[texto.detalle, { textAlign: 'center' }]}>{detalles.filter(Boolean).join(', ')}</Text>
      </Aparecer>

      <Selector titulo="Estado" opciones={ESTADOS} seleccionado={prenda.estado} alCambiar={cambiarEstado} />
      <Text style={[texto.detalle, { marginTop: -espacio.s, marginBottom: espacio.xl }]}>
        {cambiando ? 'Guardando…' : EXPLICACION_ESTADO[prenda.estado]}
      </Text>

      <Selector
        titulo="Estampado"
        opciones={ESTAMPADOS}
        seleccionado={prenda.estampado}
        alCambiar={(estampado) => estampado !== prenda.estampado && cambiarEstilo({ estampado })}
      />
      <Selector
        titulo="Estilo"
        opciones={ESTILOS}
        seleccionado={prenda.estilo}
        alCambiar={(estilo) => estilo !== prenda.estilo && cambiarEstilo({ estilo })}
      />
      <Boton
        texto={detectando ? 'Mirando la foto…' : 'Detectar estampado y estilo con IA'}
        icono={IconoIA}
        secundario
        alPresionar={detectarConIA}
        cargando={detectando}
      />
      <View style={{ height: espacio.xl }} />

      {error && (
        <Text style={estilos.error} accessibilityLiveRegion="polite" accessibilityRole="alert">
          {error}
        </Text>
      )}
      <Boton texto="Eliminar prenda" icono={IconoEliminar} peligro alPresionar={eliminar} cargando={eliminando} />
    </ScrollView>
  );
}

const useEstilos = crearEstilos(({ colores, texto }) => ({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  contenido: { padding: espacio.l, paddingBottom: espacio.xxl },
  mensaje: { margin: espacio.l },
  zonaFoto: { alignItems: 'center', marginBottom: espacio.xl },
  marcoFoto: {
    width: '62%',
    maxWidth: 260,
    aspectRatio: 3 / 4,
    borderRadius: radio.xl,
    backgroundColor: colores.superficieSuave,
    overflow: 'hidden',
  },
  foto: { width: '100%', height: '100%' },
  muestraFoto: {
    position: 'absolute',
    top: espacio.s + 2,
    left: espacio.s + 2,
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 2,
    borderColor: colores.superficie,
  },
  nombre: { ...texto.titulo, textAlign: 'center', marginTop: espacio.m },
  error: { ...texto.detalle, color: colores.error, marginBottom: espacio.m },
}));

// Tiendas: viste una prenda que te gustó y no la compraste (no había tu talla, el precio…). Le tomas foto, la IA
// de la computadora dice qué es y lee la marca y el estampado (la foto no sale a internet). Primero se busca esa
// misma prenda (links con lo que leyó la IA) y después parecidas. Todo queda en tu lista hasta que la quites.
import { Image } from 'expo-image';
import { useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { ActivityIndicator, ScrollView, Text, View } from 'react-native';

import {
  analizarDeseo,
  buscarDeseoPorImagen,
  buscarEnTiendas,
  cambiarDeseo,
  eliminarDeseo,
  listarDeseos,
} from '../../api';
import { Boton } from '../../componentes/Boton';
import { Encabezado } from '../../componentes/Encabezado';
import { Selector } from '../../componentes/Selector';
import { TarjetaDeseo } from '../../componentes/TarjetaDeseo';
import { confirmar } from '../../confirmar';
import { elegirFoto } from '../../fotos';
import { IconoAviso, IconoCamara, IconoGaleria, IconoIA } from '../../iconos';
import { Aparecer, vibrar } from '../../movimiento';
import { crearEstilos, espacio, espacioBarra, radio, tamañoIcono, useTema } from '../../tema';

const PARA = [
  { valor: 'mujer', etiqueta: 'Mujer' },
  { valor: 'hombre', etiqueta: 'Hombre' },
  { valor: 'sin_especificar', etiqueta: 'Cualquiera' },
];

export default function PantallaTiendas() {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const [deseos, establecerDeseos] = useState(null);
  const [para, establecerPara] = useState('sin_especificar');
  const [analizando, establecerAnalizando] = useState(null); // uri de la foto que la IA está viendo
  const [aviso, establecerAviso] = useState(null);
  const [error, establecerError] = useState(null);

  useFocusEffect(
    useCallback(() => {
      listarDeseos()
        .then(establecerDeseos)
        .catch((e) => establecerError(e.message));
    }, []),
  );

  async function buscar(desdeCamara) {
    let uri;
    try {
      uri = await elegirFoto(desdeCamara, false);
    } catch (e) {
      establecerError(e.message);
      return;
    }
    if (!uri) return;
    establecerError(null);
    establecerAviso(null);
    establecerAnalizando(uri);
    try {
      const nuevo = await buscarEnTiendas(uri, para);
      establecerDeseos((lista) => [nuevo, ...(lista ?? [])]);
      establecerAviso([nuevo.aviso, nuevo.aviso_imagen].filter(Boolean).join(' ') || null);
      vibrar.exito();
    } catch (e) {
      vibrar.aviso();
      establecerError(e.message);
    } finally {
      establecerAnalizando(null);
    }
  }

  async function corregir(deseo, busqueda) {
    const cambiado = await cambiarDeseo(deseo.id, { busqueda });
    establecerDeseos((lista) => lista.map((d) => (d.id === deseo.id ? cambiado : d)));
  }

  async function buscarPorImagen(deseo) {
    const nuevo = await buscarDeseoPorImagen(deseo.id);
    establecerDeseos((lista) => lista.map((d) => (d.id === deseo.id ? nuevo : d)));
  }

  async function reanalizar(deseo) {
    const nuevo = await analizarDeseo(deseo.id);
    establecerDeseos((lista) => lista.map((d) => (d.id === deseo.id ? nuevo : d)));
  }

  function quitar(deseo) {
    confirmar('Quitar de tu lista', `¿Quitar «${deseo.busqueda}»? También se borra su foto.`, 'Quitar', async () => {
      try {
        await eliminarDeseo(deseo.id);
        establecerDeseos((lista) => lista.filter((d) => d.id !== deseo.id));
      } catch (e) {
        establecerError(e.message);
      }
    });
  }

  return (
    <View style={estilos.pantalla}>
      <Encabezado atras titulo="Tiendas" />
      <ScrollView style={estilos.pantalla} contentContainerStyle={estilos.contenido} keyboardShouldPersistTaps="handled">
        <Text style={texto.detalle}>
          ¿Te gustó algo en una tienda y no lo compraste? Tómale foto: primero buscamos esa misma prenda en internet
          y, si no está, parecidas. Las ves aquí y solo si te gusta una entras a la tienda.
        </Text>

        <Selector titulo="¿Para quién?" opciones={PARA} seleccionado={para} alCambiar={establecerPara} enLinea estilo={{ marginBottom: 0 }} />

        <View style={estilos.botones}>
          <View style={{ flex: 1 }}>
            <Boton texto="Cámara" icono={IconoCamara} alPresionar={() => buscar(true)} deshabilitado={Boolean(analizando)} />
          </View>
          <View style={{ flex: 1 }}>
            <Boton texto="Galería" icono={IconoGaleria} secundario alPresionar={() => buscar(false)} deshabilitado={Boolean(analizando)} />
          </View>
        </View>

        {analizando && (
          <View style={estilos.analizando} accessibilityLiveRegion="polite">
            <Image source={{ uri: analizando }} style={estilos.fotoAnalizando} contentFit="cover" />
            <View style={{ flex: 1, gap: espacio.xs }}>
              <View style={estilos.filaIA}>
                <IconoIA color={colores.primario} size={tamañoIcono.s} />
                <Text style={texto.cuerpoFuerte}>Buscando la prenda…</Text>
              </View>
              <Text style={texto.nota}>La IA tarda unos segundos (la primera vez, un poco más).</Text>
            </View>
            <ActivityIndicator color={colores.primario} />
          </View>
        )}

        {aviso && (
          <View style={estilos.aviso}>
            <IconoAviso color={colores.acento} size={tamañoIcono.s} />
            <Text style={[texto.detalle, { flex: 1 }]}>{aviso}</Text>
          </View>
        )}
        {error && (
          <Text style={[texto.detalle, { color: colores.error }]} accessibilityRole="alert">
            {error}
          </Text>
        )}

        <View style={{ gap: espacio.m }}>
          <Text style={texto.subtitulo} accessibilityRole="header">
            Te gustaron{deseos?.length ? ` · ${deseos.length}` : ''}
          </Text>
          {deseos === null ? (
            !error && <ActivityIndicator color={colores.primario} />
          ) : deseos.length === 0 ? (
            <Text style={[texto.cuerpo, { color: colores.textoSecundario }]}>
              Aquí aparecerán las prendas que fotografíes, con un link por tienda. Toca el texto para corregir qué se
              busca.
            </Text>
          ) : (
            deseos.map((deseo, indice) => (
              <Aparecer key={deseo.id} indice={indice}>
                <TarjetaDeseo
                  deseo={deseo}
                  alCambiar={(busqueda) => corregir(deseo, busqueda)}
                  alEliminar={() => quitar(deseo)}
                  alAnalizar={() => reanalizar(deseo)}
                  alBuscarPorImagen={() => buscarPorImagen(deseo)}
                />
              </Aparecer>
            ))
          )}
        </View>
      </ScrollView>
    </View>
  );
}

const useEstilos = crearEstilos(({ colores }) => ({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  contenido: { padding: espacio.m, paddingTop: espacio.s, paddingBottom: espacioBarra, gap: espacio.l },
  botones: { flexDirection: 'row', gap: espacio.s },
  analizando: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.s + 4,
    padding: espacio.m,
    borderRadius: radio.l,
    backgroundColor: colores.superficieSuave,
  },
  fotoAnalizando: { width: 56, aspectRatio: 3 / 4, borderRadius: radio.s, opacity: 0.7 },
  filaIA: { flexDirection: 'row', alignItems: 'center', gap: espacio.xs + 2 },
  aviso: { flexDirection: 'row', alignItems: 'flex-start', gap: espacio.s },
}));

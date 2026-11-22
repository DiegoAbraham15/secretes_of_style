// Vista previa de una prenda que Google encontró con tu foto (Tiendas): la ves en grande dentro de la app y, solo si
// te gusta, entras a la página para comprarla.
//   tipo "exacta":   la misma prenda en una página (casi siempre una tienda): "Ver en <tienda>".
//   tipo "parecida": una imagen parecida; Google no dice de qué página es, así que no hay botón: se busca con los
//                    links de parecidas de la tarjeta.
import { Image } from 'expo-image';
import { useLocalSearchParams } from 'expo-router';
import { useState } from 'react';
import { Linking, ScrollView, Text, View } from 'react-native';

import { Boton } from '../../componentes/Boton';
import { IconoAbrirLink, IconoGaleria } from '../../iconos';
import { crearEstilos, espacio, fuentes, radio, tamañoIcono, useTema } from '../../tema';

const esLinkSeguro = (url) => typeof url === 'string' && /^https?:\/\//i.test(url);

export default function PantallaVistaPrevia() {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const { imagen, titulo, tienda, url, tipo } = useLocalSearchParams();
  const [sinImagen, establecerSinImagen] = useState(!esLinkSeguro(imagen));
  const [error, establecerError] = useState(null);
  const exacta = tipo === 'exacta';

  async function abrir() {
    if (!esLinkSeguro(url)) return;
    try {
      await Linking.openURL(url);
    } catch {
      establecerError('No se pudo abrir la página.');
    }
  }

  return (
    <ScrollView style={estilos.pantalla} contentContainerStyle={estilos.contenido}>
      {sinImagen ? (
        <View style={[estilos.imagen, estilos.sinImagen]}>
          <IconoGaleria color={colores.textoSecundario} size={tamañoIcono.l} />
          <Text style={texto.nota}>La tienda no dejó ver la foto</Text>
        </View>
      ) : (
        <Image
          source={{ uri: imagen }}
          style={estilos.imagen}
          contentFit="contain"
          transition={200}
          onError={() => establecerSinImagen(true)}
          accessibilityLabel={titulo || 'Prenda parecida'}
        />
      )}

      <View style={{ gap: espacio.xs }}>
        <Text style={[estilos.etiqueta, !exacta && estilos.etiquetaParecida]}>
          {exacta ? 'La misma prenda de tu foto' : 'Parecida a tu foto'}
        </Text>
        <Text style={estilos.titulo} accessibilityRole="header">
          {titulo || 'Prenda parecida'}
        </Text>
        {tienda ? <Text style={texto.detalle}>En {tienda}</Text> : null}
      </View>

      {esLinkSeguro(url) && (
        <Boton texto={`Ver en ${tienda || 'la tienda'}`} icono={IconoAbrirLink} alPresionar={abrir} />
      )}
      <Text style={[texto.nota, { color: colores.textoSecundario }]}>
        {esLinkSeguro(url)
          ? 'Se abre la página donde la encontramos: ahí revisas el precio, eliges tu talla y la compras.'
          : 'Es una prenda parecida: búscala en las tiendas con los links de parecidas de tu lista.'}
      </Text>
      {error && (
        <Text style={[texto.detalle, { color: colores.error }]} accessibilityRole="alert">
          {error}
        </Text>
      )}
    </ScrollView>
  );
}

const useEstilos = crearEstilos(({ colores }) => ({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  contenido: { padding: espacio.m, gap: espacio.m, paddingBottom: espacio.xxl },
  imagen: { width: '100%', aspectRatio: 3 / 4, borderRadius: radio.l, backgroundColor: colores.superficieSuave },
  sinImagen: { alignItems: 'center', justifyContent: 'center', gap: espacio.s },
  etiqueta: {
    alignSelf: 'flex-start',
    fontFamily: fuentes.media,
    fontSize: 13,
    color: colores.sobreAcento,
    backgroundColor: colores.acento,
    paddingHorizontal: espacio.s + 2,
    paddingVertical: espacio.xs,
    borderRadius: radio.pastilla,
    overflow: 'hidden',
  },
  etiquetaParecida: { color: colores.texto, backgroundColor: colores.superficieSuave },
  titulo: { fontFamily: fuentes.negrita, fontSize: 20, lineHeight: 26, color: colores.texto },
}));

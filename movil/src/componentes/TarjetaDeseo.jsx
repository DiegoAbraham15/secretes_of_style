// Una prenda que te gustó en una tienda. Primero se busca ESA MISMA prenda y, si no aparece, parecidas:
//   1. La misma prenda
//      - Por imagen (si el servidor tiene la clave de Google Cloud Vision): vistas previas de las páginas donde
//        Google encontró esa prenda. Al tocar una se abre en grande (vista-previa.jsx) y desde ahí, si te gusta,
//        entras a la tienda.
//      - Por texto: lo que leyó la IA local (marca, modelo, personaje o texto del estampado, color). Se corrige
//        tocándolo.
//   2. Parecidas, por si no la encuentras: imágenes parecidas que encontró Google y links con solo tipo y color.
// Cada link abre el buscador de la tienda (en el navegador o en su app, si la tienes).
// alCambiar(textoNuevo) guarda la corrección; alEliminar la quita de la lista; alAnalizar pide que la IA vuelva a
// mirar la foto (para las que se guardaron sin IA o antes de que leyera la marca); alBuscarPorImagen pide a Google
// que la busque (para las que se guardaron antes o cuando Google no respondió).
// Si la IA reconoció la prenda, "¿Vale la pena comprarla?" abre cuántos looks arma con tu ropa (vale-la-pena.jsx).
import { Image } from 'expo-image';
import { router } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, Linking, Pressable, ScrollView, Text, View } from 'react-native';

import { ETIQUETA_CATEGORIA, ETIQUETA_COLOR } from '../catalogos';
import {
  IconoAbrirLink,
  IconoBuscar,
  IconoEditar,
  IconoEliminar,
  IconoIA,
  IconoPalomita,
  IconoValeLaPena,
} from '../iconos';
import { crearEstilos, espacio, fuentes, presionado, radio, tactil, tamañoIcono, useTema } from '../tema';
import { Boton } from './Boton';
import { Campo } from './Campo';
import { FotoPrenda } from './FotoPrenda';

const PARA = { mujer: 'Para mujer', hombre: 'Para hombre', sin_especificar: null };

// Vistas previas en fila (se desliza de lado). Las que no cargan su foto se quitan.
// tipo: "exacta" (la misma prenda: foto, tienda y título) o "parecida" (solo la foto y la tienda, si se sabe).
function Carrusel({ resultados, tipo }) {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const [rotas, establecerRotas] = useState([]);
  const visibles = resultados.filter((r) => r.imagen && !rotas.includes(r.imagen));
  if (visibles.length === 0) return null;
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={estilos.carrusel}>
      {visibles.map((resultado) => (
        <Pressable
          key={resultado.imagen}
          onPress={() =>
            router.push({
              pathname: '/vista-previa',
              params: { imagen: resultado.imagen, titulo: resultado.titulo ?? '', tienda: resultado.tienda ?? '', url: resultado.url ?? '', tipo },
            })
          }
          accessibilityRole="button"
          accessibilityLabel={`${resultado.titulo || 'Prenda parecida'}${resultado.tienda ? `, en ${resultado.tienda}` : ''}. Ver vista previa`}
          style={({ pressed }) => [estilos.resultado, pressed && presionado]}>
          <Image
            source={{ uri: resultado.imagen }}
            style={estilos.imagenResultado}
            contentFit="cover"
            transition={150}
            onError={() => establecerRotas((anteriores) => [...anteriores, resultado.imagen])}
          />
          {resultado.tienda ? (
            <Text style={estilos.tiendaResultado} numberOfLines={1}>
              {resultado.tienda}
            </Text>
          ) : null}
          {tipo === 'exacta' && resultado.titulo ? (
            <Text style={[texto.nota, { color: colores.textoSecundario }]} numberOfLines={2}>
              {resultado.titulo}
            </Text>
          ) : null}
        </Pressable>
      ))}
    </ScrollView>
  );
}

// Un botón por tienda. suave: los de parecidas, con menos peso que los de la misma prenda.
function LinksDeTiendas({ links, suave, alAbrir }) {
  const { colores } = useTema();
  const estilos = useEstilos();
  return (
    <View style={estilos.tiendas}>
      {links.map((link) => (
        <Pressable
          key={link.tienda}
          onPress={() => alAbrir(link.url)}
          accessibilityRole="link"
          accessibilityLabel={`Buscar en ${link.tienda}`}
          style={({ pressed }) => [estilos.tienda, suave && estilos.tiendaSuave, pressed && presionado]}>
          <Text style={[estilos.textoTienda, suave && { color: colores.texto }]}>{link.tienda}</Text>
          <IconoAbrirLink color={suave ? colores.textoSecundario : colores.primario} size={14} weight="bold" />
        </Pressable>
      ))}
    </View>
  );
}

export function TarjetaDeseo({ deseo, alCambiar, alEliminar, alAnalizar, alBuscarPorImagen }) {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const [editando, establecerEditando] = useState(false);
  const [busqueda, establecerBusqueda] = useState(deseo.busqueda);
  const [guardando, establecerGuardando] = useState(false);
  const [analizando, establecerAnalizando] = useState(false);
  const [buscandoImagen, establecerBuscandoImagen] = useState(false);
  const [error, establecerError] = useState(null);

  const visto = deseo.detectado;
  const web = deseo.imagen_web; // lo que encontró Google con la foto (null si no se buscó)
  const queVio = visto
    ? [
        visto.marca,
        visto.subcategoria || ETIQUETA_CATEGORIA[visto.categoria],
        visto.detalles,
        ETIQUETA_COLOR[visto.color_principal]?.toLowerCase(),
      ]
        .filter(Boolean)
        .join(', ')
    : null;
  // Sin IA, o guardada antes de que la IA leyera la marca y los detalles: vale la pena que vuelva a mirarla.
  const puedeAnalizar = !visto || !('detalles' in visto);

  function editar() {
    establecerBusqueda(deseo.busqueda);
    establecerEditando(true);
  }

  async function guardar() {
    if (!busqueda.trim() || busqueda.trim() === deseo.busqueda) {
      establecerEditando(false);
      return;
    }
    establecerGuardando(true);
    establecerError(null);
    try {
      await alCambiar(busqueda.trim());
      establecerEditando(false);
    } catch (e) {
      establecerError(e.message);
    } finally {
      establecerGuardando(false);
    }
  }

  async function abrir(url) {
    try {
      await Linking.openURL(url);
    } catch {
      establecerError('No se pudo abrir la tienda.');
    }
  }

  async function buscarPorImagen() {
    establecerBuscandoImagen(true);
    establecerError(null);
    try {
      await alBuscarPorImagen();
    } catch (e) {
      establecerError(e.message);
    } finally {
      establecerBuscandoImagen(false);
    }
  }

  async function analizar() {
    establecerAnalizando(true);
    establecerError(null);
    try {
      await alAnalizar();
    } catch (e) {
      establecerError(e.message);
    } finally {
      establecerAnalizando(false);
    }
  }

  return (
    <View style={estilos.tarjeta}>
      <View style={estilos.fila}>
        <FotoPrenda prenda={deseo} style={estilos.foto} accessibilityLabel="Foto de la prenda que te gustó" />
        <View style={estilos.datos}>
          {editando ? (
            <Campo
              value={busqueda}
              onChangeText={establecerBusqueda}
              onSubmitEditing={guardar}
              returnKeyType="done"
              autoFocus
              maxLength={120}
              accessibilityLabel="Qué buscar en las tiendas"
              derecha={
                guardando ? (
                  <ActivityIndicator color={colores.primario} />
                ) : (
                  <Pressable onPress={guardar} accessibilityRole="button" accessibilityLabel="Guardar búsqueda" hitSlop={8}>
                    <IconoPalomita color={colores.primario} size={tamañoIcono.s} weight="bold" />
                  </Pressable>
                )
              }
            />
          ) : (
            <Pressable
              onPress={editar}
              accessibilityRole="button"
              accessibilityLabel={`Buscar «${deseo.busqueda}». Toca para corregirlo`}
              style={({ pressed }) => [estilos.busqueda, pressed && presionado]}>
              <Text style={[texto.cuerpoFuerte, { flex: 1 }]}>{deseo.busqueda}</Text>
              <IconoEditar color={colores.textoSecundario} size={tamañoIcono.s} />
            </Pressable>
          )}
          <Text style={texto.nota}>
            {[PARA[deseo.para], queVio ? `La IA vio: ${queVio}` : 'Escribe qué prenda es', deseo.fecha_creacion.slice(0, 10)]
              .filter(Boolean)
              .join(' · ')}
          </Text>
          {puedeAnalizar && alAnalizar && (
            <Pressable
              onPress={analizar}
              disabled={analizando}
              accessibilityRole="button"
              hitSlop={8}
              style={({ pressed }) => [estilos.enlace, pressed && presionado]}>
              {analizando ? (
                <ActivityIndicator color={colores.primario} size="small" />
              ) : (
                <IconoIA color={colores.primario} size={14} />
              )}
              <Text style={estilos.textoEnlace}>
                {analizando ? 'La IA está mirando la foto…' : 'Que la IA lea la marca y el estampado'}
              </Text>
            </Pressable>
          )}
        </View>
        <Pressable
          onPress={alEliminar}
          accessibilityRole="button"
          accessibilityLabel="Quitar de la lista"
          hitSlop={8}
          style={({ pressed }) => [estilos.quitar, pressed && presionado]}>
          <IconoEliminar color={colores.textoSecundario} size={tamañoIcono.s} />
        </Pressable>
      </View>

      {error && (
        <Text style={[texto.detalle, { color: colores.error }]} accessibilityRole="alert">
          {error}
        </Text>
      )}

      {/* 1. La misma prenda: primero por imagen (Google) y luego con lo que leyó la IA */}
      <View style={estilos.grupo}>
        <Text style={estilos.paso} accessibilityRole="header">
          La misma prenda
        </Text>
        {web &&
          (web.exactas.length > 0 ? (
            <>
              <Text style={texto.nota}>
                Google la encontró en {web.exactas.length} {web.exactas.length === 1 ? 'página' : 'páginas'}. Toca una
                para verla:
              </Text>
              <Carrusel resultados={web.exactas} tipo="exacta" />
            </>
          ) : (
            <Text style={texto.nota}>Google no encontró esta misma prenda en internet; abajo tienes parecidas.</Text>
          ))}
        {!web && deseo.por_imagen && alBuscarPorImagen && (
          <Boton
            texto={buscandoImagen ? 'Buscando con tu foto…' : 'Buscar esta prenda por imagen'}
            icono={IconoBuscar}
            alPresionar={buscarPorImagen}
            cargando={buscandoImagen}
          />
        )}
        <Text style={texto.nota}>Por texto, con lo que leyó la IA:</Text>
        <LinksDeTiendas links={deseo.links} alAbrir={abrir} />
      </View>

      {/* 2. Si no aparece: parecidas (las imágenes de Google y los links sin marca ni detalles) */}
      {(web?.parecidas.length > 0 || deseo.links_parecidas?.length > 0) && (
        <View style={estilos.grupo}>
          <Text style={estilos.paso} accessibilityRole="header">
            Si no la encuentras: parecidas
          </Text>
          {web?.parecidas.length > 0 && <Carrusel resultados={web.parecidas} tipo="parecida" />}
          {deseo.links_parecidas?.length > 0 && (
            <>
              <Text style={texto.nota}>Por texto: «{deseo.parecida}»</Text>
              <LinksDeTiendas links={deseo.links_parecidas} suave alAbrir={abrir} />
            </>
          )}
        </View>
      )}

      {visto?.categoria && visto?.color_principal && (
        <Boton
          texto="¿Vale la pena comprarla?"
          icono={IconoValeLaPena}
          secundario
          alPresionar={() => router.push({ pathname: '/vale-la-pena', params: { id: deseo.id } })}
        />
      )}
    </View>
  );
}

const useEstilos = crearEstilos(({ colores, tarjeta }) => ({
  tarjeta: { ...tarjeta, padding: espacio.m, gap: espacio.m },
  fila: { flexDirection: 'row', gap: espacio.s + 4, alignItems: 'flex-start' },
  foto: { width: 72, aspectRatio: 3 / 4, borderRadius: radio.s, backgroundColor: colores.superficieSuave },
  datos: { flex: 1, gap: espacio.xs },
  busqueda: { flexDirection: 'row', alignItems: 'center', gap: espacio.s, minHeight: tactil - 8 },
  quitar: { minWidth: 32, minHeight: 32, alignItems: 'center', justifyContent: 'center' },
  enlace: { flexDirection: 'row', alignItems: 'center', gap: espacio.xs + 2, minHeight: 32, alignSelf: 'flex-start' },
  textoEnlace: { fontFamily: fuentes.media, fontSize: 14, color: colores.primario },
  grupo: { gap: espacio.s, paddingTop: espacio.s + 4, borderTopWidth: 1, borderTopColor: colores.borde },
  paso: { fontFamily: fuentes.negrita, fontSize: 15, lineHeight: 20, color: colores.texto },
  tiendas: { flexDirection: 'row', flexWrap: 'wrap', gap: espacio.s },
  tienda: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.xs + 2,
    minHeight: 40,
    paddingHorizontal: espacio.m,
    borderRadius: radio.pastilla,
    borderWidth: 1.5,
    borderColor: colores.primario,
    backgroundColor: colores.superficie,
  },
  tiendaSuave: { borderColor: colores.bordeControl, borderWidth: 1 },
  carrusel: { gap: espacio.s, paddingRight: espacio.s },
  resultado: { width: 112, gap: 2 },
  imagenResultado: { width: 112, aspectRatio: 3 / 4, borderRadius: radio.m, backgroundColor: colores.superficieSuave },
  tiendaResultado: { fontFamily: fuentes.negrita, fontSize: 13, lineHeight: 18, color: colores.texto },
  textoTienda: { fontFamily: fuentes.media, fontSize: 14, color: colores.primario },
}));

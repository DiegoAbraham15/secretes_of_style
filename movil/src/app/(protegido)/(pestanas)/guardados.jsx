import { Image } from 'expo-image';
import { useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { ActivityIndicator, FlatList, Pressable, Text, View } from 'react-native';

import { eliminarAtuendo, listarAtuendos, urlImagen } from '../../../api';
import { ETIQUETA_CATEGORIA, ETIQUETA_COLOR, HEX_COLOR, nombreDePrenda, ORDEN_CUERPO } from '../../../catalogos';
import { Encabezado } from '../../../componentes/Encabezado';
import { ICONO_CLIMA } from '../../../componentes/TarjetaClima';
import { confirmar } from '../../../confirmar';
import { IconoAbrir, IconoCerrar, IconoEliminar, IconoGuardados, IconoNublado } from '../../../iconos';
import { Aparecer, vibrar } from '../../../movimiento';
import { crearEstilos, espacio, espacioBarra, fuentes, presionado, radio, tactil, tamañoIcono, useTema } from '../../../tema';

// SQLite guarda la fecha en UTC sin zona ("2026-10-27 13:05:00").
const leerFecha = (fechaUtc) => new Date(`${fechaUtc.replace(' ', 'T')}Z`);

// "Hoy", "Ayer" o "28 oct": la columna de la izquierda de la línea de tiempo.
function nombreDelDia(fecha) {
  const ayer = new Date();
  ayer.setDate(ayer.getDate() - 1);
  if (fecha.toDateString() === new Date().toDateString()) return 'Hoy';
  if (fecha.toDateString() === ayer.toDateString()) return 'Ayer';
  return fecha.toLocaleDateString('es-MX', { day: 'numeric', month: 'short' }).replace('.', '');
}

const horaDe = (fecha) => fecha.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit', hour12: false });

// "azul marino, verde y café"
const unirConY = (lista) => (lista.length < 2 ? lista.join('') : `${lista.slice(0, -1).join(', ')} y ${lista.at(-1)}`);

// Un atuendo guardado dentro de la línea de tiempo: a la izquierda el día y la hora, en medio el punto
// sobre la línea y a la derecha una tarjeta con el clima de ese día y las fotos de las prendas.
function Entrada({ atuendo, dia, primera, ultima, alEliminar, eliminando }) {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const [abierta, establecerAbierta] = useState(false);
  const fecha = leerFecha(atuendo.fecha_creacion);
  const clima = atuendo.reporte_clima;
  const Icono = ICONO_CLIMA[clima?.descripcion] ?? IconoNublado;
  const prendas = atuendo.elementos
    .map((elemento) => elemento.prenda)
    .sort((a, b) => ORDEN_CUERPO.indexOf(a.categoria) - ORDEN_CUERPO.indexOf(b.categoria));
  const colorTexto = unirConY([...new Set(prendas.map((p) => ETIQUETA_COLOR[p.color_principal].toLowerCase()))]);

  return (
    <View style={estilos.entrada}>
      <View style={estilos.columnaFecha}>
        {dia && <Text style={estilos.dia}>{dia}</Text>}
        <Text style={texto.nota}>{horaDe(fecha)}</Text>
      </View>

      {/* La línea une los puntos; el más reciente va relleno de rosa */}
      <View style={estilos.columnaLinea}>
        {!(primera && ultima) && (
          <View style={[estilos.linea, primera && { top: ALTO_PUNTO }, ultima && { bottom: undefined, height: ALTO_PUNTO }]} />
        )}
        <View style={[estilos.punto, primera && estilos.puntoReciente]} />
      </View>

      <View style={estilos.tarjeta}>
        <View style={estilos.cabeceraTarjeta}>
          <View style={estilos.cuadroIcono}>
            <Icono color={colores.primario} size={tamañoIcono.s + 2} />
          </View>
          <View style={{ flex: 1, minWidth: 0 }}>
            <Text style={estilos.tituloTarjeta} numberOfLines={1}>
              {clima ? `${clima.descripcion}, ${Math.round(clima.temperatura_c)} °C` : 'Sin datos del clima'}
            </Text>
            <Text style={texto.nota} numberOfLines={2}>
              {prendas.length} {prendas.length === 1 ? 'prenda' : 'prendas'}: {colorTexto}
            </Text>
          </View>
          <Pressable
            onPress={alEliminar}
            disabled={eliminando}
            accessibilityRole="button"
            accessibilityLabel="Eliminar este atuendo"
            style={({ pressed }) => [estilos.botonIcono, pressed && presionado]}>
            {eliminando ? (
              <ActivityIndicator color={colores.error} />
            ) : (
              <IconoEliminar color={colores.textoSecundario} size={tamañoIcono.s + 2} />
            )}
          </Pressable>
        </View>

        <View style={estilos.fotos}>
          {prendas.map((prenda) => (
            <Image
              key={prenda.id}
              source={{ uri: urlImagen(prenda.url_imagen) }}
              style={estilos.foto}
              contentFit="cover"
              cachePolicy="memory-disk"
              transition={200}
              accessibilityLabel={`${nombreDePrenda(prenda)} ${ETIQUETA_COLOR[prenda.color_principal].toLowerCase()}`}
            />
          ))}
        </View>

        {abierta && (
          <View style={estilos.detalle}>
            {prendas.map((prenda) => (
              <View key={prenda.id} style={estilos.filaDetalle}>
                <View style={[estilos.muestra, { backgroundColor: HEX_COLOR[prenda.color_principal] }]} />
                <Text style={[texto.detalle, { flex: 1, color: colores.texto }]}>
                  {nombreDePrenda(prenda)} {ETIQUETA_COLOR[prenda.color_principal].toLowerCase()}
                </Text>
                {/* La categoría solo si el nombre no la dice ya (p. ej. "Chamarra", que es un abrigo) */}
                {prenda.subcategoria && <Text style={texto.nota}>{ETIQUETA_CATEGORIA[prenda.categoria]}</Text>}
              </View>
            ))}
          </View>
        )}

        <Pressable
          onPress={() => establecerAbierta(!abierta)}
          accessibilityRole="button"
          accessibilityState={{ expanded: abierta }}
          hitSlop={8}
          style={({ pressed }) => [estilos.verMas, pressed && presionado]}>
          <Text style={estilos.textoVerMas}>{abierta ? 'Ocultar prendas' : 'Ver prendas'}</Text>
          {abierta ? (
            <IconoCerrar color={colores.primario} size={14} weight="bold" />
          ) : (
            <IconoAbrir color={colores.primario} size={14} weight="bold" />
          )}
        </Pressable>
      </View>
    </View>
  );
}

export default function PantallaGuardados() {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const [atuendos, establecerAtuendos] = useState([]);
  const [cargando, establecerCargando] = useState(true);
  const [recargando, establecerRecargando] = useState(false);
  const [eliminando, establecerEliminando] = useState(null); // id del atuendo que se está eliminando
  const [error, establecerError] = useState(null);

  const cargar = useCallback(async () => {
    establecerError(null);
    try {
      // Si se eliminaron todas sus prendas, el atuendo ya no tiene nada que mostrar.
      establecerAtuendos((await listarAtuendos()).filter((a) => a.elementos.length > 0));
    } catch (e) {
      establecerError(e.message);
    } finally {
      establecerCargando(false);
    }
  }, []);

  // Se actualiza cada vez que se abre la pestaña (p. ej. después de guardar uno en Atuendos).
  useFocusEffect(
    useCallback(() => {
      cargar();
    }, [cargar]),
  );

  async function recargar() {
    establecerRecargando(true);
    await cargar();
    establecerRecargando(false);
  }

  function eliminar(atuendo) {
    confirmar('Eliminar atuendo', '¿Eliminar este atuendo de tus guardados? Las prendas siguen en tu armario.', 'Eliminar', async () => {
      establecerEliminando(atuendo.id);
      establecerError(null);
      try {
        await eliminarAtuendo(atuendo.id);
        vibrar.aviso();
        establecerAtuendos((actuales) => actuales.filter((a) => a.id !== atuendo.id));
      } catch (e) {
        establecerError(e.message);
      } finally {
        establecerEliminando(null);
      }
    });
  }

  // El día solo se escribe en el primer atuendo de ese día.
  const dias = atuendos.map((a) => nombreDelDia(leerFecha(a.fecha_creacion)));

  return (
    <View style={estilos.pantalla}>
      <Encabezado titulo="Mis atuendos" />
      <FlatList
        style={estilos.pantalla}
        contentContainerStyle={estilos.lista}
        data={cargando ? [] : atuendos}
        keyExtractor={(atuendo) => String(atuendo.id)}
        onRefresh={recargar}
        refreshing={recargando}
        ListHeaderComponent={
          <>
            {error && <Text style={estilos.error}>{error}</Text>}
            {atuendos.length > 0 && (
              <Text style={[texto.detalle, { marginBottom: espacio.l }]}>
                {atuendos.length} {atuendos.length === 1 ? 'atuendo guardado' : 'atuendos guardados'}, del más reciente
                al más antiguo.
              </Text>
            )}
          </>
        }
        renderItem={({ item, index }) => (
          <Aparecer indice={index}>
            <Entrada
              atuendo={item}
              dia={dias[index] !== dias[index - 1] ? dias[index] : null}
              primera={index === 0}
              ultima={index === atuendos.length - 1}
              alEliminar={() => eliminar(item)}
              eliminando={eliminando === item.id}
            />
          </Aparecer>
        )}
        ListEmptyComponent={
          cargando ? (
            <ActivityIndicator color={colores.primario} style={{ marginTop: espacio.xxl }} />
          ) : (
            !error && (
              <View style={estilos.vacio}>
                <View style={estilos.circuloVacio}>
                  <IconoGuardados color={colores.primario} size={tamañoIcono.l} />
                </View>
                <Text style={[texto.subtitulo, { textAlign: 'center' }]}>Aún no guardas atuendos</Text>
                <Text style={[texto.detalle, { textAlign: 'center' }]}>
                  En la pestaña Atuendos toca “Guardar atuendo” en el que te guste.
                </Text>
              </View>
            )
          )
        }
      />
    </View>
  );
}

const ANCHO_FECHA = 52;
const ALTO_PUNTO = 22; // centro del punto, a la altura del título de la tarjeta
const TAMAÑO_FOTO = 56;

const useEstilos = crearEstilos(({ colores, texto }) => ({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  lista: { padding: espacio.m, paddingTop: espacio.s, paddingBottom: espacioBarra },

  // Sin espacio entre entradas para que la línea de tiempo no se corte; la separación va dentro.
  entrada: { flexDirection: 'row', paddingBottom: espacio.m },
  columnaFecha: { width: ANCHO_FECHA, alignItems: 'flex-end', paddingTop: espacio.s + 4 },
  dia: { fontFamily: fuentes.negrita, fontSize: 14, lineHeight: 20, color: colores.texto },
  columnaLinea: { width: 28, alignItems: 'center' },
  linea: {
    position: 'absolute',
    top: 0,
    bottom: -espacio.m,
    width: 2,
    backgroundColor: colores.borde,
  },
  punto: {
    marginTop: ALTO_PUNTO - 6,
    width: 12,
    height: 12,
    borderRadius: 6,
    borderWidth: 2,
    borderColor: colores.bordeControl,
    backgroundColor: colores.fondo,
  },
  puntoReciente: { borderColor: colores.primarioSuave, backgroundColor: colores.primario, transform: [{ scale: 1.25 }] },

  tarjeta: {
    flex: 1,
    padding: espacio.s + 4,
    borderRadius: radio.l,
    borderWidth: 1,
    borderColor: colores.borde,
    backgroundColor: colores.superficie,
    gap: espacio.s + 4,
  },
  cabeceraTarjeta: { flexDirection: 'row', alignItems: 'center', gap: espacio.s + 4 },
  cuadroIcono: {
    width: 40,
    height: 40,
    borderRadius: radio.m,
    backgroundColor: colores.primarioSuave,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tituloTarjeta: { fontFamily: fuentes.negrita, fontSize: 15, lineHeight: 20, color: colores.texto },
  botonIcono: { width: 40, height: tactil, alignItems: 'center', justifyContent: 'center', marginRight: -espacio.s },
  fotos: { flexDirection: 'row', flexWrap: 'wrap', gap: espacio.s },
  foto: {
    width: TAMAÑO_FOTO,
    height: TAMAÑO_FOTO,
    borderRadius: radio.m,
    backgroundColor: colores.superficieSuave,
  },
  detalle: { gap: espacio.s, paddingTop: espacio.s, borderTopWidth: 1, borderTopColor: colores.borde },
  filaDetalle: { flexDirection: 'row', alignItems: 'center', gap: espacio.s },
  muestra: { width: 10, height: 10, borderRadius: 5, borderWidth: 1, borderColor: colores.bordeControl },
  verMas: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    alignSelf: 'flex-start',
    minHeight: 32,
    marginBottom: -espacio.xs,
  },
  textoVerMas: { fontFamily: fuentes.media, fontSize: 14, color: colores.primario },

  vacio: { alignItems: 'center', gap: espacio.s, marginTop: espacio.xxl, paddingHorizontal: espacio.xl },
  circuloVacio: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: colores.primarioSuave,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: espacio.s,
  },
  error: { ...texto.detalle, color: colores.error, marginBottom: espacio.m },
}));

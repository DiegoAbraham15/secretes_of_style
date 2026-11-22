// Nueva prenda: eliges una foto y se vuelve un borrador que el servidor procesa (la IA propone los datos, el motor
// le quita el fondo, se mide el color y se propone la temporada). Lo que la persona corrige a mano, la IA ya no
// lo pisa (useFormularioPrenda). "Guardar y agregar otra" deja la pantalla lista para la siguiente; salir con
// datos sin guardar pide confirmación y descarta el borrador. Arriba, atajos a Varias prendas y Desde un link.
import { Image } from 'expo-image';
import { router, useNavigation, usePreventRemove } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Text, View } from 'react-native';

import { confirmarBorrador, crearBorrador, descartarBorrador, obtenerBorrador, urlImagen } from '../../api';
import { ETIQUETA_CATEGORIA, ETIQUETA_COLOR, ETIQUETA_ESTAMPADO, HEX_COLOR } from '../../catalogos';
import { Boton } from '../../componentes/Boton';
import { datosDe, faltaAlgo, FormularioPrenda, useFormularioPrenda } from '../../componentes/FormularioPrenda';
import { confirmar } from '../../confirmar';
import { elegirFoto } from '../../fotos';
import { IconoAbrirLink, IconoAgregar, IconoCamara, IconoGaleria, IconoIA } from '../../iconos';
import { Presionable, vibrar } from '../../movimiento';
import { crearEstilos, espacio, fuentes, presionado, radio, tactil, tamañoIcono, useTema } from '../../tema';

const CADA_CUANTO_MS = 1500;

// Botón de contorno con ícono (origen de la foto y atajos).
function BotonContorno({ icono: Icono, texto: etiqueta, alPresionar }) {
  const { colores } = useTema();
  const estilos = useEstilos();
  return (
    <Presionable onPress={alPresionar} accessibilityRole="button" accessibilityLabel={etiqueta} style={estilos.botonFoto}>
      <Icono color={colores.primario} size={tamañoIcono.s} weight="bold" />
      <Text style={estilos.textoBotonFoto}>{etiqueta}</Text>
    </Presionable>
  );
}

export default function PantallaNuevaPrenda() {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const navegacion = useNavigation();
  const { valores, cambiar, aplicarPropuesta, reiniciar } = useFormularioPrenda();
  const [fotoLocal, establecerFotoLocal] = useState(null);
  const [borrador, establecerBorrador] = useState(null);
  const [subiendo, establecerSubiendo] = useState(false);
  const [guardando, establecerGuardando] = useState(null); // 'cerrar' | 'otra'
  const [agregadas, establecerAgregadas] = useState(0);
  const [error, establecerError] = useState(null);
  const guardada = useRef(false);

  const procesando = borrador && (borrador.estado === 'en_fila' || borrador.estado === 'analizando');
  const lista = borrador?.estado === 'lista';

  // Mientras la IA y el motor trabajan, se pregunta cómo van.
  useEffect(() => {
    if (!procesando) return undefined;
    const temporizador = setInterval(() => {
      obtenerBorrador(borrador.id)
        .then(establecerBorrador)
        .catch(() => {});
    }, CADA_CUANTO_MS);
    return () => clearInterval(temporizador);
  }, [procesando, borrador?.id]);

  useEffect(() => {
    if (lista) aplicarPropuesta(borrador.propuesta);
  }, [lista, borrador?.propuesta, aplicarPropuesta]);

  // Salir con una foto sin guardar: se pregunta y, si sale, el borrador se descarta.
  usePreventRemove(Boolean(borrador), ({ data }) => {
    if (guardada.current) {
      navegacion.dispatch(data.action); // se acaba de guardar: sale sin preguntar
      return;
    }
    confirmar('¿Salir sin guardar?', 'La foto y los datos de esta prenda se perderán.', 'Salir', () => {
      descartarBorrador(borrador.id).catch(() => {});
      navegacion.dispatch(data.action);
    });
  });

  async function elegirImagen(desdeCamara) {
    let uri;
    try {
      uri = await elegirFoto(desdeCamara);
    } catch (e) {
      establecerError(e.message);
      return;
    }
    if (!uri) return;
    if (borrador) descartarBorrador(borrador.id).catch(() => {}); // la foto anterior ya no se usa
    establecerFotoLocal(uri);
    establecerBorrador(null);
    establecerError(null);
    establecerSubiendo(true);
    try {
      establecerBorrador(await crearBorrador(uri));
    } catch (e) {
      establecerError(e.message);
    } finally {
      establecerSubiendo(false);
    }
  }

  async function guardar(otra) {
    if (!borrador || faltaAlgo(valores)) {
      establecerError('Falta la foto, la categoría, el color o el nivel de abrigo.');
      return;
    }
    establecerGuardando(otra ? 'otra' : 'cerrar');
    establecerError(null);
    try {
      await confirmarBorrador(borrador.id, datosDe(valores));
      vibrar.exito();
      if (otra) {
        establecerAgregadas((n) => n + 1);
        establecerBorrador(null);
        establecerFotoLocal(null);
        reiniciar();
      } else {
        guardada.current = true;
        router.back();
      }
    } catch (e) {
      establecerError(e.message);
    } finally {
      establecerGuardando(null);
    }
  }

  const propuesta = borrador?.propuesta ?? {};
  const resumenIA = [
    propuesta.subcategoria || ETIQUETA_CATEGORIA[propuesta.categoria],
    ETIQUETA_COLOR[propuesta.color_principal],
    ETIQUETA_ESTAMPADO[propuesta.estampado],
  ]
    .filter(Boolean)
    .join(', ');
  const foto = lista ? urlImagen(borrador.url_imagen) : fotoLocal;

  return (
    <ScrollView style={estilos.pantalla} contentContainerStyle={estilos.contenido} keyboardShouldPersistTaps="handled">
      {/* Atajos: muchas prendas o una de una tienda en línea */}
      <View style={estilos.atajos}>
        <BotonContorno icono={IconoGaleria} texto="Varias fotos" alPresionar={() => router.replace('/carga-masiva')} />
        <BotonContorno icono={IconoAbrirLink} texto="Desde un link" alPresionar={() => router.replace('/importar')} />
      </View>

      {agregadas > 0 && (
        <Text style={[texto.detalle, { textAlign: 'center', marginBottom: espacio.m }]} accessibilityLiveRegion="polite">
          {agregadas} {agregadas === 1 ? 'prenda agregada' : 'prendas agregadas'}. Sigue con la próxima.
        </Text>
      )}

      <View style={estilos.zonaFoto}>
        <Pressable
          onPress={() => elegirImagen(false)}
          accessibilityRole="button"
          accessibilityLabel={foto ? 'Cambiar foto desde la galería' : 'Agregar foto desde la galería'}
          style={({ pressed }) => [estilos.marcoFoto, !foto && estilos.marcoVacio, pressed && presionado]}>
          {foto ? (
            <Image source={{ uri: foto }} style={estilos.foto} contentFit={borrador?.sin_fondo ? 'contain' : 'cover'} transition={250} />
          ) : (
            <View style={estilos.sinFoto}>
              <IconoGaleria color={colores.primario} size={tamañoIcono.l} />
              <Text style={[texto.cuerpoFuerte, { marginTop: espacio.m }]}>Agrega una foto</Text>
              <Text style={[texto.nota, { textAlign: 'center', marginTop: espacio.xs }]}>
                Le quitamos el fondo solos; con buena luz se ve mejor
              </Text>
            </View>
          )}
          {foto && valores.color_principal && (
            <View style={[estilos.muestraFoto, { backgroundColor: HEX_COLOR[valores.color_principal] }]} />
          )}
        </Pressable>

        {(subiendo || borrador) && (
          <View style={estilos.avisoIA} accessibilityLiveRegion="polite">
            {subiendo || procesando ? (
              <ActivityIndicator color={colores.primario} size="small" />
            ) : (
              <IconoIA color={borrador?.estado === 'error' ? colores.error : colores.primario} size={tamañoIcono.s} />
            )}
            <Text style={[texto.detalle, { flex: 1 }]}>
              {subiendo
                ? 'Subiendo la foto…'
                : procesando
                  ? 'La IA la está viendo y quitando el fondo…'
                  : borrador.estado === 'error'
                    ? 'No se pudo analizar; llena los datos a mano.'
                    : [
                        resumenIA ? `Detectado con IA: ${resumenIA}.` : null,
                        borrador.sin_fondo ? 'Fondo quitado.' : null,
                        ...(borrador.avisos ?? []),
                        'Revisa los datos antes de guardar.',
                      ]
                        .filter(Boolean)
                        .join(' ')}
            </Text>
          </View>
        )}
        {borrador?.duplicada_de && (
          <Text style={[texto.detalle, { color: colores.texto, marginTop: espacio.s }]}>Ya tienes esta misma foto en tu armario.</Text>
        )}

        <View style={estilos.botonesFoto}>
          <BotonContorno icono={IconoGaleria} texto={foto ? 'Otra de galería' : 'Galería'} alPresionar={() => elegirImagen(false)} />
          <BotonContorno icono={IconoCamara} texto={foto ? 'Tomar otra' : 'Cámara'} alPresionar={() => elegirImagen(true)} />
        </View>
      </View>

      <FormularioPrenda valores={valores} alCambiar={cambiar} conCompra />

      {error && (
        <Text style={estilos.error} accessibilityLiveRegion="polite" accessibilityRole="alert">
          {error}
        </Text>
      )}
      <View style={{ gap: espacio.s }}>
        <Boton texto="Guardar prenda" alPresionar={() => guardar(false)} cargando={guardando === 'cerrar'} deshabilitado={!borrador || Boolean(guardando)} />
        <Boton
          texto="Guardar y agregar otra"
          icono={IconoAgregar}
          secundario
          alPresionar={() => guardar(true)}
          cargando={guardando === 'otra'}
          deshabilitado={!borrador || Boolean(guardando)}
        />
      </View>
    </ScrollView>
  );
}

const useEstilos = crearEstilos(({ colores, texto }) => ({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  contenido: { padding: espacio.l, paddingBottom: espacio.xxl },
  atajos: { flexDirection: 'row', gap: espacio.s, justifyContent: 'center', marginBottom: espacio.l },
  zonaFoto: { alignItems: 'center', marginBottom: espacio.xl },
  marcoFoto: {
    width: '62%',
    maxWidth: 260,
    aspectRatio: 3 / 4,
    borderRadius: radio.l,
    backgroundColor: colores.superficieSuave,
    overflow: 'hidden',
  },
  marcoVacio: { backgroundColor: colores.superficie, borderWidth: 1.5, borderStyle: 'dashed', borderColor: colores.primario },
  foto: { width: '100%', height: '100%' },
  sinFoto: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: espacio.m },
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
  avisoIA: {
    alignSelf: 'stretch',
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.s,
    marginTop: espacio.m,
    paddingVertical: espacio.s,
    paddingHorizontal: espacio.m,
    borderRadius: radio.m,
    backgroundColor: colores.superficieSuave,
  },
  botonesFoto: { flexDirection: 'row', gap: espacio.s, marginTop: espacio.m },
  botonFoto: {
    minHeight: tactil,
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.s,
    paddingHorizontal: espacio.m,
    borderRadius: radio.m,
    borderWidth: 1.5,
    borderColor: colores.primario,
    backgroundColor: colores.superficie,
  },
  textoBotonFoto: { fontFamily: fuentes.negrita, fontSize: 15, color: colores.primario },
  error: { ...texto.detalle, color: colores.error, marginBottom: espacio.m },
}));

import { Image } from 'expo-image';
import { ImageManipulator, SaveFormat } from 'expo-image-manipulator';
import * as ImagePicker from 'expo-image-picker';
import { router } from 'expo-router';
import { useRef, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, Switch, Text, View } from 'react-native';

import { analizarPrenda, subirPrenda } from '../../api';
import {
  CATEGORIAS,
  COLORES,
  ESTAMPADOS,
  ESTILOS,
  ETIQUETA_CATEGORIA,
  ETIQUETA_COLOR,
  ETIQUETA_ESTAMPADO,
  HEX_COLOR,
  NIVELES_ABRIGO,
} from '../../catalogos';
import { Boton } from '../../componentes/Boton';
import { Campo } from '../../componentes/Campo';
import { Selector } from '../../componentes/Selector';
import { IconoCamara, IconoGaleria, IconoIA } from '../../iconos';
import { Presionable, vibrar } from '../../movimiento';
import { crearEstilos, espacio, fuentes, presionado, radio, tactil, tamañoIcono, useTema } from '../../tema';

const ANCHO_MAXIMO_FOTO = 1200;

// Reduce la foto antes de subirla: a 1200 px de ancho en JPEG pesa unos cientos de KB en vez de varios MB.
async function reducirFoto(foto) {
  const contexto = ImageManipulator.manipulate(foto.uri);
  if (foto.width > ANCHO_MAXIMO_FOTO) contexto.resize({ width: ANCHO_MAXIMO_FOTO, height: null });
  const imagen = await contexto.renderAsync();
  const guardada = await imagen.saveAsync({ format: SaveFormat.JPEG, compress: 0.7 });
  return guardada.uri;
}

// Botón de contorno con ícono para elegir el origen de la foto.
function BotonFoto({ icono: Icono, texto: etiqueta, alPresionar }) {
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
  const [imagen, establecerImagen] = useState(null); // { uri, nombre }
  const [categoria, establecerCategoria] = useState(null);
  const [subcategoria, establecerSubcategoria] = useState('');
  const [color, establecerColor] = useState(null);
  const [estampado, establecerEstampado] = useState('liso');
  const [estilo, establecerEstilo] = useState('casual');
  const [nivelAbrigo, establecerNivelAbrigo] = useState(null);
  const [impermeable, establecerImpermeable] = useState(false);
  const [error, establecerError] = useState(null);
  const [guardando, establecerGuardando] = useState(false);
  const [analisis, establecerAnalisis] = useState(null); // { cargando } o { texto, error }
  const fotoActual = useRef(null); // si cambian la foto mientras se analiza, se ignora la respuesta vieja

  // La IA del servidor propone los datos de la prenda; la persona los revisa y corrige antes de guardar.
  async function analizar(uri) {
    fotoActual.current = uri;
    establecerAnalisis({ cargando: true });
    try {
      const prenda = await analizarPrenda(uri, 'prenda.jpg');
      if (fotoActual.current !== uri) return;
      if (prenda.categoria) establecerCategoria(prenda.categoria);
      if (prenda.subcategoria) establecerSubcategoria(prenda.subcategoria);
      if (prenda.color_principal) establecerColor(prenda.color_principal);
      if (prenda.estampado) establecerEstampado(prenda.estampado);
      if (prenda.estilo) establecerEstilo(prenda.estilo);
      if (prenda.nivel_abrigo) establecerNivelAbrigo(prenda.nivel_abrigo);
      establecerImpermeable(prenda.impermeable);
      const resumen = [
        prenda.subcategoria || ETIQUETA_CATEGORIA[prenda.categoria],
        ETIQUETA_COLOR[prenda.color_principal],
        ETIQUETA_ESTAMPADO[prenda.estampado],
      ]
        .filter(Boolean)
        .join(', ');
      establecerAnalisis({ texto: `Detectado con IA: ${resumen}. Revisa los datos antes de guardar.` });
    } catch {
      if (fotoActual.current !== uri) return;
      establecerAnalisis({ error: true, texto: 'No se pudo analizar la foto; llena los datos a mano.' });
    }
  }

  async function elegirImagen(desdeCamara) {
    const permiso = desdeCamara
      ? await ImagePicker.requestCameraPermissionsAsync()
      : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permiso.granted) {
      establecerError('Da permiso de fotos o cámara en los ajustes del teléfono para agregar la foto.');
      return;
    }

    // Calidad 1: la compresión se hace una sola vez, al reducir la foto.
    const opciones = { mediaTypes: ['images'], allowsEditing: true, aspect: [3, 4], quality: 1 };
    const resultado = desdeCamara
      ? await ImagePicker.launchCameraAsync(opciones)
      : await ImagePicker.launchImageLibraryAsync(opciones);
    if (resultado.canceled) return;

    let uri;
    try {
      uri = await reducirFoto(resultado.assets[0]);
      establecerImagen({ uri, nombre: 'prenda.jpg' });
      establecerError(null);
    } catch {
      establecerError('No se pudo preparar la foto. Intenta con otra.');
      return;
    }
    analizar(uri);
  }

  async function guardar() {
    if (!imagen || !categoria || !color || !nivelAbrigo) {
      establecerError('Falta la foto, la categoría, el color o el nivel de abrigo.');
      return;
    }
    establecerGuardando(true);
    establecerError(null);
    try {
      await subirPrenda({
        uriImagen: imagen.uri,
        nombreImagen: imagen.nombre,
        categoria,
        subcategoria: subcategoria.trim(),
        color_principal: color,
        nivel_abrigo: nivelAbrigo,
        impermeable,
        estampado,
        estilo,
      });
      vibrar.exito();
      router.back();
    } catch (e) {
      establecerError(e.message);
    } finally {
      establecerGuardando(false);
    }
  }

  return (
    <ScrollView style={estilos.pantalla} contentContainerStyle={estilos.contenido} keyboardShouldPersistTaps="handled">
      {/* Foto de la prenda: grande y centrada, con una vista previa de cómo se verá en el armario */}
      <View style={estilos.zonaFoto}>
        <Pressable
          onPress={() => elegirImagen(false)}
          accessibilityRole="button"
          accessibilityLabel={imagen ? 'Cambiar foto desde la galería' : 'Agregar foto desde la galería'}
          style={({ pressed }) => [estilos.marcoFoto, !imagen && estilos.marcoVacio, pressed && presionado]}>
          {imagen ? (
            <Image source={{ uri: imagen.uri }} style={estilos.foto} contentFit="cover" transition={200} />
          ) : (
            <View style={estilos.sinFoto}>
              <IconoGaleria color={colores.primario} size={tamañoIcono.l} />
              <Text style={[texto.cuerpoFuerte, { marginTop: espacio.m }]}>Agrega una foto</Text>
              <Text style={[texto.nota, { textAlign: 'center', marginTop: espacio.xs }]}>
                Sobre un fondo liso y con buena luz se ve mejor
              </Text>
            </View>
          )}
          {imagen && color && <View style={[estilos.muestraFoto, { backgroundColor: HEX_COLOR[color] }]} />}
        </Pressable>

        {imagen && (
          <View style={{ alignItems: 'center', marginTop: espacio.m }}>
            <Text style={texto.cuerpoFuerte} numberOfLines={1}>
              {subcategoria.trim() || ETIQUETA_CATEGORIA[categoria] || 'Tu prenda'}
            </Text>
            <Text style={texto.nota}>
              {[
                ETIQUETA_COLOR[color],
                estampado !== 'liso' && ETIQUETA_ESTAMPADO[estampado].toLowerCase(),
                nivelAbrigo && `abrigo ${nivelAbrigo} de 5`,
                impermeable && 'impermeable',
              ]
                .filter(Boolean)
                .join(', ') || 'Completa los datos de abajo'}
            </Text>
          </View>
        )}

        {analisis && (
          <View style={estilos.avisoIA} accessibilityLiveRegion="polite">
            {analisis.cargando ? (
              <ActivityIndicator color={colores.primario} size="small" />
            ) : (
              <IconoIA color={analisis.error ? colores.error : colores.primario} size={tamañoIcono.s} />
            )}
            <Text style={[texto.detalle, { flex: 1 }, analisis.error && { color: colores.error }]}>
              {analisis.cargando ? 'Analizando la foto con IA…' : analisis.texto}
            </Text>
          </View>
        )}

        <View style={estilos.botonesFoto}>
          <BotonFoto
            icono={IconoGaleria}
            texto={imagen ? 'Otra de galería' : 'Galería'}
            alPresionar={() => elegirImagen(false)}
          />
          <BotonFoto icono={IconoCamara} texto={imagen ? 'Tomar otra' : 'Cámara'} alPresionar={() => elegirImagen(true)} />
        </View>
      </View>

      <Selector titulo="Categoría" opciones={CATEGORIAS} seleccionado={categoria} alCambiar={establecerCategoria} />

      <Text style={texto.antetitulo} nativeID="etiquetaTipo">
        Tipo de prenda (opcional)
      </Text>
      <Campo
        value={subcategoria}
        onChangeText={establecerSubcategoria}
        placeholder="Blusa, jeans, botines"
        maxLength={60}
        accessibilityLabel="Tipo de prenda, opcional"
        accessibilityLabelledBy="etiquetaTipo"
        estilo={estilos.campo}
      />

      <Selector titulo="Color principal" opciones={COLORES} seleccionado={color} alCambiar={establecerColor} />
      <Selector titulo="Estampado" opciones={ESTAMPADOS} seleccionado={estampado} alCambiar={establecerEstampado} />
      <Selector titulo="Estilo" opciones={ESTILOS} seleccionado={estilo} alCambiar={establecerEstilo} />
      <Selector
        titulo="Nivel de abrigo"
        opciones={NIVELES_ABRIGO}
        seleccionado={nivelAbrigo}
        alCambiar={establecerNivelAbrigo}
      />

      <View style={estilos.interruptor}>
        <View style={{ flex: 1 }}>
          <Text style={texto.cuerpoFuerte}>Impermeable</Text>
          <Text style={texto.detalle}>Resiste la lluvia</Text>
        </View>
        <Switch
          value={impermeable}
          onValueChange={establecerImpermeable}
          accessibilityLabel="Impermeable"
          trackColor={{ true: colores.primario, false: colores.bordeControl }}
        />
      </View>

      {error && (
        <Text style={estilos.error} accessibilityLiveRegion="polite" accessibilityRole="alert">
          {error}
        </Text>
      )}
      <Boton texto="Guardar prenda" alPresionar={guardar} cargando={guardando} />
    </ScrollView>
  );
}

const useEstilos = crearEstilos(({ colores, texto }) => ({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  contenido: { padding: espacio.l, paddingBottom: espacio.xxl },
  zonaFoto: { alignItems: 'center', marginBottom: espacio.xl },
  marcoFoto: {
    width: '62%',
    maxWidth: 260,
    aspectRatio: 3 / 4,
    borderRadius: radio.l,
    backgroundColor: colores.superficieSuave,
    overflow: 'hidden',
  },
  marcoVacio: {
    backgroundColor: colores.superficie,
    borderWidth: 1.5,
    borderStyle: 'dashed',
    borderColor: colores.primario,
  },
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
  campo: { marginTop: espacio.s, marginBottom: espacio.l },
  interruptor: { flexDirection: 'row', alignItems: 'center', minHeight: tactil, marginBottom: espacio.l },
  error: { ...texto.detalle, color: colores.error, marginBottom: espacio.m },
}));

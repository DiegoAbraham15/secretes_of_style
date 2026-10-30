// Un atuendo sugerido como tarjeta: arriba una franja con las fotos de sus prendas, de arriba abajo como se
// usan (accesorio, abrigo, parte superior, parte inferior, calzado), y debajo "Look N", el nombre de cada
// prenda con por qué combina con la base, las ventajas para el clima y las acciones.
// etiqueta: aviso sobre las fotos (p. ej. "La mejor opción"). destacado: resalta la tarjeta.
// alExplicar: botón "¿Por qué?"; explicacion ({ texto } o { error }) es lo que redactó la IA.
// conCorazon y alCorazon: el corazón con el que la persona le enseña sus gustos a la app; errorVoto si no se guardó.
import { Image } from 'expo-image';
import { Pressable, Text, View } from 'react-native';

import { urlImagen } from '../api';
import { ETIQUETA_COLOR, HEX_COLOR, nombreDePrenda, ORDEN_CUERPO } from '../catalogos';
import { IconoCorazon, IconoGuardados, IconoIA, IconoPalomita, IconoVentaja } from '../iconos';
import { crearEstilos, espacio, fuentes, presionado, radio, tactil, tamañoIcono, useTema } from '../tema';
import { Boton } from './Boton';

const nombreConColor = (prenda) => `${nombreDePrenda(prenda)} ${ETIQUETA_COLOR[prenda.color_principal].toLowerCase()}`;

function Prenda({ prenda, motivo, esBase }) {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  return (
    <View style={estilos.fila}>
      <View style={[estilos.muestra, { backgroundColor: HEX_COLOR[prenda.color_principal] }]} />
      <View style={estilos.datos}>
        <Text style={estilos.nombre}>{nombreConColor(prenda)}</Text>
        {motivo && <Text style={texto.nota}>{motivo[0].toUpperCase() + motivo.slice(1)}</Text>}
      </View>
      {esBase && <Text style={[texto.nota, { color: colores.primario }]}>Tu base</Text>}
    </View>
  );
}

export function Perchero({
  sugerencia,
  numero,
  etiqueta,
  destacado = false,
  guardada,
  guardando,
  alGuardar,
  alExplicar,
  explicando,
  explicacion,
  conCorazon,
  alCorazon,
  errorVoto,
}) {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const { elementos, ventajas } = sugerencia;
  const base = elementos[0];

  // De arriba abajo, como se usa la ropa.
  const ordenadas = [...elementos].sort(
    (a, b) => ORDEN_CUERPO.indexOf(a.prenda.categoria) - ORDEN_CUERPO.indexOf(b.prenda.categoria),
  );

  return (
    <View style={[estilos.tarjeta, destacado && estilos.tarjetaDestacada]}>
      <View style={estilos.fotos}>
        {ordenadas.map(({ prenda }) => (
          <Image
            key={prenda.id}
            source={{ uri: urlImagen(prenda.url_imagen) }}
            style={estilos.foto}
            contentFit="cover"
            cachePolicy="memory-disk"
            transition={200}
            accessibilityLabel={nombreConColor(prenda)}
          />
        ))}
        {etiqueta && <Text style={estilos.etiqueta}>{etiqueta}</Text>}
      </View>

      <View style={estilos.cuerpo}>
        <View style={estilos.cabecera}>
          <View style={{ flex: 1 }}>
            <Text style={estilos.look} accessibilityRole="header">
              Look {numero}
            </Text>
            <Text style={texto.nota}>
              {ventajas.length > 0
                ? `${ventajas.length} ${ventajas.length === 1 ? 'ventaja' : 'ventajas'} para hoy`
                : 'Sin ventajas extra'}
            </Text>
          </View>
          <Pressable
            onPress={alCorazon}
            accessibilityRole="button"
            accessibilityLabel="Me gusta este atuendo"
            accessibilityState={{ selected: conCorazon }}
            style={({ pressed }) => [estilos.corazon, conCorazon && estilos.corazonActivo, pressed && presionado]}>
            <IconoCorazon
              color={conCorazon ? colores.primario : colores.textoSecundario}
              size={tamañoIcono.m}
              weight={conCorazon ? 'fill' : 'regular'}
            />
          </Pressable>
        </View>
        {errorVoto && (
          <Text style={[texto.detalle, { color: colores.error }]} accessibilityRole="alert">
            {errorVoto}
          </Text>
        )}

        <View style={estilos.prendas}>
          {ordenadas.map((elemento) => (
            <Prenda key={elemento.prenda.id} {...elemento} esBase={elemento === base} />
          ))}
        </View>

        {ventajas.length > 0 && (
          <View style={estilos.ventajas}>
            {ventajas.map((ventaja) => (
              <View key={ventaja} style={estilos.ventaja}>
                <IconoVentaja color={colores.acento} size={16} weight="fill" />
                <Text style={[texto.detalle, { flex: 1, color: colores.texto }]}>{ventaja}</Text>
              </View>
            ))}
          </View>
        )}

        {explicacion?.texto && (
          <View style={estilos.explicacion} accessibilityLiveRegion="polite">
            <View style={estilos.ventaja}>
              <IconoIA color={colores.primario} size={16} />
              <Text style={[texto.antetitulo, { color: colores.primario }]}>Por qué funciona</Text>
            </View>
            <Text style={[texto.detalle, { color: colores.texto }]}>{explicacion.texto}</Text>
          </View>
        )}
        {explicacion?.error && (
          <Text style={[texto.detalle, { color: colores.error }]} accessibilityRole="alert">
            {explicacion.error}
          </Text>
        )}

        <View style={estilos.acciones}>
          <View style={{ flex: 1 }}>
            <Boton
              texto={guardada ? 'Guardado' : 'Guardar'}
              icono={guardada ? IconoPalomita : IconoGuardados}
              secundario={guardada || !destacado}
              alPresionar={alGuardar}
              cargando={guardando}
              deshabilitado={guardada}
            />
          </View>
          {!explicacion?.texto && (
            <View style={{ flex: 1 }}>
              <Boton
                texto={explicando ? 'Pensando…' : '¿Por qué?'}
                icono={IconoIA}
                secundario
                alPresionar={alExplicar}
                cargando={explicando}
              />
            </View>
          )}
        </View>
      </View>
    </View>
  );
}

const useEstilos = crearEstilos(({ colores, texto, tarjeta }) => ({
  tarjeta: { ...tarjeta, overflow: 'hidden', marginBottom: espacio.m },
  tarjetaDestacada: { borderWidth: 2, borderColor: colores.primario },

  // Las fotos van de orilla a orilla y separadas por una línea, como una tira de catálogo.
  fotos: { flexDirection: 'row', gap: 2, backgroundColor: colores.borde },
  foto: { flex: 1, aspectRatio: 3 / 4, backgroundColor: colores.superficieSuave },
  etiqueta: {
    position: 'absolute',
    top: espacio.s + 4,
    left: espacio.s + 4,
    fontFamily: fuentes.media,
    fontSize: 13,
    color: colores.sobreAcento,
    backgroundColor: colores.acento,
    paddingHorizontal: espacio.s + 2,
    paddingVertical: espacio.xs,
    borderRadius: radio.pastilla,
    overflow: 'hidden',
  },

  cuerpo: { padding: espacio.m, gap: espacio.m },
  cabecera: { flexDirection: 'row', alignItems: 'center', gap: espacio.s },
  corazon: {
    width: tactil,
    height: tactil,
    borderRadius: tactil / 2,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colores.superficieSuave,
  },
  corazonActivo: { backgroundColor: colores.primarioSuave },
  look: { fontFamily: fuentes.displayItalica, fontSize: 32, lineHeight: 40, color: colores.texto },

  prendas: { gap: espacio.s + 4 },
  fila: { flexDirection: 'row', alignItems: 'flex-start', gap: espacio.s + 2 },
  muestra: { width: 12, height: 12, borderRadius: 6, marginTop: 4, borderWidth: 1, borderColor: colores.bordeControl },
  datos: { flex: 1, minWidth: 0 },
  nombre: { ...texto.cuerpoFuerte, fontFamily: fuentes.negrita, fontSize: 15, lineHeight: 20 },

  ventajas: { padding: espacio.s + 4, borderRadius: radio.m, backgroundColor: colores.superficieSuave, gap: espacio.s },
  ventaja: { flexDirection: 'row', alignItems: 'center', gap: espacio.s },
  // La explicación de la IA se lee como una cita: línea rosa a la izquierda.
  explicacion: { paddingLeft: espacio.m, borderLeftWidth: 3, borderLeftColor: colores.primario, gap: espacio.s },
  acciones: { flexDirection: 'row', gap: espacio.s },
}));

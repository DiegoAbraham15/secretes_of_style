// Un atuendo mostrado como maniquí: las prendas apiladas de arriba abajo como se usan
// (accesorio, abrigo, parte superior, parte inferior, calzado), cada una con su nombre
// y por qué combina con la prenda base. Abajo, las ventajas para el clima.
// titulo: reemplaza "Atuendo N" (p. ej. la fecha en Guardados). etiqueta: aviso arriba (p. ej. "La mejor opción").
// destacado: resalta la tarjeta. alGuardar / alEliminar: botón al pie (no aparece si no se pasa).
import { Image } from 'expo-image';
import { Text, View } from 'react-native';

import { urlImagen } from '../api';
import { ETIQUETA_CATEGORIA, ETIQUETA_COLOR, HEX_COLOR, nombreDePrenda } from '../catalogos';
import { IconoEliminar, IconoGuardados, IconoPalomita, IconoVentaja } from '../iconos';
import { crearEstilos, espacio, fuentes, radio, useTema } from '../tema';
import { Boton } from './Boton';

const ORDEN_CUERPO = ['accesorio', 'abrigo', 'parte_superior', 'parte_inferior', 'calzado'];
const ANCHO_FOTO = 80;

function Prenda({ prenda, motivo, esBase }) {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  return (
    <View style={estilos.fila}>
      <Image
        source={{ uri: urlImagen(prenda.url_imagen) }}
        style={estilos.foto}
        contentFit="cover"
        cachePolicy="memory-disk"
        transition={200}
      />

      <View style={estilos.datos}>
        <Text style={[texto.antetitulo, esBase && { color: colores.primario }]}>
          {ETIQUETA_CATEGORIA[prenda.categoria]}
          {esBase && ' · tu prenda base'}
        </Text>
        <View style={estilos.filaNombre}>
          <View style={[estilos.muestra, { backgroundColor: HEX_COLOR[prenda.color_principal] }]} />
          <Text style={estilos.nombre} numberOfLines={2}>
            {nombreDePrenda(prenda)} {ETIQUETA_COLOR[prenda.color_principal].toLowerCase()}
          </Text>
        </View>
        {motivo && <Text style={texto.nota}>{motivo[0].toUpperCase() + motivo.slice(1)}</Text>}
      </View>
    </View>
  );
}

export function Perchero({
  sugerencia,
  numero,
  titulo,
  etiqueta,
  destacado = false,
  guardada,
  guardando,
  alGuardar,
  alEliminar,
  eliminando,
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
      {etiqueta && <Text style={[estilos.etiqueta, destacado && estilos.etiquetaDestacada]}>{etiqueta}</Text>}

      <Text style={texto.subtitulo}>{titulo ?? `Atuendo ${numero}`}</Text>
      {ventajas && (
        <Text style={[texto.detalle, { marginTop: 2 }]}>
          {ventajas.length > 0
            ? `${ventajas.length} ${ventajas.length === 1 ? 'ventaja' : 'ventajas'} para hoy`
            : 'Sin ventajas extra'}
        </Text>
      )}

      {/* El maniquí: una línea vertical une las prendas de arriba abajo */}
      <View style={estilos.maniqui}>
        <View style={estilos.columna} />
        {ordenadas.map((elemento) => (
          <Prenda key={elemento.prenda.id} {...elemento} esBase={elemento === base} />
        ))}
      </View>

      {ventajas?.length > 0 && (
        <View style={estilos.ventajas}>
          {ventajas.map((ventaja) => (
            <View key={ventaja} style={estilos.ventaja}>
              <IconoVentaja color={colores.acento} size={16} weight="fill" />
              <Text style={[texto.detalle, { flex: 1, color: colores.texto }]}>{ventaja}</Text>
            </View>
          ))}
        </View>
      )}

      {alGuardar && (
        <View style={{ marginTop: espacio.m }}>
          <Boton
            texto={guardada ? 'Guardado' : 'Guardar atuendo'}
            icono={guardada ? IconoPalomita : IconoGuardados}
            secundario={guardada || !destacado}
            alPresionar={alGuardar}
            cargando={guardando}
            deshabilitado={guardada}
          />
        </View>
      )}
      {alEliminar && (
        <View style={{ marginTop: espacio.m }}>
          <Boton texto="Eliminar" icono={IconoEliminar} peligro alPresionar={alEliminar} cargando={eliminando} />
        </View>
      )}
    </View>
  );
}

const useEstilos = crearEstilos(({ colores, texto, tarjeta }) => ({
  tarjeta: { ...tarjeta, padding: espacio.m, marginBottom: espacio.m },
  tarjetaDestacada: { borderWidth: 2, borderColor: colores.primario },
  etiqueta: {
    alignSelf: 'flex-start',
    fontFamily: fuentes.negrita,
    fontSize: 12,
    letterSpacing: 0.6,
    textTransform: 'uppercase',
    color: colores.primario,
    backgroundColor: colores.primarioSuave,
    paddingHorizontal: espacio.s + 2,
    paddingVertical: espacio.xs,
    borderRadius: radio.pastilla,
    overflow: 'hidden',
    marginBottom: espacio.s,
  },
  // "La mejor opción": dorado de la paleta con texto negro.
  etiquetaDestacada: { color: colores.sobreAcento, backgroundColor: colores.acento },

  maniqui: { marginTop: espacio.m, gap: espacio.s },
  columna: {
    position: 'absolute',
    top: espacio.m,
    bottom: espacio.m,
    left: ANCHO_FOTO / 2 - 1,
    width: 2,
    backgroundColor: colores.superficieSuave,
  },
  fila: { flexDirection: 'row', alignItems: 'center', gap: espacio.m },
  foto: {
    width: ANCHO_FOTO,
    aspectRatio: 4 / 5,
    borderRadius: radio.l,
    backgroundColor: colores.superficieSuave,
    borderWidth: 2,
    borderColor: colores.superficie,
  },
  datos: { flex: 1, gap: 2 },
  filaNombre: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  muestra: { width: 12, height: 12, borderRadius: 6, borderWidth: 1, borderColor: colores.bordeControl },
  nombre: { ...texto.cuerpoFuerte, flex: 1, fontSize: 15, lineHeight: 20 },

  ventajas: {
    marginTop: espacio.m,
    padding: espacio.m,
    borderRadius: radio.l,
    backgroundColor: colores.superficieSuave,
    gap: espacio.s,
  },
  ventaja: { flexDirection: 'row', alignItems: 'center', gap: espacio.s },
}));

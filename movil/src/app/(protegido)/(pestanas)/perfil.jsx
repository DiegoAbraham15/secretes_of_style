// Perfil: la cuenta y todo lo personal en un solo lugar, como un menú de filas.
import { router } from 'expo-router';
import { ScrollView, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { confirmar } from '../../../confirmar';
import {
  IconoCapsula,
  IconoCorazon,
  IconoEstadisticas,
  IconoIr,
  IconoPaleta,
  IconoProbar,
  IconoSalir,
  IconoTiendas,
} from '../../../iconos';
import { Presionable } from '../../../movimiento';
import { useSesion } from '../../../sesion';
import { crearEstilos, espacio, espacioBarra, fuentes, radio, tamañoIcono, useTema } from '../../../tema';

const SECCIONES = [
  {
    titulo: 'Tu estilo',
    filas: [
      { etiqueta: 'Tu foto para el probador', detalle: 'Ve cómo se te ven tus looks', icono: IconoProbar, ruta: '/tu-foto' },
      { etiqueta: 'Tus gustos', detalle: 'Colores, ropa, estampados y accesorios', icono: IconoCorazon, ruta: '/mis-gustos' },
      { etiqueta: 'Tu colorimetría', detalle: 'Los colores que más te favorecen', icono: IconoPaleta, ruta: '/colorimetria' },
    ],
  },
  {
    titulo: 'Tu armario',
    filas: [
      { etiqueta: 'Cápsulas', detalle: 'Pocas prendas, muchos looks', icono: IconoCapsula, ruta: '/capsula' },
      { etiqueta: 'Tiendas', detalle: 'Lo que viste y te gustó', icono: IconoTiendas, ruta: '/tiendas' },
      { etiqueta: 'Estadísticas', detalle: 'Uso, armario y cómo aprende tus gustos', icono: IconoEstadisticas, ruta: '/estadisticas' },
    ],
  },
];

function Fila({ etiqueta, detalle, icono: Icono, alPresionar, peligro = false, ultima }) {
  const { colores } = useTema();
  const estilos = useEstilos();
  const color = peligro ? colores.error : colores.primario;
  return (
    <Presionable
      onPress={alPresionar}
      accessibilityRole="button"
      accessibilityLabel={etiqueta}
      accessibilityHint={detalle}
      escala={0.98}
      style={[estilos.fila, !ultima && estilos.separada]}>
      <View style={[estilos.icono, peligro && { backgroundColor: colores.errorSuave }]}>
        <Icono color={color} size={tamañoIcono.s + 2} />
      </View>
      <View style={{ flex: 1, minWidth: 0 }}>
        <Text style={[estilos.etiqueta, peligro && { color: colores.error }]}>{etiqueta}</Text>
        {detalle && <Text style={estilos.detalle}>{detalle}</Text>}
      </View>
      {!peligro && <IconoIr color={colores.textoSecundario} size={tamañoIcono.s} />}
    </Presionable>
  );
}

export default function PantallaPerfil() {
  const { texto } = useTema();
  const estilos = useEstilos();
  const { correo, cerrarSesion } = useSesion();
  const { top } = useSafeAreaInsets();

  const salir = () =>
    confirmar(
      'Cerrar sesión',
      `${correo ? `Entraste como ${correo}. ` : ''}¿Quieres cerrar tu sesión? Se cerrará también en tus otros dispositivos.`,
      'Salir',
      cerrarSesion,
    );

  return (
    <ScrollView style={estilos.pantalla} contentContainerStyle={[estilos.contenido, { paddingTop: top + espacio.l }]}>
      <View style={estilos.cabecera}>
        <View style={estilos.avatar}>
          <Text style={estilos.inicial}>{correo ? correo[0].toUpperCase() : ''}</Text>
        </View>
        <Text style={texto.titulo} accessibilityRole="header">
          Tu perfil
        </Text>
        {correo && <Text style={texto.detalle}>{correo}</Text>}
      </View>

      {SECCIONES.map((seccion) => (
        <View key={seccion.titulo} style={{ gap: espacio.s }}>
          <Text style={texto.antetitulo}>{seccion.titulo}</Text>
          <View style={estilos.grupo}>
            {seccion.filas.map((fila, i) => (
              <Fila key={fila.ruta} {...fila} ultima={i === seccion.filas.length - 1} alPresionar={() => router.push(fila.ruta)} />
            ))}
          </View>
        </View>
      ))}

      <View style={estilos.grupo}>
        <Fila etiqueta="Cerrar sesión" icono={IconoSalir} peligro ultima alPresionar={salir} />
      </View>
    </ScrollView>
  );
}

const useEstilos = crearEstilos(({ colores, tarjeta }) => ({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  contenido: { paddingHorizontal: espacio.m, paddingBottom: espacioBarra, gap: espacio.l },
  cabecera: { alignItems: 'center', gap: espacio.xs },
  avatar: {
    width: 88,
    height: 88,
    borderRadius: 44,
    backgroundColor: colores.primarioSuave,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: espacio.s,
  },
  inicial: { fontFamily: fuentes.negrita, fontSize: 36, lineHeight: 42, color: colores.primario },
  grupo: { ...tarjeta, paddingHorizontal: espacio.m },
  fila: { flexDirection: 'row', alignItems: 'center', gap: espacio.m, minHeight: 64, paddingVertical: espacio.s },
  separada: { borderBottomWidth: 1, borderBottomColor: colores.borde },
  icono: {
    width: 40,
    height: 40,
    borderRadius: radio.m,
    backgroundColor: colores.primarioSuave,
    alignItems: 'center',
    justifyContent: 'center',
  },
  etiqueta: { fontFamily: fuentes.media, fontSize: 16, lineHeight: 22, color: colores.texto },
  detalle: { fontFamily: fuentes.regular, fontSize: 13, lineHeight: 18, color: colores.textoSecundario },
}));

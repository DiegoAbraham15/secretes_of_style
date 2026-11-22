// Inicio: el punto de partida. Acceso directo a lo que más se usa (armar el look de hoy), a todas las
// funciones en burbujas, un resumen del armario y el reto de la semana.
import { router, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { RefreshControl, ScrollView, Text, View } from 'react-native';

import { obtenerEstadisticas, obtenerReto } from '../../../api';
import { ETIQUETA_COLOR } from '../../../catalogos';
import { Boton } from '../../../componentes/Boton';
import { Encabezado } from '../../../componentes/Encabezado';
import { TarjetaReto } from '../../../componentes/TarjetaReto';
import {
  IconoArmario,
  IconoAtuendos,
  IconoCapsula,
  IconoEstadisticas,
  IconoGaleria,
  IconoPaleta,
  IconoProbar,
  IconoSorprendeme,
  IconoTiendas,
  IconoViaje,
} from '../../../iconos';
import { Aparecer, Presionable } from '../../../movimiento';
import { crearEstilos, espacio, espacioBarra, fuentes, radio, tamañoIcono, useTema } from '../../../tema';

const ACCESOS = [
  { etiqueta: 'Looks IA', icono: IconoAtuendos, ruta: '/generador' },
  { etiqueta: 'Armario', icono: IconoArmario, ruta: '/armario' },
  { etiqueta: 'Tiendas', icono: IconoTiendas, ruta: '/tiendas' },
  { etiqueta: 'Modo viaje', icono: IconoViaje, ruta: '/viaje' },
  { etiqueta: 'Cápsula', icono: IconoCapsula, ruta: '/capsula' },
  { etiqueta: 'Colorimetría', icono: IconoPaleta, ruta: '/colorimetria' },
  { etiqueta: 'Probador', icono: IconoProbar, ruta: '/tu-foto' },
  { etiqueta: 'Estadísticas', icono: IconoEstadisticas, ruta: '/estadisticas' },
];

function saludo() {
  const hora = new Date().getHours();
  return hora < 12 ? 'Buenos días' : hora < 19 ? 'Buenas tardes' : 'Buenas noches';
}

export default function PantallaInicio() {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const [estadisticas, establecerEstadisticas] = useState(null);
  const [reto, establecerReto] = useState(null);
  const [recargando, establecerRecargando] = useState(false);
  const [anchoAccesos, establecerAnchoAccesos] = useState(0);

  const cargarReto = useCallback(async (nuevo) => {
    try {
      establecerReto(nuevo ?? (await obtenerReto()));
    } catch {
      establecerReto(null);
    }
  }, []);

  const cargar = useCallback(async () => {
    cargarReto();
    try {
      establecerEstadisticas(await obtenerEstadisticas());
    } catch {
      establecerEstadisticas(null);
    }
  }, [cargarReto]);

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

  const indicadores = estadisticas?.indicadores;
  const usado = estadisticas?.uso?.aprovechamiento?.['30'];
  const numeros = indicadores
    ? [
        { valor: indicadores.total_prendas, etiqueta: 'Prendas' },
        { valor: indicadores.atuendos_guardados, etiqueta: 'Looks guardados' },
        usado != null
          ? { valor: `${usado} %`, etiqueta: 'Usado en 30 días' }
          : { valor: ETIQUETA_COLOR[indicadores.color_mas_usado] ?? '—', etiqueta: 'Color que más tienes' },
      ]
    : [];

  return (
    <View style={estilos.pantalla}>
      <Encabezado titulo={saludo()} subtitulo="¿Qué te pones hoy?" />
      <ScrollView
        contentContainerStyle={estilos.contenido}
        refreshControl={<RefreshControl refreshing={recargando} onRefresh={recargar} tintColor={colores.primario} />}>
        <Aparecer indice={0}>
          <View style={estilos.principal}>
            <View style={estilos.principalTexto}>
              <Text style={texto.subtitulo}>Tu look de hoy</Text>
              <Text style={texto.detalle}>Con el clima de tu ciudad, tus gustos y sin repetir lo de estos días.</Text>
            </View>
            <Boton texto="Armar mi look" icono={IconoSorprendeme} alPresionar={() => router.push('/generador')} />
          </View>
        </Aparecer>

        <Aparecer indice={1}>
          <View
            style={estilos.accesos}
            accessibilityRole="menu"
            onLayout={(e) => establecerAnchoAccesos(e.nativeEvent.layout.width - espacio.xs * 2)}>
            {ACCESOS.map((acceso) => (
              <Presionable
                key={acceso.ruta}
                onPress={() => router.push(acceso.ruta)}
                accessibilityRole="button"
                accessibilityLabel={acceso.etiqueta}
                escala={0.94}
                style={[estilos.acceso, { width: Math.floor(anchoAccesos / 4) || 72 }]}>
                <View style={estilos.burbuja}>
                  <acceso.icono color={colores.primario} size={tamañoIcono.m} />
                </View>
                <Text style={estilos.etiquetaAcceso} numberOfLines={1}>
                  {acceso.etiqueta}
                </Text>
              </Presionable>
            ))}
          </View>
        </Aparecer>

        {numeros.length > 0 && (
          <Aparecer indice={2}>
            <View style={estilos.encabezadoSeccion}>
              <Text style={[texto.subtitulo, { flex: 1 }]} accessibilityRole="header">
                Tu armario en números
              </Text>
              <Text style={estilos.enlace} onPress={() => router.push('/estadisticas')} accessibilityRole="link">
                Ver más
              </Text>
            </View>
            <View style={estilos.numeros}>
              {numeros.map((n) => (
                <View key={n.etiqueta} style={estilos.numero}>
                  <Text style={estilos.valor} numberOfLines={1} adjustsFontSizeToFit>
                    {n.valor}
                  </Text>
                  <Text style={texto.nota} numberOfLines={2}>
                    {n.etiqueta}
                  </Text>
                </View>
              ))}
            </View>
          </Aparecer>
        )}

        {indicadores?.total_prendas === 0 && (
          <View style={estilos.vacio}>
            <View style={estilos.burbujaGrande}>
              <IconoArmario color={colores.primario} size={tamañoIcono.l} />
            </View>
            <Text style={[texto.subtitulo, { textAlign: 'center' }]}>Empieza con tu armario</Text>
            <Text style={[texto.detalle, { textAlign: 'center' }]}>
              Agrega algunas prendas y te armamos looks con el clima de hoy.
            </Text>
            <Boton texto="Agregar varias prendas" icono={IconoGaleria} secundario alPresionar={() => router.push('/carga-masiva')} />
          </View>
        )}

        {reto && reto.estado === 'activo' && (
          <Aparecer indice={3}>
            <TarjetaReto reto={reto} alCambiar={cargarReto} />
          </Aparecer>
        )}
      </ScrollView>
    </View>
  );
}

const useEstilos = crearEstilos(({ colores, tarjeta }) => ({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  contenido: { padding: espacio.m, paddingTop: espacio.s, paddingBottom: espacioBarra, gap: espacio.l },
  principal: { ...tarjeta, padding: espacio.l, gap: espacio.m },
  principalTexto: { gap: espacio.xs },
  accesos: { ...tarjeta, flexDirection: 'row', flexWrap: 'wrap', paddingVertical: espacio.m, paddingHorizontal: espacio.xs },
  acceso: { alignItems: 'center', gap: espacio.s, paddingVertical: espacio.s, minHeight: 88 },
  burbuja: {
    width: 52,
    height: 52,
    borderRadius: radio.m,
    backgroundColor: colores.primarioSuave,
    alignItems: 'center',
    justifyContent: 'center',
  },
  etiquetaAcceso: { fontFamily: fuentes.media, fontSize: 12, lineHeight: 16, color: colores.texto, textAlign: 'center' },
  encabezadoSeccion: { flexDirection: 'row', alignItems: 'center', marginBottom: espacio.s },
  enlace: { fontFamily: fuentes.media, fontSize: 14, color: colores.primario, padding: espacio.xs },
  numeros: { flexDirection: 'row', gap: espacio.s },
  numero: { ...tarjeta, flex: 1, padding: espacio.m, gap: espacio.xs, minWidth: 0 },
  valor: { fontFamily: fuentes.negrita, fontSize: 24, lineHeight: 30, color: colores.texto },
  vacio: { ...tarjeta, alignItems: 'center', gap: espacio.s, padding: espacio.l },
  burbujaGrande: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: colores.primarioSuave,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: espacio.s,
  },
}));

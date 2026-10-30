import { useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { ActivityIndicator, ScrollView, Text, View } from 'react-native';

import { obtenerEstadisticas } from '../../../api';
import { ETIQUETA_CATEGORIA, ETIQUETA_COLOR, HEX_COLOR, NIVELES_ABRIGO } from '../../../catalogos';
import { Encabezado } from '../../../componentes/Encabezado';
import { GraficaBarras, GraficaColumnas, Indicadores, Resumen, Seccion } from '../../../componentes/Graficas';
import { IconoGuardados, IconoImpermeable } from '../../../iconos';
import { Aparecer } from '../../../movimiento';
import { crearEstilos, espacio, espacioBarra, useTema } from '../../../tema';

const TITULO = 'Estadísticas';
const COLORES_VISIBLES = 5; // los demás se abren con "Ver los N"

export default function PantallaEstadisticas() {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const [datos, establecerDatos] = useState(null);
  const [error, establecerError] = useState(null);
  const [repeticion, establecerRepeticion] = useState(0); // cambia para que las barras se animen de nuevo

  // Se actualiza cada vez que se abre la pestaña, y las barras vuelven a crecer.
  useFocusEffect(
    useCallback(() => {
      obtenerEstadisticas()
        .then((respuesta) => {
          establecerDatos(respuesta);
          establecerRepeticion((n) => n + 1);
        })
        .catch((e) => establecerError(e.message));
    }, []),
  );

  if (error || !datos) {
    return (
      <View style={estilos.pantalla}>
        <Encabezado titulo={TITULO} />
        {error ? (
          <Text style={[texto.cuerpo, estilos.mensaje, { color: colores.error }]}>{error}</Text>
        ) : (
          <ActivityIndicator color={colores.primario} style={{ marginTop: espacio.xxl }} />
        )}
      </View>
    );
  }

  const { indicadores } = datos;
  const colorMasUsado = indicadores.color_mas_usado;

  // Cada gráfica recibe sus datos ya con las etiquetas en español.
  // Categorías y colores van de mayor a menor; el nivel de abrigo conserva su orden del 1 al 5.
  const porCategoria = Object.entries(datos.por_categoria)
    .map(([categoria, valor]) => ({ etiqueta: ETIQUETA_CATEGORIA[categoria], valor }))
    .sort((a, b) => b.valor - a.valor);
  const porColor = Object.entries(datos.por_color).map(([color, valor]) => ({
    etiqueta: ETIQUETA_COLOR[color],
    valor,
    hex: HEX_COLOR[color],
  }));
  const porNivel = NIVELES_ABRIGO.map((nivel) => ({
    corta: nivel.valor,
    etiqueta: nivel.etiqueta.replace(/^\d /, ''), // "1 Muy fresca": el número ya va bajo la columna
    valor: datos.por_nivel_abrigo[nivel.valor],
  }));

  const colorEmpatado = porColor.filter((c) => c.valor === datos.por_color[colorMasUsado]).length > 1;
  const indicadoresDelArmario = [
    colorMasUsado
      ? {
          hex: HEX_COLOR[colorMasUsado],
          titulo: ETIQUETA_COLOR[colorMasUsado],
          detalle: colorEmpatado ? 'Color que más tienes, con empate' : 'Color que más tienes',
          valor: datos.por_color[colorMasUsado],
        }
      : { icono: IconoGuardados, titulo: 'Ninguno', detalle: 'Color que más tienes', valor: 0 },
    { icono: IconoImpermeable, titulo: 'Impermeables', detalle: 'Listas para la lluvia', valor: indicadores.impermeables },
    { icono: IconoGuardados, titulo: 'Atuendos guardados', detalle: 'En tu pestaña Guardados', valor: indicadores.atuendos_guardados },
  ];

  return (
    <View style={estilos.pantalla}>
      <Encabezado titulo={TITULO} />
      <ScrollView style={estilos.pantalla} contentContainerStyle={estilos.contenido}>
        <Aparecer>
          <Resumen total={indicadores.total_prendas} hallazgo={datos.hallazgo} />
        </Aparecer>

        {indicadores.total_prendas > 0 ? (
          <>
            <Aparecer indice={1}>
              <Indicadores filas={indicadoresDelArmario} />
            </Aparecer>
            <Aparecer indice={2}>
              <Seccion titulo="Por categoría" nota="Toca para ver el detalle">
                <GraficaBarras datos={porCategoria} unidad="prendas" repeticion={repeticion} />
              </Seccion>
            </Aparecer>
            <Seccion titulo="Por color" nota={`${porColor.length} ${porColor.length === 1 ? 'color' : 'colores'}`}>
              <GraficaBarras datos={porColor} unidad="prendas" repeticion={repeticion} limite={COLORES_VISIBLES} />
            </Seccion>
            <Seccion titulo="Por nivel de abrigo">
              <GraficaColumnas
                datos={porNivel}
                unidad="prendas"
                repeticion={repeticion}
                inicio="Para calor"
                fin="Para frío"
              />
            </Seccion>
          </>
        ) : (
          <Text style={[texto.cuerpo, { color: colores.textoSecundario }]}>
            Las gráficas aparecen cuando agregas tu primera prenda en la pestaña Armario.
          </Text>
        )}
      </ScrollView>
    </View>
  );
}

const useEstilos = crearEstilos(({ colores }) => ({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  contenido: { padding: espacio.m, paddingTop: espacio.s, paddingBottom: espacioBarra, gap: espacio.l },
  mensaje: { margin: espacio.l },
}));

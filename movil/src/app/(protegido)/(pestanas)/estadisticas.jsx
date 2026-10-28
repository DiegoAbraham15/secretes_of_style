import { useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { ActivityIndicator, ScrollView, Text } from 'react-native';

import { obtenerEstadisticas } from '../../../api';
import { ETIQUETA_CATEGORIA, ETIQUETA_COLOR, HEX_COLOR, NIVELES_ABRIGO } from '../../../catalogos';
import { GraficaBarras, Hallazgo, ResumenBento } from '../../../componentes/Graficas';
import { crearEstilos, espacio, useTema } from '../../../tema';

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

  if (error) return <Text style={[texto.cuerpo, estilos.mensaje, { color: colores.error }]}>{error}</Text>;
  if (!datos) return <ActivityIndicator color={colores.primario} style={{ marginTop: espacio.xxl }} />;

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
    color: HEX_COLOR[color], // la barra se pinta del color de la prenda
  }));
  const porNivel = NIVELES_ABRIGO.map((nivel) => ({
    etiqueta: nivel.etiqueta,
    valor: datos.por_nivel_abrigo[nivel.valor],
  }));

  return (
    <ScrollView style={estilos.pantalla} contentContainerStyle={estilos.contenido}>
      <ResumenBento
        total={indicadores.total_prendas}
        color={colorMasUsado && { etiqueta: ETIQUETA_COLOR[colorMasUsado], hex: HEX_COLOR[colorMasUsado] }}
        impermeables={indicadores.impermeables}
        guardados={indicadores.atuendos_guardados}
      />

      <Hallazgo>{datos.hallazgo}</Hallazgo>

      {indicadores.total_prendas > 0 ? (
        <>
          <GraficaBarras
            titulo="Prendas por categoría"
            pregunta="¿Qué tipo de prenda tienes más?"
            datos={porCategoria}
            unidad="prendas"
            repeticion={repeticion}
          />
          <GraficaBarras
            titulo="Colores de tu armario"
            pregunta="¿De qué color son tus prendas? Solo aparecen los colores que tienes."
            datos={porColor}
            unidad="prendas"
            repeticion={repeticion}
          />
          <GraficaBarras
            titulo="Nivel de abrigo"
            pregunta="¿Para qué clima está lista tu ropa? 1 es para calor y 5 para frío."
            datos={porNivel}
            unidad="prendas"
            repeticion={repeticion}
          />
        </>
      ) : (
        <Text style={[texto.cuerpo, { color: colores.textoSecundario }]}>
          Las gráficas aparecen cuando agregas tu primera prenda en la pestaña Armario.
        </Text>
      )}
    </ScrollView>
  );
}

const useEstilos = crearEstilos(({ colores }) => ({
  pantalla: { flex: 1, backgroundColor: colores.fondo },
  contenido: { padding: espacio.m, paddingBottom: espacio.xxl },
  mensaje: { margin: espacio.l },
}));

// El clima actual y lo que conviene ponerse según lo que deduce la lógica.
import { Text, View } from 'react-native';

import {
  IconoDespejado,
  IconoLluvia,
  IconoNiebla,
  IconoNieve,
  IconoNublado,
  IconoTormenta,
  IconoUbicacion,
} from '../iconos';
import { crearEstilos, espacio, fuentes, radio, tamañoIcono, useTema } from '../tema';

// Las descripciones que manda el servidor (clima.py) con su ícono.
export const ICONO_CLIMA = {
  Despejado: IconoDespejado,
  Nublado: IconoNublado,
  Niebla: IconoNiebla,
  Lluvia: IconoLluvia,
  Chubascos: IconoLluvia,
  Nieve: IconoNieve,
  Tormenta: IconoTormenta,
};

export function TarjetaClima({ clima, ubicacionAproximada }) {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const minutos = clima.minutos_desactualizado; // solo llega si el servidor no pudo consultar el clima
  const antiguedad = minutos < 60 ? `${minutos} min` : `${Math.round(minutos / 60)} h`;
  // Las reglas solo deducen algo con frío o lluvia; el calor se explica aquí.
  const consejos = [
    ...clima.deducciones,
    ...(clima.hechos.includes('calor') ? ['Hace calor: elige prendas frescas y colores claros'] : []),
  ];
  const Icono = ICONO_CLIMA[clima.descripcion] ?? IconoNublado;

  return (
    <View style={estilos.tarjeta}>
      <View style={estilos.fila}>
        <View style={estilos.cuadroIcono}>
          <Icono color={colores.primario} size={tamañoIcono.m} />
        </View>
        <View style={{ flex: 1, minWidth: 0 }}>
          <Text style={estilos.descripcion}>{clima.descripcion}</Text>
          <Text style={texto.nota}>
            Se siente de {Math.round(clima.sensacion_termica_c)} °C, lluvia {clima.probabilidad_lluvia} %
          </Text>
        </View>
        <Text
          style={estilos.temperatura}
          accessibilityLabel={`${Math.round(clima.temperatura_c)} grados, ${clima.descripcion}`}>
          {Math.round(clima.temperatura_c)}°
        </Text>
      </View>

      {minutos != null && (
        <Text style={[texto.nota, { marginTop: espacio.s }]}>
          No se pudo consultar el clima ahora: se muestra el de hace {antiguedad}.
        </Text>
      )}

      <View style={estilos.consejos}>
        {(consejos.length > 0 ? consejos : ['Clima templado y sin lluvia']).map((consejo) => (
          <View key={consejo} style={estilos.consejo}>
            <View style={estilos.punto} />
            <Text style={[texto.detalle, { flex: 1, color: colores.texto }]}>{consejo}</Text>
          </View>
        ))}
      </View>

      {ubicacionAproximada && (
        <View style={estilos.filaUbicacion}>
          <IconoUbicacion color={colores.textoSecundario} size={tamañoIcono.s} />
          <Text style={[texto.nota, { flex: 1 }]}>Sin permiso de ubicación: se usa el clima de Ciudad de México.</Text>
        </View>
      )}
    </View>
  );
}

const useEstilos = crearEstilos(({ colores }) => ({
  tarjeta: { padding: espacio.m, borderRadius: radio.l, backgroundColor: colores.superficieSuave },
  fila: { flexDirection: 'row', alignItems: 'center', gap: espacio.s + 4 },
  cuadroIcono: {
    width: 44,
    height: 44,
    borderRadius: radio.m,
    backgroundColor: colores.primarioSuave,
    alignItems: 'center',
    justifyContent: 'center',
  },
  descripcion: { fontFamily: fuentes.negrita, fontSize: 15, lineHeight: 20, color: colores.texto },
  temperatura: { fontFamily: fuentes.display, fontSize: 40, lineHeight: 48, color: colores.texto },
  // Los consejos van debajo de una línea fina, cada uno con su punto.
  consejos: { marginTop: espacio.s + 4, paddingTop: espacio.s + 4, borderTopWidth: 1, borderTopColor: colores.borde, gap: espacio.xs },
  consejo: { flexDirection: 'row', alignItems: 'center', gap: espacio.s },
  punto: { width: 6, height: 6, borderRadius: 3, backgroundColor: colores.primario },
  filaUbicacion: { flexDirection: 'row', alignItems: 'center', gap: espacio.s, marginTop: espacio.s + 4 },
}));

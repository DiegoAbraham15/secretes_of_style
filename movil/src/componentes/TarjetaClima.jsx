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
const ICONO_CLIMA = {
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
        <Text
          style={estilos.temperatura}
          accessibilityLabel={`${Math.round(clima.temperatura_c)} grados, ${clima.descripcion}`}>
          {Math.round(clima.temperatura_c)}°
        </Text>
        <View style={{ flex: 1 }}>
          <View style={estilos.filaDescripcion}>
            <View style={estilos.circuloIcono}>
              <Icono color={colores.primario} size={tamañoIcono.m} />
            </View>
            <Text style={texto.subtitulo}>{clima.descripcion}</Text>
          </View>
          <Text style={texto.detalle}>
            Se siente de {Math.round(clima.sensacion_termica_c)} °C · lluvia {clima.probabilidad_lluvia} %
          </Text>
        </View>
      </View>

      {minutos != null && (
        <Text style={[texto.nota, { marginTop: espacio.s }]}>
          No se pudo consultar el clima ahora: se muestra el de hace {antiguedad}.
        </Text>
      )}

      <View style={estilos.consejos}>
        <Text style={[texto.antetitulo, { color: colores.primario }]}>Para hoy</Text>
        {consejos.length === 0 ? (
          <Text style={[texto.cuerpo, estilos.consejo]}>Clima templado y sin lluvia</Text>
        ) : (
          consejos.map((consejo) => (
            <Text key={consejo} style={[texto.cuerpo, estilos.consejo]}>
              {consejo}
            </Text>
          ))
        )}
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

const useEstilos = crearEstilos(({ colores, tarjeta }) => ({
  tarjeta: { ...tarjeta, padding: espacio.m },
  fila: { flexDirection: 'row', alignItems: 'center', gap: espacio.m },
  temperatura: { fontFamily: fuentes.negra, fontSize: 64, lineHeight: 68, letterSpacing: -3, color: colores.texto },
  filaDescripcion: { flexDirection: 'row', alignItems: 'center', gap: espacio.s, marginBottom: 2 },
  circuloIcono: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colores.primarioSuave,
    alignItems: 'center',
    justifyContent: 'center',
  },
  // Los consejos van en un bloque suave dentro de la tarjeta (Soft UI: capas en vez de líneas).
  consejos: {
    marginTop: espacio.m,
    padding: espacio.m,
    borderRadius: radio.l,
    backgroundColor: colores.superficieSuave,
  },
  consejo: { marginTop: espacio.xs },
  filaUbicacion: { flexDirection: 'row', alignItems: 'center', gap: espacio.s, marginTop: espacio.m },
}));

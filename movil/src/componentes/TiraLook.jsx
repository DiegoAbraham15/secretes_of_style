// Un look en chiquito: las fotos de sus prendas en una tira, de arriba abajo como se usan. Lo usan las cápsulas y el
// reto de la semana. prendas: la lista completa de prendas del look. titulo: arriba de la tira (p. ej. "Look 3").
// children: acciones debajo (p. ej. "Me lo puse hoy").
import { Text, View } from 'react-native';

import { nombreConColor, ORDEN_CUERPO } from '../catalogos';
import { crearEstilos, espacio, fuentes, radio, useTema } from '../tema';
import { FotoPrenda } from './FotoPrenda';

export function TiraLook({ prendas, titulo, ancho = 200, children }) {
  const { texto } = useTema();
  const estilos = useEstilos();
  const ordenadas = [...prendas].sort((a, b) => ORDEN_CUERPO.indexOf(a.categoria) - ORDEN_CUERPO.indexOf(b.categoria));
  return (
    <View style={[estilos.tarjeta, { width: ancho }]} accessible={!children} accessibilityLabel={`${titulo ?? 'Look'}: ${ordenadas.map(nombreConColor).join(', ')}`}>
      {titulo ? <Text style={estilos.titulo}>{titulo}</Text> : null}
      <View style={estilos.fotos}>
        {ordenadas.map((prenda) => (
          <FotoPrenda key={prenda.id} prenda={prenda} style={estilos.foto} />
        ))}
      </View>
      <Text style={texto.nota} numberOfLines={2}>
        {ordenadas.map(nombreConColor).join(' · ')}
      </Text>
      {children}
    </View>
  );
}

const useEstilos = crearEstilos(({ colores, tarjeta }) => ({
  tarjeta: { ...tarjeta, padding: espacio.s + 4, gap: espacio.s },
  titulo: { fontFamily: fuentes.displayItalica, fontSize: 20, lineHeight: 26, color: colores.texto },
  fotos: { flexDirection: 'row', gap: 2, borderRadius: radio.m, overflow: 'hidden', backgroundColor: colores.borde },
  foto: { flex: 1, aspectRatio: 3 / 4, backgroundColor: colores.superficieSuave },
}));

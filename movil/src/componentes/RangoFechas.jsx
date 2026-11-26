// Calendario para elegir un rango de fechas (del 18 al 25), en lugar de contar días: se toca el primer día y luego
// el último. Solo se pueden elegir los días con pronóstico confiable (hoy y los 15 siguientes, que es lo que
// entrega Open-Meteo). Con un toque en un solo día, el rango es de ese día.
// El servidor sigue recibiendo "salida" (en cuántos días sale) y "dias"; rangoADias() los calcula del rango.
import { useState } from 'react';
import { Pressable, Text, View } from 'react-native';

import { IconoIr } from '../iconos';
import { crearEstilos, espacio, fuentes, presionado, radio, tactil, tamañoIcono, useTema } from '../tema';

export const DIAS_DE_PRONOSTICO = 16; // hoy y los 15 días siguientes
const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre',
  'noviembre', 'diciembre'];
const INICIALES_SEMANA = ['L', 'M', 'M', 'J', 'V', 'S', 'D'];
const DIA_MS = 24 * 60 * 60 * 1000;

const dos = (n) => String(n).padStart(2, '0');
const aTexto = (f) => `${f.getFullYear()}-${dos(f.getMonth() + 1)}-${dos(f.getDate())}`; // "2026-12-18"
const aFecha = (texto) => {
  const [a, m, d] = texto.split('-').map(Number);
  return new Date(a, m - 1, d);
};
const hoy = () => {
  const f = new Date();
  return new Date(f.getFullYear(), f.getMonth(), f.getDate());
};
// Días entre dos fechas; se redondea porque un cambio de horario deja días de 23 o 25 horas.
const diferenciaEnDias = (desde, hasta) => Math.round((hasta - desde) / DIA_MS);
const sumarDias = (fecha, n) => new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate() + n);

/** El rango que se muestra al abrir la pantalla: sale en `salida` días y dura `dias` días. */
export function rangoInicial(salida = 1, dias = 3) {
  const inicio = sumarDias(hoy(), salida);
  return { inicio: aTexto(inicio), fin: aTexto(sumarDias(inicio, dias - 1)) };
}

/** De un rango a lo que pide el servidor: en cuántos días sale (0 = hoy) y cuántos días dura (con el último). */
export function rangoADias({ inicio, fin }) {
  const salida = diferenciaEnDias(hoy(), aFecha(inicio));
  return { salida, dias: diferenciaEnDias(aFecha(inicio), aFecha(fin ?? inicio)) + 1 };
}

/** "18 al 25 de diciembre" (o "28 de diciembre al 3 de enero" si cambia de mes). */
export function textoDelRango({ inicio, fin }) {
  const a = aFecha(inicio);
  const b = aFecha(fin ?? inicio);
  if (diferenciaEnDias(a, b) === 0) return `${a.getDate()} de ${MESES[a.getMonth()]}`;
  if (a.getMonth() === b.getMonth()) return `${a.getDate()} al ${b.getDate()} de ${MESES[b.getMonth()]}`;
  return `${a.getDate()} de ${MESES[a.getMonth()]} al ${b.getDate()} de ${MESES[b.getMonth()]}`;
}

const DIAS_SEMANA = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];

/** "2026-12-01" → "Martes 1 de diciembre" (a mano: no depende del idioma del teléfono). */
export function fechaLarga(iso) {
  const fecha = aFecha(iso);
  const semana = DIAS_SEMANA[fecha.getDay()];
  return `${semana[0].toUpperCase()}${semana.slice(1)} ${fecha.getDate()} de ${MESES[fecha.getMonth()]}`;
}

export function RangoFechas({ valor, alCambiar }) {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const primerDia = hoy();
  const ultimoDia = sumarDias(primerDia, DIAS_DE_PRONOSTICO - 1);
  const [mes, establecerMes] = useState(() => {
    const inicio = aFecha(valor.inicio);
    return new Date(inicio.getFullYear(), inicio.getMonth(), 1);
  });

  const hayAnterior = mes > new Date(primerDia.getFullYear(), primerDia.getMonth(), 1);
  const haySiguiente = mes < new Date(ultimoDia.getFullYear(), ultimoDia.getMonth(), 1);
  const irAMes = (cambio) => establecerMes(new Date(mes.getFullYear(), mes.getMonth() + cambio, 1));

  // Casillas del mes: huecos hasta el día de la semana del 1 (la semana empieza en lunes) y luego los días.
  const huecos = (new Date(mes.getFullYear(), mes.getMonth(), 1).getDay() + 6) % 7;
  const diasDelMes = new Date(mes.getFullYear(), mes.getMonth() + 1, 0).getDate();
  const casillas = [...Array(huecos).fill(null), ...Array.from({ length: diasDelMes }, (_, i) => i + 1)];
  while (casillas.length % 7 !== 0) casillas.push(null);
  const semanas = Array.from({ length: casillas.length / 7 }, (_, i) => casillas.slice(i * 7, i * 7 + 7));

  // Primer toque: inicio del rango. Segundo toque (después del inicio): fin. Otro toque: empieza de nuevo.
  function tocar(fecha) {
    const elegido = aTexto(fecha);
    const hayRango = valor.fin && valor.fin !== valor.inicio; // ya hay varios días elegidos
    if (hayRango || elegido < valor.inicio) alCambiar({ inicio: elegido, fin: elegido }); // empieza de nuevo
    else alCambiar({ inicio: valor.inicio, fin: elegido }); // con un solo día elegido, el toque marca el último
  }

  const { dias } = rangoADias(valor);
  return (
    <View style={estilos.contenedor} accessibilityLabel="Calendario para elegir las fechas del viaje">
      <View style={estilos.cabecera}>
        <Pressable
          onPress={() => irAMes(-1)}
          disabled={!hayAnterior}
          accessibilityRole="button"
          accessibilityLabel="Mes anterior"
          style={({ pressed }) => [estilos.flecha, !hayAnterior && { opacity: 0.3 }, pressed && presionado]}>
          <IconoIr color={colores.texto} size={tamañoIcono.s} style={{ transform: [{ rotate: '180deg' }] }} />
        </Pressable>
        <Text style={texto.cuerpoFuerte} accessibilityRole="header">
          {MESES[mes.getMonth()][0].toUpperCase() + MESES[mes.getMonth()].slice(1)} {mes.getFullYear()}
        </Text>
        <Pressable
          onPress={() => irAMes(1)}
          disabled={!haySiguiente}
          accessibilityRole="button"
          accessibilityLabel="Mes siguiente"
          style={({ pressed }) => [estilos.flecha, !haySiguiente && { opacity: 0.3 }, pressed && presionado]}>
          <IconoIr color={colores.texto} size={tamañoIcono.s} />
        </Pressable>
      </View>

      <View style={estilos.semana}>
        {INICIALES_SEMANA.map((letra, i) => (
          <Text key={i} style={estilos.inicial} importantForAccessibility="no">
            {letra}
          </Text>
        ))}
      </View>

      {semanas.map((semana, s) => (
        <View key={s} style={estilos.semana}>
          {semana.map((dia, i) => {
            if (!dia) return <View key={i} style={estilos.casilla} />;
            const fecha = new Date(mes.getFullYear(), mes.getMonth(), dia);
            const textoFecha = aTexto(fecha);
            const permitido = fecha >= primerDia && fecha <= ultimoDia;
            const esInicio = textoFecha === valor.inicio;
            const esFin = textoFecha === (valor.fin ?? valor.inicio);
            const dentro = textoFecha > valor.inicio && textoFecha < (valor.fin ?? valor.inicio);
            const elegido = esInicio || esFin;
            return (
              <View key={i} style={[estilos.casilla, dentro && estilos.dentro, esInicio && esFin === false && estilos.mitadDerecha,
                esFin && !esInicio && estilos.mitadIzquierda]}>
                <Pressable
                  disabled={!permitido}
                  onPress={() => tocar(fecha)}
                  accessibilityRole="button"
                  accessibilityLabel={`${dia} de ${MESES[mes.getMonth()]}`}
                  accessibilityState={{ selected: elegido, disabled: !permitido }}
                  style={({ pressed }) => [estilos.dia, elegido && estilos.diaElegido, pressed && permitido && presionado]}>
                  <Text style={[estilos.numero, !permitido && estilos.numeroApagado, elegido && estilos.numeroElegido]}>{dia}</Text>
                </Pressable>
              </View>
            );
          })}
        </View>
      ))}

      <Text style={[texto.detalle, { marginTop: espacio.s }]} accessibilityLiveRegion="polite">
        Del {textoDelRango(valor)} · {dias} {dias === 1 ? 'día' : 'días'}
      </Text>
      <Text style={texto.nota}>Toca el primer día y luego el último. El pronóstico alcanza hasta 16 días.</Text>
    </View>
  );
}

const useEstilos = crearEstilos(({ colores }) => ({
  contenedor: { gap: espacio.xs, padding: espacio.m, borderRadius: radio.m, backgroundColor: colores.superficieSuave },
  cabecera: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: espacio.s },
  flecha: { width: tactil, height: tactil, alignItems: 'center', justifyContent: 'center' },
  semana: { flexDirection: 'row' },
  inicial: { flex: 1, textAlign: 'center', fontFamily: fuentes.media, fontSize: 12, color: colores.textoSecundario, paddingBottom: espacio.xs },
  casilla: { flex: 1, height: 44, alignItems: 'center', justifyContent: 'center' },
  dentro: { backgroundColor: colores.primarioSuave },
  mitadDerecha: { backgroundColor: colores.primarioSuave, borderTopLeftRadius: 22, borderBottomLeftRadius: 22 },
  mitadIzquierda: { backgroundColor: colores.primarioSuave, borderTopRightRadius: 22, borderBottomRightRadius: 22 },
  dia: { width: 44, height: 44, borderRadius: 22, alignItems: 'center', justifyContent: 'center' },
  diaElegido: { backgroundColor: colores.primario },
  numero: { fontFamily: fuentes.media, fontSize: 15, color: colores.texto },
  numeroApagado: { color: colores.textoSecundario, opacity: 0.4 },
  numeroElegido: { color: colores.sobrePrimario, fontFamily: fuentes.negrita },
}));

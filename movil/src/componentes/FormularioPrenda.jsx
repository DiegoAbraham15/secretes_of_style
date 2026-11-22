// Los datos de una prenda, en un solo formulario que usan Nueva prenda, Varias prendas, Importar y el detalle.
// useFormularioPrenda guarda los valores y qué campos tocó la persona: cuando llega lo que propone la IA
// (aplicarPropuesta), solo llena los que siguen intactos. Así la IA nunca borra una corrección hecha a mano.
// compacto: muestra lo esencial (categoría, color, abrigo y temporada) y el resto se abre con "Más datos".
// conCompra: agrega precio y fecha de compra (sirven para el costo por puesta en Estadísticas).
import { useCallback, useRef, useState } from 'react';
import { Pressable, Switch, Text, View } from 'react-native';

import { CATEGORIAS, COLORES, ESTAMPADOS, ESTILOS, NIVELES_ABRIGO, TEMPORADAS } from '../catalogos';
import { IconoAbrir, IconoCerrar } from '../iconos';
import { crearEstilos, espacio, fuentes, presionado, tactil, useTema } from '../tema';
import { Campo } from './Campo';
import { Selector } from './Selector';

const VACIOS = {
  categoria: null,
  subcategoria: '',
  color_principal: null,
  nivel_abrigo: null,
  impermeable: false,
  estampado: 'liso',
  estilo: 'casual',
  temporada: null,
  precio_compra: '',
  fecha_adquisicion: '',
};
const CAMPOS = Object.keys(VACIOS);

// La temporada que se propone con el nivel de abrigo (la misma regla que el servidor).
export const temporadaDe = (nivel) =>
  !nivel ? null : nivel <= 2 ? 'primavera_verano' : nivel === 3 ? 'todo_el_ano' : 'otono_invierno';

// De una prenda o una propuesta de la IA a los valores del formulario (precio y fecha como texto).
export function valoresDe(origen = {}) {
  const valores = { ...VACIOS };
  for (const campo of CAMPOS) {
    if (origen[campo] !== undefined && origen[campo] !== null) valores[campo] = origen[campo];
  }
  valores.precio_compra = origen.precio_compra != null ? String(origen.precio_compra) : '';
  valores.subcategoria = origen.subcategoria ?? '';
  return valores;
}

// Lo que se manda a la API: el precio como número, y lo vacío como null.
export function datosDe(valores) {
  const precio = Number(String(valores.precio_compra).replace(',', '.'));
  return {
    ...valores,
    subcategoria: valores.subcategoria.trim(),
    precio_compra: valores.precio_compra === '' || Number.isNaN(precio) ? null : precio,
    fecha_adquisicion: valores.fecha_adquisicion.trim() || null,
  };
}

// Lo mínimo para guardar una prenda.
export const faltaAlgo = (valores) => !valores.categoria || !valores.color_principal || !valores.nivel_abrigo;

export function useFormularioPrenda(inicial) {
  const [valores, establecerValores] = useState(() => valoresDe(inicial));
  const tocados = useRef(new Set());

  const cambiar = useCallback((campo, valor) => {
    tocados.current.add(campo);
    establecerValores((actuales) => {
      const nuevos = { ...actuales, [campo]: valor };
      // Si cambia el abrigo y la temporada nadie la tocó, se propone sola.
      if (campo === 'nivel_abrigo' && !tocados.current.has('temporada')) nuevos.temporada = temporadaDe(valor);
      return nuevos;
    });
  }, []);

  // Lo que propone la IA llena solo los campos que la persona no ha tocado.
  const aplicarPropuesta = useCallback((propuesta = {}) => {
    establecerValores((actuales) => {
      const propuestos = valoresDe({ ...actuales, ...propuesta });
      const nuevos = { ...actuales };
      for (const campo of CAMPOS) {
        if (!tocados.current.has(campo) && propuesta[campo] != null) nuevos[campo] = propuestos[campo];
      }
      if (!nuevos.temporada) nuevos.temporada = temporadaDe(nuevos.nivel_abrigo);
      return nuevos;
    });
  }, []);

  const reiniciar = useCallback((nuevos = {}) => {
    tocados.current = new Set();
    establecerValores(valoresDe(nuevos));
  }, []);

  return { valores, cambiar, aplicarPropuesta, reiniciar, hayCambios: () => tocados.current.size > 0 };
}

export function FormularioPrenda({ valores, alCambiar, compacto = false, conCompra = false }) {
  const { colores, texto } = useTema();
  const estilos = useEstilos();
  const [abierto, establecerAbierto] = useState(!compacto);
  const enLinea = compacto; // en las tarjetas, las opciones se deslizan de lado para no ocupar media pantalla
  const separado = compacto ? { marginBottom: espacio.s + 4 } : undefined;

  return (
    <View>
      <Selector titulo="Categoría" opciones={CATEGORIAS} seleccionado={valores.categoria} alCambiar={(v) => alCambiar('categoria', v)} enLinea={enLinea} estilo={separado} />
      <Selector titulo="Color principal" opciones={COLORES} seleccionado={valores.color_principal} alCambiar={(v) => alCambiar('color_principal', v)} enLinea={enLinea} estilo={separado} />
      <Selector titulo="Nivel de abrigo" opciones={NIVELES_ABRIGO} seleccionado={valores.nivel_abrigo} alCambiar={(v) => alCambiar('nivel_abrigo', v)} enLinea={enLinea} estilo={separado} />
      <Selector titulo="Temporada" opciones={TEMPORADAS} seleccionado={valores.temporada} alCambiar={(v) => alCambiar('temporada', v)} enLinea={enLinea} estilo={separado} />

      {compacto && (
        <Pressable
          onPress={() => establecerAbierto(!abierto)}
          accessibilityRole="button"
          accessibilityState={{ expanded: abierto }}
          style={({ pressed }) => [estilos.mas, pressed && presionado]}>
          <Text style={estilos.textoMas}>{abierto ? 'Menos datos' : 'Más datos: tipo, estampado, estilo…'}</Text>
          {abierto ? (
            <IconoCerrar color={colores.primario} size={14} weight="bold" />
          ) : (
            <IconoAbrir color={colores.primario} size={14} weight="bold" />
          )}
        </Pressable>
      )}

      {abierto && (
        <>
          <Text style={texto.antetitulo}>Tipo de prenda (opcional)</Text>
          <Campo
            value={valores.subcategoria}
            onChangeText={(v) => alCambiar('subcategoria', v)}
            placeholder="Blusa, jeans, botines"
            maxLength={60}
            accessibilityLabel="Tipo de prenda, opcional"
            estilo={estilos.campo}
          />
          <Selector titulo="Estampado" opciones={ESTAMPADOS} seleccionado={valores.estampado} alCambiar={(v) => alCambiar('estampado', v)} enLinea={enLinea} estilo={separado} />
          <Selector titulo="Estilo" opciones={ESTILOS} seleccionado={valores.estilo} alCambiar={(v) => alCambiar('estilo', v)} enLinea={enLinea} estilo={separado} />
          <View style={estilos.interruptor}>
            <View style={{ flex: 1 }}>
              <Text style={texto.cuerpoFuerte}>Impermeable</Text>
              <Text style={texto.detalle}>Resiste la lluvia</Text>
            </View>
            <Switch
              value={valores.impermeable}
              onValueChange={(v) => alCambiar('impermeable', v)}
              accessibilityLabel="Impermeable"
              trackColor={{ true: colores.primario, false: colores.bordeControl }}
            />
          </View>
        </>
      )}

      {conCompra && abierto && (
        <View style={estilos.compra}>
          <View style={{ flex: 1 }}>
            <Text style={texto.antetitulo}>Precio (opcional)</Text>
            <Campo
              value={valores.precio_compra}
              onChangeText={(v) => alCambiar('precio_compra', v.replace(/[^0-9.,]/g, ''))}
              placeholder="$ 0.00"
              keyboardType="decimal-pad"
              accessibilityLabel="Precio de compra, opcional"
              estilo={estilos.campo}
            />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={texto.antetitulo}>Fecha de compra</Text>
            <Campo
              value={valores.fecha_adquisicion}
              onChangeText={(v) => alCambiar('fecha_adquisicion', v.replace(/[^0-9-]/g, '').slice(0, 10))}
              placeholder="AAAA-MM-DD"
              keyboardType="numbers-and-punctuation"
              accessibilityLabel="Fecha de compra, año-mes-día, opcional"
              estilo={estilos.campo}
            />
          </View>
        </View>
      )}
    </View>
  );
}

const useEstilos = crearEstilos(({ colores }) => ({
  mas: { flexDirection: 'row', alignItems: 'center', gap: 4, minHeight: tactil - 8, alignSelf: 'flex-start', marginBottom: espacio.s },
  textoMas: { fontFamily: fuentes.media, fontSize: 14, color: colores.primario },
  campo: { marginTop: espacio.s, marginBottom: espacio.l },
  interruptor: { flexDirection: 'row', alignItems: 'center', minHeight: tactil, marginBottom: espacio.l },
  compra: { flexDirection: 'row', gap: espacio.s + 4 },
}));

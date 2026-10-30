// Campo de texto en caja con un ícono al inicio. Al escribir en él, el borde y el fondo toman el color
// primario para que se note dónde está el cursor. derecha: algo al final de la caja (p. ej. ver contraseña).
// El resto de las props van al TextInput.
import { useState } from 'react';
import { TextInput, View } from 'react-native';

import { crearEstilos, espacio, fuentes, radio, tactil, tamañoIcono, useTema } from '../tema';

export function Campo({ icono: Icono, derecha, estilo, ...props }) {
  const { colores, oscuro } = useTema();
  const estilos = useEstilos();
  const [activo, establecerActivo] = useState(false);

  return (
    <View style={[estilos.caja, activo && estilos.cajaActiva, estilo]}>
      {Icono && <Icono color={activo ? colores.primario : colores.textoSecundario} size={tamañoIcono.s} />}
      <TextInput
        placeholderTextColor={colores.textoSecundario}
        keyboardAppearance={oscuro ? 'dark' : 'light'}
        {...props}
        onFocus={() => establecerActivo(true)}
        onBlur={() => establecerActivo(false)}
        style={estilos.texto}
      />
      {derecha}
    </View>
  );
}

const useEstilos = crearEstilos(({ colores }) => ({
  caja: {
    minHeight: tactil + 4,
    flexDirection: 'row',
    alignItems: 'center',
    gap: espacio.s + 4,
    paddingHorizontal: espacio.m,
    borderRadius: radio.l,
    borderWidth: 1.5,
    borderColor: colores.borde,
    backgroundColor: colores.superficieSuave,
  },
  cajaActiva: { borderColor: colores.primario, backgroundColor: colores.primarioSuave },
  texto: { flex: 1, minWidth: 0, minHeight: tactil, fontFamily: fuentes.regular, fontSize: 16, color: colores.texto },
}));

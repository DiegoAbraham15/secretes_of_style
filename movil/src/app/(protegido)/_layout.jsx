import { Stack } from 'expo-router';

import { fuentes, useTema } from '../../tema';

export default function LayoutProtegido() {
  const { colores } = useTema();

  // Las pantallas que se abren encima de las pestañas, como hoja que se desliza hacia abajo para cerrarla.
  const modal = {
    presentation: 'modal',
    headerTintColor: colores.primario,
    headerTitleStyle: { fontFamily: fuentes.negrita, fontSize: 18, color: colores.texto },
    headerStyle: { backgroundColor: colores.fondo },
    headerShadowVisible: false,
    contentStyle: { backgroundColor: colores.fondo },
  };

  return (
    <Stack screenOptions={{ contentStyle: { backgroundColor: colores.fondo } }}>
      <Stack.Screen name="(pestanas)" options={{ headerShown: false }} />
      <Stack.Screen name="nueva-prenda" options={{ ...modal, title: 'Nueva prenda' }} />
      <Stack.Screen name="prenda/[id]" options={{ ...modal, title: 'Tu prenda' }} />
    </Stack>
  );
}

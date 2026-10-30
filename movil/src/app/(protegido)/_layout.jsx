import { Stack } from 'expo-router';
import { ActivityIndicator, View } from 'react-native';

import { useSesion } from '../../sesion';
import { fuentes, useTema } from '../../tema';

export default function LayoutProtegido() {
  const { colores } = useTema();
  const { cuestionarioListo } = useSesion();

  // Las pantallas que se abren encima de las pestañas, como hoja que se desliza hacia abajo para cerrarla.
  const modal = {
    presentation: 'modal',
    headerTintColor: colores.primario,
    headerTitleStyle: { fontFamily: fuentes.display, fontSize: 22, color: colores.texto },
    headerStyle: { backgroundColor: colores.fondo },
    headerShadowVisible: false,
    contentStyle: { backgroundColor: colores.fondo },
  };

  // Mientras se sabe si falta el cuestionario, para no enseñar el armario un instante.
  if (cuestionarioListo === null) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', backgroundColor: colores.fondo }}>
        <ActivityIndicator color={colores.primario} />
      </View>
    );
  }

  return (
    <Stack screenOptions={{ contentStyle: { backgroundColor: colores.fondo } }}>
      <Stack.Protected guard={!cuestionarioListo}>
        <Stack.Screen name="cuestionario" options={{ headerShown: false }} />
      </Stack.Protected>
      <Stack.Protected guard={cuestionarioListo}>
        <Stack.Screen name="(pestanas)" options={{ headerShown: false }} />
        <Stack.Screen name="nueva-prenda" options={{ ...modal, title: 'Nueva prenda' }} />
        <Stack.Screen name="prenda/[id]" options={{ ...modal, title: 'Tu prenda' }} />
      </Stack.Protected>
    </Stack>
  );
}

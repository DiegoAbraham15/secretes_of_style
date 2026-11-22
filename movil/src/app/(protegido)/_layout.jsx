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
    headerTitleStyle: { fontFamily: fuentes.negrita, fontSize: 18, color: colores.texto },
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
        <Stack.Screen name="generador" options={{ headerShown: false }} />
        <Stack.Screen name="tiendas" options={{ headerShown: false }} />
        <Stack.Screen name="estadisticas" options={{ headerShown: false }} />
        <Stack.Screen name="nueva-prenda" options={{ ...modal, title: 'Nueva prenda' }} />
        <Stack.Screen name="carga-masiva" options={{ ...modal, title: 'Varias prendas' }} />
        <Stack.Screen name="importar" options={{ ...modal, title: 'Desde un link' }} />
        <Stack.Screen name="prenda/[id]" options={{ ...modal, title: 'Tu prenda' }} />
        <Stack.Screen name="tu-foto" options={{ ...modal, title: 'Tu foto' }} />
        <Stack.Screen name="mis-gustos" options={{ ...modal, title: 'Tus gustos' }} />
        <Stack.Screen name="colorimetria" options={{ ...modal, title: 'Tu colorimetría' }} />
        <Stack.Screen name="viaje" options={{ ...modal, title: 'Tu viaje' }} />
        <Stack.Screen name="capsula" options={{ ...modal, title: 'Cápsula de ropa' }} />
        <Stack.Screen name="capsulas/[id]" options={{ ...modal, title: 'Tu cápsula' }} />
        <Stack.Screen name="vale-la-pena" options={{ ...modal, title: '¿Vale la pena?' }} />
        <Stack.Screen name="vista-previa" options={{ ...modal, title: 'Vista previa' }} />
      </Stack.Protected>
    </Stack>
  );
}

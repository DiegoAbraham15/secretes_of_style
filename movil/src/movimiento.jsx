// Movimiento de la app (estilo Motion-Driven de la skill): cascada al aparecer, escala al presionar
// y vibración en las confirmaciones. Todo respeta "Reducir movimiento" del teléfono.
import * as Haptics from 'expo-haptics';
import { useEffect, useState } from 'react';
import { AccessibilityInfo, Animated, Easing, Platform, Pressable } from 'react-native';

import { duracion, presionado } from './tema';

// true si el usuario activó "Reducir movimiento"; se actualiza si lo cambia con la app abierta.
export function useReducirMovimiento() {
  const [reducir, establecerReducir] = useState(false);
  useEffect(() => {
    AccessibilityInfo.isReduceMotionEnabled().then(establecerReducir);
    const suscripcion = AccessibilityInfo.addEventListener('reduceMotionChanged', establecerReducir);
    return () => suscripcion.remove();
  }, []);
  return reducir;
}

// Aparece subiendo 12 px y con fundido; indice escalona la entrada de cada elemento de una lista.
export function Aparecer({ indice = 0, estilo, children }) {
  const reducir = useReducirMovimiento();
  const [avance] = useState(() => new Animated.Value(0));

  useEffect(() => {
    if (reducir) {
      avance.setValue(1);
      return undefined;
    }
    const animacion = Animated.timing(avance, {
      toValue: 1,
      duration: duracion.lenta,
      delay: Math.min(indice, 8) * duracion.escalonado, // después del 8.º ya no espera más
      easing: Easing.out(Easing.cubic), // desacelera al llegar
      useNativeDriver: true,
    });
    animacion.start();
    return () => animacion.stop();
  }, [avance, indice, reducir]);

  const subir = avance.interpolate({ inputRange: [0, 1], outputRange: [12, 0] });
  return (
    <Animated.View style={[estilo, { opacity: avance, transform: [{ translateY: subir }] }]}>{children}</Animated.View>
  );
}

// Pressable que se encoge un poco con un resorte al tocarlo (0.97) y regresa al soltar.
// estiloExterno: posición y tamaño en el diseño (lo que antes iba en el Pressable, p. ej. position absolute).
export function Presionable({ estiloExterno, style, escala = 0.97, onPressIn, onPressOut, children, ...props }) {
  const reducir = useReducirMovimiento();
  const [valor] = useState(() => new Animated.Value(1));
  const animar = (destino) =>
    Animated.spring(valor, { toValue: destino, speed: 40, bounciness: 4, useNativeDriver: true }).start();

  return (
    <Animated.View style={[estiloExterno, { transform: [{ scale: valor }] }]}>
      <Pressable
        {...props}
        onPressIn={(evento) => {
          if (!reducir) animar(escala);
          onPressIn?.(evento);
        }}
        onPressOut={(evento) => {
          if (!reducir) animar(1);
          onPressOut?.(evento);
        }}
        style={(estado) => [typeof style === 'function' ? style(estado) : style, reducir && estado.pressed && presionado]}>
        {children}
      </Pressable>
    </Animated.View>
  );
}

// Vibración breve en las confirmaciones (no en cada toque, para no abusar). En la web no hay vibración.
const hayVibracion = Platform.OS !== 'web';
export const vibrar = {
  exito: () => hayVibracion && Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success).catch(() => {}),
  aviso: () => hayVibracion && Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning).catch(() => {}),
  seleccion: () => hayVibracion && Haptics.selectionAsync().catch(() => {}),
};

// Pide confirmación antes de una acción: Alert en el teléfono, window.confirm en la web.
import { Alert, Platform } from 'react-native';

export function confirmar(titulo, pregunta, textoAccion, accion) {
  if (Platform.OS === 'web') {
    if (window.confirm(pregunta)) accion();
    return;
  }
  Alert.alert(titulo, pregunta, [
    { text: 'Cancelar', style: 'cancel' },
    { text: textoAccion, style: 'destructive', onPress: accion },
  ]);
}

// Tomar o elegir una foto, recortarla a 3:4 y reducirla antes de subirla. La usan Nueva prenda y Tu foto.
import { ImageManipulator, SaveFormat } from 'expo-image-manipulator';
import * as ImagePicker from 'expo-image-picker';

const ANCHO_MAXIMO_FOTO = 1200;

// Reduce la foto antes de subirla: a 1200 px de ancho en JPEG pesa unos cientos de KB en vez de varios MB.
async function reducirFoto(foto) {
  const contexto = ImageManipulator.manipulate(foto.uri);
  if (foto.width > ANCHO_MAXIMO_FOTO) contexto.resize({ width: ANCHO_MAXIMO_FOTO, height: null });
  const imagen = await contexto.renderAsync();
  const guardada = await imagen.saveAsync({ format: SaveFormat.JPEG, compress: 0.7 });
  return guardada.uri;
}

// Devuelve la uri de la foto lista para subir, o null si la persona canceló. Los errores traen el mensaje para la pantalla.
// recortar: deja que la persona recorte la foto. En iOS ese recorte siempre es cuadrado (aspect solo aplica en
// Android), y en la foto de cuerpo cortaba las piernas: ahí va en false y el servidor recorta alrededor de la persona.
export async function elegirFoto(desdeCamara, recortar = true) {
  const permiso = desdeCamara
    ? await ImagePicker.requestCameraPermissionsAsync()
    : await ImagePicker.requestMediaLibraryPermissionsAsync();
  if (!permiso.granted) {
    throw new Error('Da permiso de fotos o cámara en los ajustes del teléfono para agregar la foto.');
  }

  // Calidad 1: la compresión se hace una sola vez, al reducir la foto.
  const opciones = { mediaTypes: ['images'], allowsEditing: recortar, aspect: [3, 4], quality: 1 };
  const resultado = desdeCamara
    ? await ImagePicker.launchCameraAsync(opciones)
    : await ImagePicker.launchImageLibraryAsync(opciones);
  if (resultado.canceled) return null;

  try {
    return await reducirFoto(resultado.assets[0]);
  } catch {
    throw new Error('No se pudo preparar la foto. Intenta con otra.');
  }
}

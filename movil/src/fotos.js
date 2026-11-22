// Tomar o elegir fotos, recortarlas a 3:4 y reducirlas antes de subirlas. Las usan Nueva prenda, Varias prendas y Tu foto.
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

// Varias fotos de la galería a la vez (sin recorte: el selector múltiple no lo permite). Devuelve las uris ya
// reducidas, en el orden en que se eligieron, o [] si la persona canceló.
export async function elegirFotos(limite = 20) {
  const permiso = await ImagePicker.requestMediaLibraryPermissionsAsync();
  if (!permiso.granted) {
    throw new Error('Da permiso de fotos en los ajustes del teléfono para agregar tus prendas.');
  }
  const resultado = await ImagePicker.launchImageLibraryAsync({
    mediaTypes: ['images'],
    allowsMultipleSelection: true,
    selectionLimit: limite,
    orderedSelection: true,
    quality: 1,
  });
  if (resultado.canceled) return [];
  const uris = [];
  for (const foto of resultado.assets) {
    try {
      uris.push(await reducirFoto(foto));
    } catch {
      // una foto que no se pudo preparar se salta; las demás siguen
    }
  }
  return uris;
}

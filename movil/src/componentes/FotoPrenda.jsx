// Foto de una prenda: recortada a su marco, guardada en la caché del teléfono y con una entrada suave.
// Las demás props (accessibilityLabel, etc.) pasan directo a la imagen.
import { Image } from 'expo-image';

import { urlImagen } from '../api';

export function FotoPrenda({ prenda, style, ...props }) {
  return (
    <Image
      source={{ uri: urlImagen(prenda.url_imagen) }}
      style={style}
      contentFit={prenda.sin_fondo ? 'contain' : 'cover'} // sin fondo se ve completa, sin recortarla
      cachePolicy="memory-disk"
      transition={200}
      {...props}
    />
  );
}

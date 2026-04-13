import sharp from 'sharp';
import { readFileSync, writeFileSync } from 'fs';
import { join } from 'path';

const inputPath = '/vercel/share/v0-project/public/logo.png';
const outputPath = '/vercel/share/v0-project/public/logo.png';

async function removeBackground() {
  const image = sharp(inputPath);
  const { data, info } = await image
    .ensureAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true });

  const pixels = new Uint8Array(data);
  
  // The background color is approximately #f5f5f0 (light beige/gray)
  // We'll make any pixel close to this color transparent
  for (let i = 0; i < pixels.length; i += 4) {
    const r = pixels[i];
    const g = pixels[i + 1];
    const b = pixels[i + 2];
    
    // Check if pixel is close to the background color (light gray/beige)
    // Background is approximately RGB(245, 245, 240) - very light
    if (r > 230 && g > 230 && b > 225) {
      // Make it transparent
      pixels[i + 3] = 0;
    }
  }

  await sharp(Buffer.from(pixels), {
    raw: {
      width: info.width,
      height: info.height,
      channels: 4
    }
  })
    .png()
    .toFile(outputPath);

  console.log('Background removed successfully!');
}

removeBackground().catch(console.error);

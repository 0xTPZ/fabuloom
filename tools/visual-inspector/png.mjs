import { deflateSync, inflateSync } from "node:zlib";

const PNG_SIGNATURE = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

function crc32(buffer) {
  let crc = 0xffffffff;
  for (const byte of buffer) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit += 1) crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1));
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function chunk(type, data) {
  const name = Buffer.from(type, "ascii");
  const body = Buffer.concat([name, data]);
  const result = Buffer.alloc(12 + data.length);
  result.writeUInt32BE(data.length, 0);
  body.copy(result, 4);
  result.writeUInt32BE(crc32(body), 8 + data.length);
  return result;
}

export function decodePng(input) {
  const buffer = Buffer.isBuffer(input) ? input : Buffer.from(input);
  if (!buffer.subarray(0, 8).equals(PNG_SIGNATURE)) throw new Error("not a PNG");
  let offset = 8;
  let width = 0;
  let height = 0;
  let bitDepth = 0;
  let colorType = 0;
  const idat = [];
  while (offset + 12 <= buffer.length) {
    const length = buffer.readUInt32BE(offset);
    const type = buffer.toString("ascii", offset + 4, offset + 8);
    const data = buffer.subarray(offset + 8, offset + 8 + length);
    offset += length + 12;
    if (type === "IHDR") {
      width = data.readUInt32BE(0);
      height = data.readUInt32BE(4);
      bitDepth = data[8];
      colorType = data[9];
    } else if (type === "IDAT") idat.push(data);
    else if (type === "IEND") break;
  }
  if (bitDepth !== 8 || ![2, 6].includes(colorType)) throw new Error(`unsupported PNG format: bitDepth=${bitDepth}, colorType=${colorType}`);
  const sourceBpp = colorType === 6 ? 4 : 3;
  const rowBytes = width * sourceBpp;
  const raw = inflateSync(Buffer.concat(idat));
  const rgba = Buffer.alloc(width * height * 4);
  let readOffset = 0;
  let previous = Buffer.alloc(rowBytes);
  for (let y = 0; y < height; y += 1) {
    const filter = raw[readOffset++];
    const row = Buffer.alloc(rowBytes);
    for (let x = 0; x < rowBytes; x += 1) {
      const left = x >= sourceBpp ? row[x - sourceBpp] : 0;
      const up = previous[x] || 0;
      const upLeft = x >= sourceBpp ? previous[x - sourceBpp] : 0;
      const value = raw[readOffset++];
      let reconstructed = value;
      if (filter === 1) reconstructed = (value + left) & 255;
      else if (filter === 2) reconstructed = (value + up) & 255;
      else if (filter === 3) reconstructed = (value + Math.floor((left + up) / 2)) & 255;
      else if (filter === 4) {
        const pa = Math.abs(up - upLeft);
        const pb = Math.abs(left - upLeft);
        const pc = Math.abs(left + up - 2 * upLeft);
        const predictor = pa <= pb && pa <= pc ? left : pb <= pc ? up : upLeft;
        reconstructed = (value + predictor) & 255;
      } else if (filter !== 0) throw new Error(`unsupported PNG filter ${filter}`);
      row[x] = reconstructed;
    }
    for (let x = 0; x < width; x += 1) {
      const source = x * sourceBpp;
      const destination = (y * width + x) * 4;
      rgba[destination] = row[source];
      rgba[destination + 1] = row[source + 1];
      rgba[destination + 2] = row[source + 2];
      rgba[destination + 3] = colorType === 6 ? row[source + 3] : 255;
    }
    previous = row;
  }
  return { width, height, rgba };
}

export function encodePng({ width, height, rgba }) {
  if (!Number.isInteger(width) || !Number.isInteger(height) || rgba.length !== width * height * 4) throw new TypeError("invalid RGBA image");
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8;
  ihdr[9] = 6;
  const scanlines = Buffer.alloc((width * 4 + 1) * height);
  for (let y = 0; y < height; y += 1) {
    const rowStart = y * (width * 4 + 1);
    scanlines[rowStart] = 0;
    rgba.copy(scanlines, rowStart + 1, y * width * 4, (y + 1) * width * 4);
  }
  return Buffer.concat([PNG_SIGNATURE, chunk("IHDR", ihdr), chunk("IDAT", deflateSync(scanlines, { level: 6 })), chunk("IEND", Buffer.alloc(0))]);
}

export function comparePngBuffers(referenceInput, currentInput, options = {}) {
  const reference = decodePng(referenceInput);
  const current = decodePng(currentInput);
  if (reference.width !== current.width || reference.height !== current.height) {
    return {
      compatible: false,
      width: current.width,
      height: current.height,
      reason: "image dimensions differ",
      differingPixels: null,
      differenceRatio: null,
    };
  }
  const colorTolerance = Number(options.colorTolerance ?? 12);
  const alphaTolerance = Number(options.alphaTolerance ?? 8);
  const diffMask = Buffer.alloc(current.rgba.length, 0);
  const overlay = Buffer.alloc(current.rgba.length, 255);
  let differingPixels = 0;
  let totalMagnitude = 0;
  let minX = current.width;
  let minY = current.height;
  let maxX = -1;
  let maxY = -1;
  for (let y = 0; y < current.height; y += 1) {
    for (let x = 0; x < current.width; x += 1) {
      const index = (y * current.width + x) * 4;
      const dr = Math.abs(reference.rgba[index] - current.rgba[index]);
      const dg = Math.abs(reference.rgba[index + 1] - current.rgba[index + 1]);
      const db = Math.abs(reference.rgba[index + 2] - current.rgba[index + 2]);
      const da = Math.abs(reference.rgba[index + 3] - current.rgba[index + 3]);
      const magnitude = Math.max(dr, dg, db, da);
      totalMagnitude += dr + dg + db + da;
      const different = Math.max(dr, dg, db) > colorTolerance || da > alphaTolerance;
      if (different) {
        differingPixels += 1;
        minX = Math.min(minX, x); minY = Math.min(minY, y); maxX = Math.max(maxX, x); maxY = Math.max(maxY, y);
        diffMask[index] = 255; diffMask[index + 1] = 64; diffMask[index + 2] = 32; diffMask[index + 3] = Math.min(255, 80 + magnitude * 4);
        overlay[index] = 255; overlay[index + 1] = Math.max(0, 210 - magnitude * 3); overlay[index + 2] = Math.max(0, 210 - magnitude * 3); overlay[index + 3] = 255;
      } else {
        overlay[index] = Math.round((reference.rgba[index] + current.rgba[index]) / 2);
        overlay[index + 1] = Math.round((reference.rgba[index + 1] + current.rgba[index + 1]) / 2);
        overlay[index + 2] = Math.round((reference.rgba[index + 2] + current.rgba[index + 2]) / 2);
        overlay[index + 3] = Math.round((reference.rgba[index + 3] + current.rgba[index + 3]) / 2);
      }
    }
  }
  return {
    compatible: true,
    width: current.width,
    height: current.height,
    differingPixels,
    differenceRatio: differingPixels / (current.width * current.height),
    meanChannelDifference: totalMagnitude / (current.width * current.height * 4),
    differenceBounds: maxX < 0 ? null : { left: minX, top: minY, right: maxX + 1, bottom: maxY + 1, width: maxX - minX + 1, height: maxY - minY + 1 },
    diffMaskPng: encodePng({ width: current.width, height: current.height, rgba: diffMask }),
    overlayPng: encodePng({ width: current.width, height: current.height, rgba: overlay }),
  };
}

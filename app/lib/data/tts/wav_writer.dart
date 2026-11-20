import 'dart:typed_data';

/// Writes mono 16-bit PCM WAV data from normalized float samples.
class WavWriter {
  const WavWriter();

  Uint8List encode(Float32List samples, int sampleRate) {
    const channels = 1;
    const bitsPerSample = 16;
    final frames = samples.length;
    final dataSize = frames * channels * bitsPerSample ~/ 8;
    final bytes = BytesBuilder(copy: false);
    void writeString(String value) => bytes.add(value.codeUnits);
    void writeInt(int value, int size) {
      final data = ByteData(size);
      if (size == 2) {
        data.setUint16(0, value, Endian.little);
      } else {
        data.setUint32(0, value, Endian.little);
      }
      bytes.add(data.buffer.asUint8List());
    }

    writeString('RIFF');
    writeInt(36 + dataSize, 4);
    writeString('WAVE');
    writeString('fmt ');
    writeInt(16, 4);
    writeInt(1, 2);
    writeInt(channels, 2);
    writeInt(sampleRate, 4);
    writeInt(sampleRate * channels * bitsPerSample ~/ 8, 4);
    writeInt(channels * bitsPerSample ~/ 8, 2);
    writeInt(bitsPerSample, 2);
    writeString('data');
    writeInt(dataSize, 4);
    final pcm = ByteData(dataSize);
    for (var i = 0; i < frames; i++) {
      final sample = samples[i];
      final scaled = (sample.clamp(-1.0, 1.0) * 32767).round();
      pcm.setInt16(i * 2, scaled, Endian.little);
    }
    bytes.add(pcm.buffer.asUint8List());
    return bytes.toBytes();
  }

  /// Concatenates sample buffers with optional silence between them.
  Float32List concat(
    List<Float32List> parts, {
    int sampleRate = 22050,
    int silenceMs = 0,
  }) {
    final silenceFrames = (sampleRate * silenceMs / 1000).round();
    final total =
        parts.fold<int>(0, (sum, part) => sum + part.length) +
        silenceFrames * (parts.isEmpty ? 0 : parts.length - 1);
    final output = Float32List(total);
    var offset = 0;
    for (var index = 0; index < parts.length; index++) {
      output.setAll(offset, parts[index]);
      offset += parts[index].length;
      if (silenceFrames > 0 && index < parts.length - 1) {
        offset += silenceFrames;
      }
    }
    return output;
  }
}

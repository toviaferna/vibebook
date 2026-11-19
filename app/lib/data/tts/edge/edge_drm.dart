import 'dart:math' as math;
import 'dart:typed_data';

/// Sec-MS-GEC v2 token for the Edge Read Aloud service.
///
/// Faithful Dart port of the DRM module of the GPLv3-licensed `edge-tts`
/// Python client (https://github.com/rany2/edge-tts), which reverse-engineered
/// Microsoft's obfuscated digests: a tweaked SHA-256 and a custom "CS64"
/// rolling state, combined as `<CS64>-<SHA256>`. GPLv3 is compatible with
/// this project's AGPL-3.0.
class EdgeDrm {
  EdgeDrm({DateTime Function()? clock}) : _clock = clock ?? DateTime.now;

  static const trustedClientToken = '6A5AA1D4EAFF4E9FB37E23D68491D6F4';
  static const _winEpochSeconds = 11644473600;
  static const _secondsTo100Ns = 1e7;

  final DateTime Function() _clock;
  double _clockSkewSeconds = 0;

  /// Unix seconds adjusted by the measured server skew.
  double unixTimestamp() {
    return _clock().toUtc().millisecondsSinceEpoch / 1000 + _clockSkewSeconds;
  }

  /// Adjusts the clock by the difference between the server date and the
  /// local clock, as the Python client does when a request is rejected.
  void adjustClockSkew(double skewSeconds) {
    _clockSkewSeconds += skewSeconds;
  }

  /// The Sec-MS-GEC v2 token: `<16 hex CS64>-<64 hex SHA256>`.
  String secMsGec() {
    return generateSecMsGecV2(unixTimestamp());
  }

  /// A fresh random MUID for the connection cookie.
  String muid() {
    final random = math.Random.secure();
    final bytes = List<int>.generate(16, (_) => random.nextInt(256));
    return bytes
        .map((byte) => byte.toRadixString(16).padLeft(2, '0'))
        .join()
        .toUpperCase();
  }

  /// Deterministic variant used by the tests.
  static String generateSecMsGecV2(double unixTimestamp) {
    var ticks = unixTimestamp;
    ticks += _winEpochSeconds;
    ticks -= ticks % 300;
    ticks *= _secondsTo100Ns;
    final data = utf8TokenBytes(ticks, trustedClientToken);
    final digest = _sha256Digest(data);
    final cs64 = _cs64Digest(data, digest);
    final buffer = ByteData(8)
      ..setUint32(0, cs64.$1, Endian.little)
      ..setUint32(4, cs64.$2, Endian.little);
    final cs64Hex = buffer.buffer
        .asUint8List()
        .map((byte) => byte.toRadixString(16).padLeft(2, '0'))
        .join()
        .toUpperCase();
    final shaHex = digest
        .map((byte) => byte.toRadixString(16).padLeft(2, '0'))
        .join()
        .toUpperCase();
    return '$cs64Hex-$shaHex';
  }
}

Uint8List utf8TokenBytes(double ticks, String token) {
  // At this magnitude every representable double is integral, so truncating
  // reproduces Python's f"{ticks:.0f}" exactly.
  final integer = BigInt.from(ticks);
  return Uint8List.fromList(('$integer$token').codeUnits);
}

const _u32Mask = 0xFFFFFFFF;

// ----------------------------------------------------------------------
// Tweaked SHA-256
// ----------------------------------------------------------------------

const _sha256Initial = [
  0x6A09E667,
  0xBB67AE85,
  0x3C6EF372,
  0xA54FF53A,
  0x510E527F,
  0x9B05688C,
  0x1F83D9AB,
  0x5BE0CD19,
];

const _sha256State = [
  0xFD9FBEA2,
  0x91243CE7,
  0xBE499094,
  0xCD2E1E0A,
  0x6C006F49,
  0x04BD35AB,
  0xFEB0A7E4,
  0x03EFFBD2,
];

const _sha256Schedule = [
  0xEB24BF9E,
  0x1558691F,
  0xA0C09EE2,
  0x0CFA32BA,
  0xA622EE8C,
  0xD1DD9491,
  0xC0DD25A0,
  0xF9E70AB6,
  0xF0C31573,
  0x7058CE4E,
  0x7188E606,
  0x00E5AB33,
  0xD258B060,
  0x72766564,
];

const _sha256RoundConstants = [
  0x428A2F98,
  0x71374491,
  0xB5C0FBCF,
  0xE9B5DBA5,
  0x3956C25B,
  0x59F111F1,
  0x923F82A4,
  0xAB1C5ED5,
  0xD807AA98,
  0x12835B01,
  0x243185BE,
  0x550C7DC3,
  0x72BE5D74,
  0x80DEB1FE,
  0x9BDC06A7,
  0xC19BF174,
  0xE49B69C1,
  0xEFBE4786,
  0x0FC19DC6,
  0x240CA1CC,
  0x2DE92C6F,
  0x4A7484AA,
  0x5CB0A9DC,
  0x76F988DA,
  0x983E5152,
  0xA831C66D,
  0xB00327C8,
  0xBF597FC7,
  0xC6E00BF3,
  0xD5A79147,
  0x06CA6351,
  0x14292967,
  0x27B70A85,
  0x2E1B2138,
  0x4D2C6DFC,
  0x53380D13,
  0x650A7354,
  0x766A0ABB,
  0x81C2C92E,
  0x92722C85,
  0xA2BFE8A1,
  0xA81A664B,
  0xC24B8B70,
  0xC76C51A3,
  0xD192E819,
  0xD6990624,
  0xF40E3585,
  0x106AA070,
  0x19A4C116,
  0x1E376C08,
  0x2748774C,
  0x34B0BCB5,
  0x391C0CB3,
  0x4ED8AA4A,
  0x5B9CCA4F,
  0x682E6FF3,
  0x748F82EE,
  0x78A5636F,
  0x84C87814,
  0x8CC70208,
  0x90BEFFFA,
  0xA4506CEB,
  0xBEF9A3F7,
  0xC67178F2,
];

const _sha256Adjustment = 0xC9DC06A7;
final _sha256BlockConstants = List<int>.of(_sha256RoundConstants)
  ..[14] = _sha256Adjustment;

const _sha256Sigma0Adjustment = 0x059C0B80;
const _sha256Sigma1Adjustment = 0x000B92C0;

int _rol16(int value) {
  value &= _u32Mask;
  return ((value << 16) | (value >> 16)) & _u32Mask;
}

int _rotr32(int value, int shift) =>
    (((value & _u32Mask) >> shift) | ((value & _u32Mask) << (32 - shift))) &
    _u32Mask;

int _sigma0(int value) {
  value &= _u32Mask;
  return ((value >> 7) ^
          (value << 25) ^
          (value >> 18) ^
          (value << 14) ^
          (value >> 3)) &
      _u32Mask;
}

int _sigma1(int value) {
  value &= _u32Mask;
  return ((value >> 17) ^
          (value << 15) ^
          (value >> 19) ^
          (value << 13) ^
          (value >> 10)) &
      _u32Mask;
}

int _bigSigma0(int value) =>
    _rotr32(value, 2) ^ _rotr32(value, 13) ^ _rotr32(value, 22);

int _bigSigma1(int value) =>
    _rotr32(value, 6) ^ _rotr32(value, 11) ^ _rotr32(value, 25);

/// Plain message schedule expansion used while hashing the padded blocks.
void _expandSha256Schedule(List<int> words, {int firstWord = 16}) {
  for (var index = firstWord; index < 64; index++) {
    final x = words[index - 2];
    final y = words[index - 15];
    final sigma1 = (x >> 17) ^ (x << 15) ^ (x >> 19) ^ (x << 13) ^ (x >> 10);
    final sigma0 = (y >> 7) ^ (y << 25) ^ (y >> 18) ^ (y << 14) ^ (y >> 3);
    words.add(
      (sigma1 + words[index - 7] + sigma0 + words[index - 16]) & _u32Mask,
    );
  }
}

/// The compression rounds. [firstRound] 14 uses the block constants and runs
/// the first two rounds one at a time, matching the Python port.
List<int> _sha256Rounds(
  List<int> state,
  List<int> words, {
  int firstRound = 0,
}) {
  var a = state[0], b = state[1], c = state[2], d = state[3];
  var e = state[4], f = state[5], g = state[6], h = state[7];
  final constants = firstRound == 14
      ? _sha256BlockConstants
      : _sha256RoundConstants;
  final aligned = math.min(64, ((firstRound + 7) ~/ 8) * 8);
  for (var index = firstRound; index < aligned; index++) {
    final t1 =
        h +
        _bigSigma1(e) +
        (g ^ (e & (f ^ g))) +
        constants[index] +
        words[index];
    final t2 = _bigSigma0(a) + ((a & b) | (c & (a | b)));
    final nextA = (t1 + t2) & _u32Mask;
    final nextE = (d + t1) & _u32Mask;
    h = g;
    g = f;
    f = e;
    e = nextE;
    d = c;
    c = b;
    b = a;
    a = nextA;
  }
  for (var index = aligned; index < 64; index += 8) {
    var t1 =
        h +
        _bigSigma1(e) +
        (g ^ (e & (f ^ g))) +
        constants[index] +
        words[index];
    d = (d + t1) & _u32Mask;
    h = (t1 + _bigSigma0(a) + ((a & b) | (c & (a | b)))) & _u32Mask;

    t1 =
        g +
        _bigSigma1(d) +
        (f ^ (d & (e ^ f))) +
        constants[index + 1] +
        words[index + 1];
    c = (c + t1) & _u32Mask;
    g = (t1 + _bigSigma0(h) + ((h & a) | (b & (h | a)))) & _u32Mask;

    t1 =
        f +
        _bigSigma1(c) +
        (e ^ (c & (d ^ e))) +
        constants[index + 2] +
        words[index + 2];
    b = (b + t1) & _u32Mask;
    f = (t1 + _bigSigma0(g) + ((g & h) | (a & (g | h)))) & _u32Mask;

    t1 =
        e +
        _bigSigma1(b) +
        (d ^ (b & (c ^ d))) +
        constants[index + 3] +
        words[index + 3];
    a = (a + t1) & _u32Mask;
    e = (t1 + _bigSigma0(f) + ((f & g) | (h & (f | g)))) & _u32Mask;

    t1 =
        d +
        _bigSigma1(a) +
        (c ^ (a & (b ^ c))) +
        constants[index + 4] +
        words[index + 4];
    h = (h + t1) & _u32Mask;
    d = (t1 + _bigSigma0(e) + ((e & f) | (g & (e | f)))) & _u32Mask;

    t1 =
        c +
        _bigSigma1(h) +
        (b ^ (h & (a ^ b))) +
        constants[index + 5] +
        words[index + 5];
    g = (g + t1) & _u32Mask;
    c = (t1 + _bigSigma0(d) + ((d & e) | (f & (d | e)))) & _u32Mask;

    t1 =
        b +
        _bigSigma1(g) +
        (a ^ (g & (h ^ a))) +
        constants[index + 6] +
        words[index + 6];
    f = (f + t1) & _u32Mask;
    b = (t1 + _bigSigma0(c) + ((c & d) | (e & (c | d)))) & _u32Mask;

    t1 =
        a +
        _bigSigma1(f) +
        (h ^ (f & (g ^ h))) +
        constants[index + 7] +
        words[index + 7];
    e = (e + t1) & _u32Mask;
    a = (t1 + _bigSigma0(b) + ((b & c) | (d & (b | c)))) & _u32Mask;
  }
  return [a, b, c, d, e, f, g, h];
}

int _be24(Uint8List data, int offset) =>
    (data[offset] << 16) | (data[offset + 1] << 8) | data[offset + 2];

int _be32(Uint8List data, int offset) =>
    (data[offset] << 24) |
    (data[offset + 1] << 16) |
    (data[offset + 2] << 8) |
    data[offset + 3];

/// The tweaked initial state derived from the first seven bytes.
List<int> _sha256Init(Uint8List data) {
  final words = <int>[
    for (var index = 0; index < 14; index++) 0,
    _be24(data, 0),
    _be32(data, 3),
  ];
  for (var index = 16; index < 30; index++) {
    var value = _sha256Schedule[index - 16];
    if (index - 2 >= 14) {
      value += index == 16
          ? _sigma1(words[index - 2]) ^ _sha256Sigma1Adjustment
          : _sigma1(words[index - 2]);
    }
    if (index - 7 >= 14) {
      value += words[index - 7];
    }
    if (index - 15 >= 14) {
      value += index == 29
          ? _sigma0(words[index - 15]) ^ _sha256Sigma0Adjustment
          : _sigma0(words[index - 15]);
    }
    words.add(value & _u32Mask);
  }
  words.add(
    (_sigma1(words[28]) +
            words[23] +
            _sigma0(words[15]) +
            words[14] +
            _sha256Adjustment -
            _sha256RoundConstants[14]) &
        _u32Mask,
  );
  _expandSha256Schedule(words, firstWord: 31);
  final working = _sha256Rounds(_sha256State, words, firstRound: 14);
  return [
    for (var index = 0; index < 8; index++)
      (_sha256Initial[index] + working[index]) & _u32Mask,
  ];
}

/// The tweaked SHA-256 over the full token string.
Uint8List _sha256Digest(Uint8List data) {
  if (data.length < 7) {
    throw ArgumentError('El token necesita al menos siete bytes.');
  }
  final length = 57 + data.length;
  final padded = <int>[
    ...data.sublist(7),
    0x80,
    for (var index = 0; index < (55 - length) % 64; index++) 0,
  ];
  final bitLength = length * 8;
  padded
    ..add((bitLength >> 56) & 0xFF)
    ..add((bitLength >> 48) & 0xFF)
    ..add((bitLength >> 40) & 0xFF)
    ..add((bitLength >> 32) & 0xFF)
    ..add((bitLength >> 24) & 0xFF)
    ..add((bitLength >> 16) & 0xFF)
    ..add((bitLength >> 8) & 0xFF)
    ..add(bitLength & 0xFF);
  var state = _sha256Init(data.sublist(0, 7));
  for (var offset = 0; offset < padded.length; offset += 64) {
    final block = padded.sublist(offset, offset + 64);
    final words = <int>[
      for (var index = 0; index < 16; index++) _be32Of(block, index * 4),
    ];
    _expandSha256Schedule(words);
    final working = _sha256Rounds(state, words);
    state = [
      for (var index = 0; index < 8; index++)
        (state[index] + working[index]) & _u32Mask,
    ];
  }
  final result = Uint8List(32);
  final view = ByteData.view(result.buffer);
  for (var index = 0; index < 8; index++) {
    view.setUint32(index * 4, state[index], Endian.big);
  }
  return result;
}

int _be32Of(List<int> block, int offset) =>
    (block[offset] << 24) |
    (block[offset + 1] << 16) |
    (block[offset + 2] << 8) |
    block[offset + 3];

// ----------------------------------------------------------------------
// CS64
// ----------------------------------------------------------------------

const _cs64Coefficients = [
  [0xE82E91B1, 0xB32700D0],
  [0x44DE24C6, 0x88DFF51D],
  [0x3BEB65BC, 0x29514038],
  [0xC89C5933, 0xB328CBDF],
  [0x8D1EC211, 0xD405B4D5],
  [0x314EF5D5, 0x26E55F3C],
  [0xE92491B1, 0x607801C6],
  [0xF0A5B9D5, 0x82B2C1FB],
  [0x06064CF3, 0xFA51A3DA],
  [0xDA79FA60, 0x207CC464],
  [0xBED20560, 0x3C3C74F3],
  [0x89F9C9F8, 0xD2D14B61],
  [0x35FA38C6, 0xBB04A2C1],
  [0xCB49E3C6, 0xC5626167],
];
const _cs64Factor = 0x82893933;
const _cs64Adjustment0 = 0xF2F90B1A;
const _cs64Adjustment1 = 0x0B1A0000;

List<int> _wordsLe4Even(Uint8List data) {
  final padded = <int>[
    ...data,
    for (var index = 0; index < (-data.length) % 4; index++) 0,
  ];
  if (padded.isEmpty) {
    return const [];
  }
  final words = <int>[];
  final view = ByteData.view(Uint8List.fromList(padded).buffer);
  for (var index = 0; index < padded.length ~/ 4; index++) {
    words.add(view.getUint32(index * 4, Endian.little));
  }
  if (words.length % 2 == 1) {
    words.add(0);
  }
  return words;
}

/// Returns (swapLast ^ state, swapAcc ^ acc) as the 32-bit pair packed after
/// the hash in the token.
(int, int) _cs64Digest(Uint8List data, Uint8List digest) {
  final view = ByteData.view(digest.buffer);
  var keyA = view.getUint32(0, Endian.little) | 1;
  var keyB = view.getUint32(4, Endian.little) | 1;
  final factors = [
    (keyA * _cs64Factor) & _u32Mask,
    (keyB * _cs64Factor) & _u32Mask,
  ];
  final terms = <int>[];
  final offsets = <int>[];
  for (var index = 0; index < _cs64Coefficients.length; index++) {
    terms.add((_cs64Coefficients[index][0] * factors[index % 2]) & _u32Mask);
    offsets.add(_cs64Coefficients[index][1]);
  }
  final dataWords = _wordsLe4Even(Uint8List.fromList([0x00, ...data]));
  for (var index = 0; index < dataWords.length; index++) {
    final word = dataWords[index];
    final even = index % 2 == 0;
    var term = word * (even ? keyA : keyB);
    var offset = _rol16(word) * (even ? 0xEF0569FB : 0xC31713DB);
    if (index == 0) {
      term += _cs64Adjustment0 * factors[0];
      offset += _cs64Adjustment1;
    }
    terms.add(term & _u32Mask);
    offsets.add(offset & _u32Mask);
  }
  var swapAcc = 0;
  var swapLast = 0;
  var state = 0;
  var acc = 0;
  for (var index = 0; index < terms.length; index += 2) {
    final x = terms[index];
    final y = terms[index + 1];
    var t = _rol16((offsets[index] + x) & _u32Mask);
    var q = (t * 0x76F50F34) & _u32Mask;
    swapAcc += (_rol16(q) * 0xC3EFEA97 + q) & _u32Mask;
    t = _rol16((offsets[index + 1] + y) & _u32Mask);
    q = (t * 0x1881CE3C) & _u32Mask;
    swapLast = (_rol16(q) * 0x35BD1EC9 + q) & _u32Mask;
    swapAcc = (swapAcc + swapLast) & _u32Mask;

    state = (state * keyA + x) & _u32Mask;
    state = (_rol16(state) * 0xCF98B111) & _u32Mask;
    state = (_rol16(state) * 0x87085B9F) & _u32Mask;
    state = (_rol16(state) * 0x12CEB96D) & _u32Mask;
    state = (_rol16(state) * 0x257E1D83) & _u32Mask;
    acc += state;
    t = (state * keyB + y) & _u32Mask;
    t = (_rol16(t) * 0xA27416F5) & _u32Mask;
    t = (_rol16(t) * 0xD38396FF) & _u32Mask;
    state =
        (_rol16(((_rol16(t) * 0x7C932B89) & _u32Mask)) * 0xBFA49F69) & _u32Mask;
    acc = (acc + state) & _u32Mask;
  }
  return (swapLast ^ state, swapAcc ^ acc);
}

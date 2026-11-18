import 'dart:ffi';
import 'dart:io';

import 'package:ffi/ffi.dart';

/// Converts paths before they cross into native libraries.
///
/// piper-phonemize and sherpa-onnx receive narrow UTF-8 strings. On Windows
/// some native file helpers fail when the path contains non-ASCII characters
/// (for example a user profile such as `C:\Users\José`). The 8.3 short path is
/// ASCII and points to the same file, so it is a safe fallback there.
String nativePath(String path) {
  if (!Platform.isWindows || path.isEmpty) {
    return path;
  }
  if (!path.codeUnits.any((unit) => unit > 0x7F)) {
    return path;
  }
  return _shortPath(path) ?? path;
}

String? _shortPath(String path) {
  final getShortPathName = _GetShortPathName.instance;
  if (getShortPathName == null) {
    return null;
  }
  final input = path.toNativeUtf16();
  try {
    var capacity = 260;
    while (capacity <= 32768) {
      final output = calloc<Uint16>(capacity);
      try {
        final length = getShortPathName(input, output, capacity);
        if (length == 0) {
          return null;
        }
        if (length < capacity) {
          final short = output.cast<Utf16>().toDartString();
          return short.isEmpty ? null : short;
        }
        capacity = length + 1;
      } finally {
        calloc.free(output);
      }
    }
  } finally {
    calloc.free(input);
  }
  return null;
}

typedef _GetShortPathNameNative = Int32 Function(
  Pointer<Utf16> longPath,
  Pointer<Uint16> shortPath,
  Uint32 bufferLength,
);
typedef _GetShortPathNameDart = int Function(
  Pointer<Utf16> longPath,
  Pointer<Uint16> shortPath,
  int bufferLength,
);

class _GetShortPathName {
  static final _GetShortPathNameDart? instance = _load();

  static _GetShortPathNameDart? _load() {
    try {
      final kernel32 = DynamicLibrary.open('kernel32.dll');
      return kernel32.lookupFunction<_GetShortPathNameNative, _GetShortPathNameDart>(
        'GetShortPathNameW',
      );
    } catch (_) {
      return null;
    }
  }
}

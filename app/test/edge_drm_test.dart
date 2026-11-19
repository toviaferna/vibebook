import 'package:flutter_test/flutter_test.dart';
import 'package:vibebook_app/data/tts/edge/edge_drm.dart';

void main() {
  test('el token v2 coincide con la referencia de edge-tts', () {
    // Vectores generados con el cliente Python (1765000000 y 1765000123.456
    // caen en el mismo bucket de cinco minutos).
    const expected =
        'B538F7BBB3CD8361-'
        'E46801D7149FAB338E06D8EE425515989069F4E177D2D6E7B0E7B586BD9F1D86';
    expect(EdgeDrm.generateSecMsGecV2(1765000000.0), expected);
    expect(EdgeDrm.generateSecMsGecV2(1765000123.456), expected);
  });

  test('timestamps de buckets distintos dan tokens distintos', () {
    final first = EdgeDrm.generateSecMsGecV2(1765000000.0);
    final second = EdgeDrm.generateSecMsGecV2(1765000400.0);
    expect(first, isNot(second));
    expect(first, contains('-'));
    expect(first.split('-').first, hasLength(16));
    expect(first.split('-').last, hasLength(64));
  });

  test('el muid es hexadecimal de 32 caracteres', () {
    final drm = EdgeDrm();
    final muid = drm.muid();
    expect(muid, hasLength(32));
    expect(muid, matches(RegExp(r'^[0-9A-F]{32}$')));
    expect(drm.muid(), isNot(muid));
  });

  test('el skew ajusta el reloj del token', () {
    final fixed = DateTime.utc(2026, 11, 18, 21, 30);
    final drm = EdgeDrm(clock: () => fixed);
    final before = drm.unixTimestamp();
    drm.adjustClockSkew(300);
    expect(drm.unixTimestamp(), closeTo(before + 300, 0.001));
  });
}

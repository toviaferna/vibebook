import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_ui/material_ui.dart';

import 'app/app.dart';
import 'dev/ambience_smoke.dart';
import 'dev/ambient_m4b_smoke.dart';
import 'dev/audio_smoke.dart';
import 'dev/convert_smoke.dart';
import 'dev/install_smoke.dart';
import 'dev/m4b_smoke.dart';
import 'dev/piper_smoke.dart';
import 'dev/tts_smoke.dart';

Future<void> main(List<String> args) async {
  WidgetsFlutterBinding.ensureInitialized();
  if (args.contains('--tts-smoke')) {
    await runTtsSmoke(args);
    return;
  }
  if (args.contains('--convert-smoke')) {
    await runConvertSmoke(args);
    return;
  }
  if (args.contains('--m4b-smoke')) {
    await runM4bSmoke(args);
    return;
  }
  if (args.contains('--install-smoke')) {
    await runInstallSmoke(args);
    return;
  }
  if (args.contains('--audio-smoke')) {
    await runAudioSmoke(args);
    return;
  }
  if (args.contains('--ambience-smoke')) {
    await runAmbienceSmoke(args);
    return;
  }
  if (args.contains('--ambient-m4b-smoke')) {
    await runAmbientM4bSmoke(args);
    return;
  }
  if (args.contains('--piper-smoke')) {
    await runPiperSmoke(args);
    return;
  }
  runApp(const ProviderScope(child: VibebookApp()));
}

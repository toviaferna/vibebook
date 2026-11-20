import 'package:file_selector/file_selector.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:material_ui/material_ui.dart';
import 'package:package_info_plus/package_info_plus.dart';

import '../../app/providers.dart';
import '../../core/design/components.dart';
import '../../core/design/form_controls.dart';
import '../../core/design/tokens.dart';
import '../../domain/ambience.dart';
import 'plugins_panel.dart';
import 'providers_panel.dart';

class SettingsPage extends ConsumerWidget {
  const SettingsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(settingsProvider);
    final colors = Theme.of(context).extension<BibliotecaColors>()!;
    return PageScaffold(
      eyebrow: 'Ajustes',
      title: 'Preferencias',
      subtitle: 'Apariencia, lectura, audio y biblioteca.',
      maxContentWidth: 980,
      child: settings.when(
        data: (value) => Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            BibliotecaSection(
              title: 'Apariencia',
              description: 'El tema de la app y la paleta del lector son independientes.',
              child: Column(
                children: [
                  BibliotecaFormRow(
                    title: 'Tema de la app',
                    subtitle: 'Claro, oscuro o el del sistema.',
                    controlWidth: 220,
                    child: BibliotecaSelect<String>(
                      label: 'Tema de la app',
                      showLabel: false,
                      value: value.themeMode,
                      options: const [
                        BibliotecaSelectOption(
                          value: 'system',
                          label: 'Sistema',
                        ),
                        BibliotecaSelectOption(value: 'light', label: 'Claro'),
                        BibliotecaSelectOption(value: 'dark', label: 'Oscuro'),
                      ],
                      onChanged: (mode) => ref
                          .read(settingsProvider.notifier)
                          .setThemeMode(mode),
                    ),
                  ),
                  BibliotecaFormRow(
                    title: 'Paleta del lector',
                    subtitle: 'Papel, sepia o noche.',
                    controlWidth: 220,
                    child: BibliotecaSelect<String>(
                      label: 'Paleta del lector',
                      showLabel: false,
                      value: value.reader.palette,
                      options: const [
                        BibliotecaSelectOption(value: 'paper', label: 'Papel'),
                        BibliotecaSelectOption(value: 'sepia', label: 'Sepia'),
                        BibliotecaSelectOption(value: 'night', label: 'Noche'),
                      ],
                      onChanged: (palette) {
                        ref
                            .read(settingsProvider.notifier)
                            .updateReader(
                              value.reader.copyWith(palette: palette),
                            );
                      },
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            BibliotecaSection(
              title: 'Lectura y audio',
              description: 'Se aplica a todos los libros.',
              child: Column(
                children: [
                  BibliotecaFormRow(
                    title: 'Tamaño del texto',
                    subtitle: '${value.reader.fontSize.round()} px',
                    controlWidth: 240,
                    child: Slider(
                      value: value.reader.fontSize,
                      min: 15,
                      max: 28,
                      divisions: 13,
                      label: '${value.reader.fontSize.round()}',
                      onChanged: (size) {
                        ref
                            .read(settingsProvider.notifier)
                            .updateReader(
                              value.reader.copyWith(fontSize: size),
                            );
                      },
                    ),
                  ),
                  BibliotecaFormRow(
                    title: 'Velocidad de audio',
                    subtitle: '${value.reader.playbackRate}x',
                    controlWidth: 180,
                    child: BibliotecaSelect<double>(
                      label: 'Velocidad de audio',
                      showLabel: false,
                      value: value.reader.playbackRate,
                      options: const [
                        BibliotecaSelectOption(value: 0.75, label: '0.75x'),
                        BibliotecaSelectOption(value: 1.0, label: '1x'),
                        BibliotecaSelectOption(value: 1.25, label: '1.25x'),
                        BibliotecaSelectOption(value: 1.5, label: '1.5x'),
                        BibliotecaSelectOption(value: 2.0, label: '2x'),
                      ],
                      onChanged: (speed) {
                        ref
                            .read(settingsProvider.notifier)
                            .updateReader(
                              value.reader.copyWith(playbackRate: speed),
                            );
                      },
                    ),
                  ),
                  BibliotecaFormRow(
                    title: 'Volumen',
                    subtitle: '${(value.reader.volume * 100).round()}%',
                    controlWidth: 240,
                    child: Slider(
                      value: value.reader.volume,
                      min: 0,
                      max: 1,
                      divisions: 20,
                      label: '${(value.reader.volume * 100).round()}%',
                      onChanged: (volume) {
                        ref
                            .read(settingsProvider.notifier)
                            .updateReader(
                              value.reader.copyWith(volume: volume),
                            );
                      },
                    ),
                  ),
                  BibliotecaFormRow(
                    title: 'Karaoke',
                    subtitle:
                        'Resaltar la palabra que suena cuando hay timings.',
                    controlWidth: 60,
                    child: Switch(
                      value: value.reader.karaoke,
                      onChanged: (enabled) {
                        ref
                            .read(settingsProvider.notifier)
                            .updateReader(
                              value.reader.copyWith(karaoke: enabled),
                            );
                      },
                    ),
                  ),
                  BibliotecaFormRow(
                    title: 'Avanzar al terminar',
                    subtitle:
                        'Pasar al capítulo siguiente cuando termina el audio.',
                    controlWidth: 60,
                    child: Switch(
                      value: value.reader.autoAdvance,
                      onChanged: (enabled) {
                        ref
                            .read(settingsProvider.notifier)
                            .updateReader(
                              value.reader.copyWith(autoAdvance: enabled),
                            );
                      },
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            BibliotecaSection(
              title: 'Biblioteca',
              description: 'La biblioteca no se mueve ni se borra al cambiar esta preferencia.',
              child: BibliotecaFormRow(
                title: 'Carpeta de libros',
                subtitle: value.libraryPath ?? 'Detección automática',
                child: Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    OutlinedButton(
                      onPressed: () async {
                        final path = await getDirectoryPath();
                        if (path != null) {
                          await ref
                              .read(settingsProvider.notifier)
                              .setLibraryPath(path);
                        }
                      },
                      child: const Text('Elegir'),
                    ),
                    if (value.libraryPath != null)
                      TextButton(
                        onPressed: () => ref
                            .read(settingsProvider.notifier)
                            .setLibraryPath(null),
                        child: const Text('Automática'),
                      ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 18),
            BibliotecaSection(
              title: 'Voz',
              description:
                  'Los modelos Piper se detectan en subcarpetas con .onnx y tokens.txt. '
                  'También podés descargarlos desde el Estudio.',
              child: BibliotecaFormRow(
                title: 'Carpeta de modelos',
                subtitle: value.modelsPath ?? 'Carpeta de la app',
                child: Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    OutlinedButton(
                      onPressed: () async {
                        final path = await getDirectoryPath();
                        if (path != null) {
                          await ref
                              .read(settingsProvider.notifier)
                              .setModelsPath(path);
                        }
                      },
                      child: const Text('Elegir'),
                    ),
                    if (value.modelsPath != null)
                      TextButton(
                        onPressed: () => ref
                            .read(settingsProvider.notifier)
                            .setModelsPath(null),
                        child: const Text('Automática'),
                      ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 18),
            const ProvidersPanel(),
            const SizedBox(height: 18),
            const PluginsPanel(),
            const SizedBox(height: 18),
            BibliotecaSection(
              title: 'Ambiente',
              description: 'Grabaciones de campo CC0 incluidas en la app. El lector usa el plan por capítulo si existe.',
              child: Column(
                children: [
                  BibliotecaFormRow(
                    title: 'Ambiente en el lector',
                    subtitle: 'Sonido de fondo mientras leés o escuchás.',
                    controlWidth: 60,
                    child: Switch(
                      value: value.ambienceEnabled,
                      onChanged: (enabled) {
                        ref
                            .read(settingsProvider.notifier)
                            .updateAmbience(enabled: enabled);
                      },
                    ),
                  ),
                  BibliotecaFormRow(
                    title: 'Sonido',
                    subtitle: AmbiencePresetDetails.byId(value.ambiencePreset)
                        .description,
                    controlWidth: 220,
                    child: BibliotecaSelect<String>(
                      label: 'Sonido de ambiente',
                      showLabel: false,
                      value: value.ambiencePreset,
                      options: [
                        for (final preset in AmbiencePreset.values)
                          BibliotecaSelectOption(
                            value: preset.id,
                            label: preset.label,
                            description: preset.description,
                          ),
                      ],
                      onChanged: (preset) {
                        ref
                            .read(settingsProvider.notifier)
                            .updateAmbience(preset: preset);
                      },
                    ),
                  ),
                  BibliotecaFormRow(
                    title: 'Volumen del ambiente',
                    subtitle: '${(value.ambienceVolume * 100).round()}%',
                    controlWidth: 240,
                    child: Slider(
                      value: value.ambienceVolume,
                      min: 0,
                      max: 1,
                      divisions: 20,
                      label: '${(value.ambienceVolume * 100).round()}%',
                      onChanged: (volume) {
                        ref
                            .read(settingsProvider.notifier)
                            .updateAmbience(volume: volume);
                      },
                    ),
                  ),
                  BibliotecaFormRow(
                    title: 'Atenuación con la voz',
                    subtitle:
                        '${(value.ambienceDucking * 100).round()}% del volumen',
                    controlWidth: 240,
                    child: Slider(
                      value: value.ambienceDucking,
                      min: 0,
                      max: 1,
                      divisions: 20,
                      label: '${(value.ambienceDucking * 100).round()}%',
                      onChanged: (ducking) {
                        ref
                            .read(settingsProvider.notifier)
                            .updateAmbience(ducking: ducking);
                      },
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            BibliotecaSection(
              title: 'Acerca de',
              child: Column(
                children: [
                  FutureBuilder<PackageInfo>(
                    future: PackageInfo.fromPlatform(),
                    builder: (context, snapshot) {
                      final info = snapshot.data;
                      return BibliotecaFormRow(
                        title: 'Vibebook',
                        subtitle: info == null
                            ? 'Flutter'
                            : 'Versión ${info.version} (${info.buildNumber})',
                        child: StatusPill(
                          label: 'FLUTTER',
                          color: colors.accent,
                        ),
                      );
                    },
                  ),
                  Text(
                    'AGPL-3.0-only. La biblioteca y la lectura funcionan sin cuenta ni nube.',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            ),
          ],
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stackTrace) => ErrorView(message: '$error'),
      ),
    );
  }
}

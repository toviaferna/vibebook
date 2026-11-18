import 'package:file_selector/file_selector.dart';
import 'package:material_ui/material_ui.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:package_info_plus/package_info_plus.dart';

import '../../app/providers.dart';
import '../../core/design/components.dart';
import '../../core/design/tokens.dart';
import '../../domain/ambience.dart';

class SettingsPage extends ConsumerWidget {
  const SettingsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(settingsProvider);
    final colors = Theme.of(context).extension<BibliotecaColors>()!;
    return PageScaffold(
      eyebrow: 'Ajustes',
      title: 'Preferencias',
      subtitle: 'Apariencia, lectura y biblioteca.',
      child: settings.when(
        data: (value) => Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _SettingsSection(
              title: 'Apariencia',
              children: [
                _SettingsRow(
                  title: 'Tema de la app',
                  subtitle: 'Claro, oscuro o el del sistema.',
                  trailing: DropdownButton<String>(
                    value: value.themeMode,
                    underline: const SizedBox.shrink(),
                    items: const [
                      DropdownMenuItem(value: 'system', child: Text('Sistema')),
                      DropdownMenuItem(value: 'light', child: Text('Claro')),
                      DropdownMenuItem(value: 'dark', child: Text('Oscuro')),
                    ],
                    onChanged: (mode) {
                      if (mode != null) {
                        ref.read(settingsProvider.notifier).setThemeMode(mode);
                      }
                    },
                  ),
                ),
                _SettingsRow(
                  title: 'Paleta del lector',
                  subtitle: 'Independiente del tema de la app.',
                  trailing: DropdownButton<String>(
                    value: value.reader.palette,
                    underline: const SizedBox.shrink(),
                    items: const [
                      DropdownMenuItem(value: 'paper', child: Text('Papel')),
                      DropdownMenuItem(value: 'sepia', child: Text('Sepia')),
                      DropdownMenuItem(value: 'night', child: Text('Noche')),
                    ],
                    onChanged: (palette) {
                      if (palette != null) {
                        ref.read(settingsProvider.notifier).updateReader(
                              value.reader.copyWith(palette: palette),
                            );
                      }
                    },
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),
            _SettingsSection(
              title: 'Lectura',
              children: [
                _SettingsRow(
                  title: 'Tamaño del texto',
                  subtitle: '${value.reader.fontSize.round()} px',
                  trailing: SizedBox(
                    width: 220,
                    child: Slider(
                      value: value.reader.fontSize,
                      min: 15,
                      max: 28,
                      divisions: 13,
                      label: '${value.reader.fontSize.round()}',
                      onChanged: (size) {
                        ref.read(settingsProvider.notifier).updateReader(
                              value.reader.copyWith(fontSize: size),
                            );
                      },
                    ),
                  ),
                ),
                _SettingsRow(
                  title: 'Velocidad de audio',
                  subtitle: '${value.reader.playbackRate}x',
                  trailing: DropdownButton<double>(
                    value: value.reader.playbackRate,
                    underline: const SizedBox.shrink(),
                    items: const [
                      DropdownMenuItem(value: 0.75, child: Text('0.75x')),
                      DropdownMenuItem(value: 1.0, child: Text('1x')),
                      DropdownMenuItem(value: 1.25, child: Text('1.25x')),
                      DropdownMenuItem(value: 1.5, child: Text('1.5x')),
                      DropdownMenuItem(value: 2.0, child: Text('2x')),
                    ],
                    onChanged: (speed) {
                      if (speed != null) {
                        ref.read(settingsProvider.notifier).updateReader(
                              value.reader.copyWith(playbackRate: speed),
                            );
                      }
                    },
                  ),
                ),
                _SettingsRow(
                  title: 'Volumen',
                  subtitle: '${(value.reader.volume * 100).round()}%',
                  trailing: SizedBox(
                    width: 220,
                    child: Slider(
                      value: value.reader.volume,
                      min: 0,
                      max: 1,
                      divisions: 20,
                      label: '${(value.reader.volume * 100).round()}%',
                      onChanged: (volume) {
                        ref.read(settingsProvider.notifier).updateReader(
                              value.reader.copyWith(volume: volume),
                            );
                      },
                    ),
                  ),
                ),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Giro de página'),
                  subtitle: const Text('Animación de hoja en el modo Libro.'),
                  value: value.reader.pageTurn,
                  onChanged: (enabled) {
                    ref.read(settingsProvider.notifier).updateReader(
                          value.reader.copyWith(pageTurn: enabled),
                        );
                  },
                ),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Karaoke'),
                  subtitle: const Text('Resaltar la palabra que suena cuando hay timings.'),
                  value: value.reader.karaoke,
                  onChanged: (enabled) {
                    ref.read(settingsProvider.notifier).updateReader(
                          value.reader.copyWith(karaoke: enabled),
                        );
                  },
                ),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Avanzar al terminar'),
                  subtitle: const Text('Pasar al capítulo siguiente cuando termina el audio.'),
                  value: value.reader.autoAdvance,
                  onChanged: (enabled) {
                    ref.read(settingsProvider.notifier).updateReader(
                          value.reader.copyWith(autoAdvance: enabled),
                        );
                  },
                ),
              ],
            ),
            const SizedBox(height: 20),
            _SettingsSection(
              title: 'Biblioteca',
              children: [
                _SettingsRow(
                  title: 'Carpeta de libros',
                  subtitle: value.libraryPath ?? 'Detección automática',
                  trailing: Wrap(
                    spacing: 8,
                    children: [
                      OutlinedButton(
                        onPressed: () async {
                          final path = await getDirectoryPath();
                          if (path != null) {
                            await ref.read(settingsProvider.notifier).setLibraryPath(path);
                          }
                        },
                        child: const Text('Elegir'),
                      ),
                      if (value.libraryPath != null)
                        TextButton(
                          onPressed: () => ref.read(settingsProvider.notifier).setLibraryPath(null),
                          child: const Text('Automática'),
                        ),
                    ],
                  ),
                ),
                Text(
                  'La biblioteca no se mueve ni se borra al cambiar esta preferencia.',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
            const SizedBox(height: 20),
            _SettingsSection(
              title: 'Voz',
              children: [
                _SettingsRow(
                  title: 'Carpeta de modelos',
                  subtitle: value.modelsPath ?? 'Carpeta de la app',
                  trailing: Wrap(
                    spacing: 8,
                    children: [
                      OutlinedButton(
                        onPressed: () async {
                          final path = await getDirectoryPath();
                          if (path != null) {
                            await ref.read(settingsProvider.notifier).setModelsPath(path);
                          }
                        },
                        child: const Text('Elegir'),
                      ),
                      if (value.modelsPath != null)
                        TextButton(
                          onPressed: () => ref.read(settingsProvider.notifier).setModelsPath(null),
                          child: const Text('Automática'),
                        ),
                    ],
                  ),
                ),
                Text(
                  'Los modelos Piper se detectan en subcarpetas con .onnx y tokens.txt. '
                  'También podés descargarlos desde el Estudio.',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
            const SizedBox(height: 20),
            _SettingsSection(
              title: 'Ambiente',
              children: [
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Ambiente en el lector'),
                  subtitle: const Text('Sonido de fondo mientras leés o escuchás.'),
                  value: value.ambienceEnabled,
                  onChanged: (enabled) {
                    ref.read(settingsProvider.notifier).updateAmbience(enabled: enabled);
                  },
                ),
                _SettingsRow(
                  title: 'Sonido',
                  subtitle: AmbiencePresetDetails.byId(value.ambiencePreset).description,
                  trailing: DropdownButton<String>(
                    value: value.ambiencePreset,
                    underline: const SizedBox.shrink(),
                    items: [
                      for (final preset in AmbiencePreset.values)
                        DropdownMenuItem(value: preset.id, child: Text(preset.label)),
                    ],
                    onChanged: (preset) {
                      if (preset != null) {
                        ref.read(settingsProvider.notifier).updateAmbience(preset: preset);
                      }
                    },
                  ),
                ),
                _SettingsRow(
                  title: 'Volumen',
                  subtitle: '${(value.ambienceVolume * 100).round()}%',
                  trailing: SizedBox(
                    width: 220,
                    child: Slider(
                      value: value.ambienceVolume,
                      min: 0,
                      max: 1,
                      divisions: 20,
                      label: '${(value.ambienceVolume * 100).round()}%',
                      onChanged: (volume) {
                        ref.read(settingsProvider.notifier).updateAmbience(volume: volume);
                      },
                    ),
                  ),
                ),
                _SettingsRow(
                  title: 'Atenuación con la voz',
                  subtitle: '${(value.ambienceDucking * 100).round()}% del volumen',
                  trailing: SizedBox(
                    width: 220,
                    child: Slider(
                      value: value.ambienceDucking,
                      min: 0,
                      max: 1,
                      divisions: 20,
                      label: '${(value.ambienceDucking * 100).round()}%',
                      onChanged: (ducking) {
                        ref.read(settingsProvider.notifier).updateAmbience(ducking: ducking);
                      },
                    ),
                  ),
                ),
                Text(
                  'Los paisajes sonoros se sintetizan localmente y se guardan en la app. '
                  'No se descargan muestras externas.',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
            const SizedBox(height: 20),
            _SettingsSection(
              title: 'Acerca de',
              children: [
                FutureBuilder<PackageInfo>(
                  future: PackageInfo.fromPlatform(),
                  builder: (context, snapshot) {
                    final info = snapshot.data;
                    return _SettingsRow(
                      title: 'Vibebook',
                      subtitle: info == null ? 'Flutter' : 'Versión ${info.version} (${info.buildNumber})',
                      trailing: StatusPill(label: 'FLUTTER', color: colors.accent),
                    );
                  },
                ),
                const SizedBox(height: 8),
                Text(
                  'AGPL-3.0-only. La biblioteca y la lectura funcionan sin cuenta ni nube.',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ],
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (error, stackTrace) => ErrorView(message: '$error'),
      ),
    );
  }
}

class _SettingsSection extends StatelessWidget {
  const _SettingsSection({required this.title, required this.children});

  final String title;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<BibliotecaColors>()!;
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: colors.surface,
        border: Border.all(color: colors.line),
        borderRadius: BibliotecaRadii.md,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SectionLabel(title),
          const SizedBox(height: 10),
          ...children,
        ],
      ),
    );
  }
}

class _SettingsRow extends StatelessWidget {
  const _SettingsRow({required this.title, required this.subtitle, this.trailing});

  final String title;
  final String subtitle;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: Theme.of(context).textTheme.titleSmall),
                const SizedBox(height: 2),
                Text(subtitle, style: Theme.of(context).textTheme.bodySmall),
              ],
            ),
          ),
          if (trailing != null) ...[
            const SizedBox(width: 16),
            trailing!,
          ],
        ],
      ),
    );
  }
}

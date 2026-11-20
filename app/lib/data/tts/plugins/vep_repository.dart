import 'dart:convert';
import 'dart:io';

import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import 'vep_client.dart';

/// Persists VEP plugins and their tokens in the app data directory.
class VepPluginRepository {
  VepPluginRepository({
    required this.client,
    File? pluginsFile,
    File? secretsFile,
    Future<Directory> Function()? supportDirectory,
  }) : _pluginsFile = pluginsFile, // ignore: prefer_initializing_formals
       _secretsFile = secretsFile, // ignore: prefer_initializing_formals
       _supportDirectory = supportDirectory ?? getApplicationSupportDirectory;

  final VepClient client;
  final File? _pluginsFile;
  final File? _secretsFile;
  final Future<Directory> Function() _supportDirectory;
  File? _resolvedPlugins;
  File? _resolvedSecrets;

  Future<File> _plugins() async {
    if (_pluginsFile != null) {
      return _pluginsFile;
    }
    if (_resolvedPlugins != null) {
      return _resolvedPlugins!;
    }
    final directory = await _supportDirectory();
    return _resolvedPlugins = File(p.join(directory.path, 'plugins.json'));
  }

  Future<File> _secrets() async {
    if (_secretsFile != null) {
      return _secretsFile;
    }
    if (_resolvedSecrets != null) {
      return _resolvedSecrets!;
    }
    final directory = await _supportDirectory();
    return _resolvedSecrets = File(
      p.join(directory.path, 'plugin-secrets.json'),
    );
  }

  Future<List<VepPlugin>> list() async {
    final file = await _plugins();
    if (!await file.exists()) {
      return <VepPlugin>[];
    }
    try {
      final decoded = jsonDecode(await file.readAsString());
      if (decoded is! Map<String, dynamic>) {
        return <VepPlugin>[];
      }
      final raw = decoded['items'];
      if (raw is! List) {
        return <VepPlugin>[];
      }
      final plugins = <VepPlugin>[];
      for (final item in raw) {
        if (item is Map<String, dynamic> && item['id'] is String) {
          plugins.add(VepPlugin.fromJson(item));
        }
      }
      return plugins;
    } on FormatException {
      return <VepPlugin>[];
    } on FileSystemException {
      return <VepPlugin>[];
    }
  }

  Future<VepPlugin> add(String url, {String? token}) async {
    final info = await client.fetchInfo(url, token: token);
    final plugins = await list();
    final existing = plugins.indexWhere((plugin) => plugin.id == info.id);
    final plugin = info.copyWith(
      tokenSet: token != null && token.trim().isNotEmpty,
    );
    if (existing >= 0) {
      plugins[existing] = plugin;
    } else {
      plugins.add(plugin);
    }
    await _writePlugins(plugins);
    if (token != null && token.trim().isNotEmpty) {
      await _writeSecret(info.id, token.trim());
    }
    return plugin;
  }

  Future<void> remove(String id) async {
    final plugins = await list();
    plugins.removeWhere((plugin) => plugin.id == id);
    await _writePlugins(plugins);
    await _removeSecret(id);
  }

  Future<String?> token(String id) async {
    final file = await _secrets();
    if (!await file.exists()) {
      return null;
    }
    try {
      final decoded = jsonDecode(await file.readAsString());
      if (decoded is Map<String, dynamic> && decoded[id] is String) {
        return decoded[id] as String;
      }
    } on FormatException {
      return null;
    } on FileSystemException {
      return null;
    }
    return null;
  }

  Future<VepTestResult> test(String id) async {
    final plugins = await list();
    VepPlugin? plugin;
    for (final item in plugins) {
      if (item.id == id) {
        plugin = item;
        break;
      }
    }
    if (plugin == null) {
      return const VepTestResult(ok: false, message: 'El plugin no existe.');
    }
    try {
      await client.test(plugin.url, token: await token(id));
      return VepTestResult(
        ok: true,
        message: 'Conectado. ${plugin.voices.length} voces disponibles.',
      );
    } catch (error) {
      return VepTestResult(ok: false, message: '$error');
    }
  }

  Future<void> _writePlugins(List<VepPlugin> plugins) async {
    final file = await _plugins();
    await file.parent.create(recursive: true);
    final temporary = File('${file.path}.part');
    try {
      await temporary.writeAsString(
        const JsonEncoder.withIndent('  ').convert({
          'version': 1,
          'items': plugins.map((plugin) => plugin.toJson()).toList(),
        }),
        flush: true,
      );
      if (await file.exists()) {
        await file.delete();
      }
      await temporary.rename(file.path);
    } finally {
      if (await temporary.exists()) {
        await temporary.delete();
      }
    }
  }

  Future<void> _writeSecret(String id, String token) async {
    final file = await _secrets();
    await file.parent.create(recursive: true);
    Map<String, dynamic> payload = {};
    if (await file.exists()) {
      try {
        final decoded = jsonDecode(await file.readAsString());
        if (decoded is Map<String, dynamic>) {
          payload = decoded;
        }
      } on FormatException {
        payload = {};
      }
    }
    payload[id] = token;
    final temporary = File('${file.path}.part');
    try {
      await temporary.writeAsString(
        const JsonEncoder.withIndent('  ').convert(payload),
        flush: true,
      );
      if (await file.exists()) {
        await file.delete();
      }
      await temporary.rename(file.path);
      if (!Platform.isWindows) {
        await Process.run('chmod', ['600', file.path]);
      }
    } finally {
      if (await temporary.exists()) {
        await temporary.delete();
      }
    }
  }

  Future<void> _removeSecret(String id) async {
    final file = await _secrets();
    if (!await file.exists()) {
      return;
    }
    try {
      final decoded = jsonDecode(await file.readAsString());
      if (decoded is! Map<String, dynamic> || !decoded.containsKey(id)) {
        return;
      }
      decoded.remove(id);
      await file.writeAsString(
        const JsonEncoder.withIndent('  ').convert(decoded),
        flush: true,
      );
    } on FormatException {
      return;
    }
  }
}

class VepTestResult {
  const VepTestResult({required this.ok, required this.message});

  final bool ok;
  final String message;
}

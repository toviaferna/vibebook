import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../domain/models.dart';

class SettingsRepository {
  SettingsRepository({SharedPreferences? preferences}) {
    _preferences = preferences;
  }

  static const _key = 'vibebook.settings.v1';
  SharedPreferences? _preferences;

  Future<SharedPreferences> get _prefs async {
    return _preferences ??= await SharedPreferences.getInstance();
  }

  Future<AppSettings> load() async {
    final prefs = await _prefs;
    final raw = prefs.getString(_key);
    if (raw == null || raw.isEmpty) {
      return const AppSettings();
    }
    try {
      final decoded = jsonDecode(raw);
      if (decoded is Map<String, dynamic>) {
        return AppSettings.fromJson(decoded);
      }
    } on FormatException {
      // Corrupt settings should not prevent the app from starting.
    }
    return const AppSettings();
  }

  Future<void> save(AppSettings settings) async {
    final prefs = await _prefs;
    await prefs.setString(_key, jsonEncode(settings.toJson()));
  }
}

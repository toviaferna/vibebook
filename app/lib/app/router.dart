import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/book_detail/book_detail_page.dart';
import '../features/import/import_page.dart';
import '../features/library/library_page.dart';
import '../features/reader/reader_page.dart';
import '../features/settings/settings_page.dart';
import '../features/studio/studio_page.dart';
import 'app_shell.dart';

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/',
    routes: [
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) {
          return AppShell(navigationShell: navigationShell);
        },
        branches: [
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/',
                builder: (context, state) => const LibraryPage(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/import',
                builder: (context, state) => const ImportPage(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/settings',
                builder: (context, state) => const SettingsPage(),
              ),
            ],
          ),
        ],
      ),
      GoRoute(
        path: '/books/:id',
        builder: (context, state) =>
            BookDetailPage(bookId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: '/books/:id/studio',
        builder: (context, state) =>
            StudioPage(bookId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: '/books/:id/read',
        builder: (context, state) =>
            ReaderPage(bookId: state.pathParameters['id']!),
      ),
    ],
  );
});

import 'package:material_ui/material_ui.dart';
import 'package:go_router/go_router.dart';

import '../core/design/tokens.dart';

class AppShell extends StatelessWidget {
  const AppShell({super.key, required this.navigationShell});

  final StatefulNavigationShell navigationShell;

  static const _destinations = [
    _Destination('Biblioteca', Icons.local_library_outlined, Icons.local_library),
    _Destination('Importar', Icons.add_circle_outline, Icons.add_circle),
    _Destination('Ajustes', Icons.tune_outlined, Icons.tune),
  ];

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<BibliotecaColors>()!;
    final width = MediaQuery.sizeOf(context).width;
    final desktop = width >= 840;
    if (desktop) {
      return Scaffold(
        body: Row(
          children: [
            _Sidebar(
              selectedIndex: navigationShell.currentIndex,
              onSelect: (index) => navigationShell.goBranch(index, initialLocation: index == navigationShell.currentIndex),
            ),
            Expanded(child: navigationShell),
          ],
        ),
      );
    }
    return Scaffold(
      body: navigationShell,
      bottomNavigationBar: NavigationBar(
        selectedIndex: navigationShell.currentIndex,
        onDestinationSelected: (index) => navigationShell.goBranch(index, initialLocation: index == navigationShell.currentIndex),
        backgroundColor: colors.surface,
        indicatorColor: colors.accentSoft,
        destinations: [
          for (final destination in _destinations)
            NavigationDestination(
              icon: Icon(destination.icon),
              selectedIcon: Icon(destination.selectedIcon, color: colors.accent),
              label: destination.label,
            ),
        ],
      ),
    );
  }
}

class _Sidebar extends StatelessWidget {
  const _Sidebar({required this.selectedIndex, required this.onSelect});

  final int selectedIndex;
  final ValueChanged<int> onSelect;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<BibliotecaColors>()!;
    return Container(
      width: 264,
      decoration: BoxDecoration(
        color: colors.paperDeep,
        border: Border(right: BorderSide(color: colors.line)),
      ),
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 24, 20, 20),
              child: Row(
                children: [
                  Container(
                    width: 42,
                    height: 42,
                    decoration: BoxDecoration(
                      color: colors.ink,
                      borderRadius: BibliotecaRadii.md,
                    ),
                    child: Icon(Icons.menu_book, color: colors.paper),
                  ),
                  const SizedBox(width: 12),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Vibebook', style: Theme.of(context).textTheme.titleLarge),
                      Text(
                        'BIBLIOTECA',
                        style: Theme.of(context).textTheme.labelSmall?.copyWith(
                              letterSpacing: 1.8,
                            ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            Divider(color: colors.line),
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 16, 12, 8),
              child: Text('NAVEGAR', style: Theme.of(context).textTheme.labelSmall),
            ),
            for (var index = 0; index < AppShell._destinations.length; index++)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 2),
                child: Material(
                  color: selectedIndex == index ? colors.surfaceRaised : Colors.transparent,
                  borderRadius: BibliotecaRadii.md,
                  child: InkWell(
                    borderRadius: BibliotecaRadii.md,
                    onTap: () => onSelect(index),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                      child: Row(
                        children: [
                          Icon(
                            selectedIndex == index
                                ? AppShell._destinations[index].selectedIcon
                                : AppShell._destinations[index].icon,
                            size: 20,
                            color: selectedIndex == index ? colors.accent : colors.inkSoft,
                          ),
                          const SizedBox(width: 12),
                          Text(
                            AppShell._destinations[index].label,
                            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                  color: selectedIndex == index ? colors.ink : colors.inkSoft,
                                  fontWeight: selectedIndex == index ? FontWeight.w600 : FontWeight.w500,
                                ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            const Spacer(),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: colors.surface,
                  border: Border(left: BorderSide(color: colors.brass, width: 2)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Lector local', style: Theme.of(context).textTheme.titleSmall),
                    const SizedBox(height: 4),
                    Text(
                      'Tu biblioteca vive en este equipo. Sin cuenta, sin nube.',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Destination {
  const _Destination(this.label, this.icon, this.selectedIcon);

  final String label;
  final IconData icon;
  final IconData selectedIcon;
}

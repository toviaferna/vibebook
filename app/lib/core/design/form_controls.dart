import 'dart:math' as math;

import 'package:collection/collection.dart';
import 'package:material_ui/material_ui.dart';

import 'tokens.dart';

class BibliotecaSelectOption<T> {
  const BibliotecaSelectOption({
    required this.value,
    required this.label,
    this.description,
    this.leading,
  });

  final T value;
  final String label;
  final String? description;
  final Widget? leading;
}

/// A compact, themed select that never lets a menu inherit the full page
/// width. On narrow windows it opens a bottom sheet instead.
class BibliotecaSelect<T> extends StatefulWidget {
  const BibliotecaSelect({
    super.key,
    required this.label,
    required this.value,
    required this.options,
    required this.onChanged,
    this.hint = 'Elegir…',
    this.helper,
    this.error,
    this.enabled = true,
    this.menuMaxHeight = 320,
    this.showLabel = true,
  });

  final String label;
  final T? value;
  final List<BibliotecaSelectOption<T>> options;
  final ValueChanged<T>? onChanged;
  final String hint;
  final String? helper;
  final String? error;
  final bool enabled;
  final double menuMaxHeight;
  final bool showLabel;

  @override
  State<BibliotecaSelect<T>> createState() => _BibliotecaSelectState<T>();
}

class _BibliotecaSelectState<T> extends State<BibliotecaSelect<T>> {
  final _anchorKey = GlobalKey();
  bool _focused = false;

  BibliotecaSelectOption<T>? get _selected {
    return widget.options.firstWhereOrNull(
      (option) => option.value == widget.value,
    );
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<BibliotecaColors>()!;
    final selected = _selected;
    final borderColor = widget.error != null
        ? colors.danger
        : _focused
        ? colors.focus
        : colors.line;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (widget.showLabel) ...[
          Text(widget.label, style: Theme.of(context).textTheme.labelMedium),
          const SizedBox(height: 6),
        ],
        Semantics(
          button: true,
          enabled: widget.enabled,
          label: '${widget.label}: ${selected?.label ?? widget.hint}',
          child: FocusableActionDetector(
            enabled: widget.enabled,
            onFocusChange: (value) => setState(() => _focused = value),
            child: Material(
              color: colors.surfaceRaised,
              borderRadius: BibliotecaRadii.md,
              child: InkWell(
                borderRadius: BibliotecaRadii.md,
                onTap: widget.enabled ? _open : null,
                child: Container(
                  key: _anchorKey,
                  height: 48,
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  decoration: BoxDecoration(
                    borderRadius: BibliotecaRadii.md,
                    border: Border.all(
                      color: borderColor,
                      width: _focused ? 2 : 1,
                    ),
                  ),
                  child: Row(
                    children: [
                      if (selected?.leading != null) ...[
                        selected!.leading!,
                        const SizedBox(width: 8),
                      ],
                      Expanded(
                        child: Text(
                          selected?.label ?? widget.hint,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(context).textTheme.bodyMedium
                              ?.copyWith(
                                color: selected == null
                                    ? colors.inkFaint
                                    : widget.enabled
                                    ? colors.ink
                                    : colors.inkFaint,
                              ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Icon(
                        Icons.expand_more,
                        size: 18,
                        color: widget.enabled
                            ? colors.inkSoft
                            : colors.inkFaint,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
        if (widget.error != null) ...[
          const SizedBox(height: 6),
          Text(
            widget.error!,
            style: Theme.of(context).textTheme.bodySmall
                ?.copyWith(color: colors.danger),
          ),
        ] else if (widget.helper != null) ...[
          const SizedBox(height: 6),
          Text(widget.helper!, style: Theme.of(context).textTheme.bodySmall),
        ],
      ],
    );
  }

  Future<void> _open() async {
    if (_selected == null && widget.options.isEmpty) {
      return;
    }
    final selected = MediaQuery.sizeOf(context).width < 600
        ? await _openSheet()
        : await _openMenu();
    if (selected != null) {
      widget.onChanged?.call(selected);
    }
  }

  Future<T?> _openMenu() async {
    final colors = Theme.of(context).extension<BibliotecaColors>()!;
    final box = _anchorKey.currentContext?.findRenderObject() as RenderBox?;
    final overlay =
        Navigator.of(context).overlay?.context.findRenderObject() as RenderBox?;
    if (box == null || overlay == null || !box.hasSize) {
      return null;
    }
    final origin = box.localToGlobal(Offset.zero, ancestor: overlay);
    final bottomRight = box.localToGlobal(
      box.size.bottomRight(Offset.zero),
      ancestor: overlay,
    );
    final width = math.min(math.max(box.size.width, 240.0), 420.0);
    return showMenu<T>(
      context: context,
      position: RelativeRect.fromRect(
        Rect.fromPoints(origin, bottomRight),
        Offset.zero & overlay.size,
      ),
      color: colors.surfaceRaised,
      elevation: 10,
      shape: RoundedRectangleBorder(
        borderRadius: BibliotecaRadii.md,
        side: BorderSide(color: colors.line),
      ),
      constraints: BoxConstraints(
        minWidth: width,
        maxWidth: width,
        maxHeight: widget.menuMaxHeight,
      ),
      items: [
        for (final option in widget.options)
          PopupMenuItem<T>(
            value: option.value,
            height: option.description == null ? 44 : 58,
            padding: const EdgeInsets.symmetric(horizontal: 10),
            child: Row(
              children: [
                if (option.leading != null) ...[
                  option.leading!,
                  const SizedBox(width: 10),
                ],
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        option.label,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: colors.ink,
                          fontWeight: option.value == widget.value
                              ? FontWeight.w600
                              : FontWeight.w400,
                        ),
                      ),
                      if (option.description != null) ...[
                        const SizedBox(height: 2),
                        Text(
                          option.description!,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ],
                  ),
                ),
                if (option.value == widget.value)
                  Icon(Icons.check, size: 18, color: colors.accent),
              ],
            ),
          ),
      ],
    );
  }

  Future<T?> _openSheet() async {
    final colors = Theme.of(context).extension<BibliotecaColors>()!;
    return showModalBottomSheet<T>(
      context: context,
      isScrollControlled: true,
      backgroundColor: colors.surface,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(8)),
      ),
      builder: (context) {
        return SafeArea(
          child: ConstrainedBox(
            constraints: BoxConstraints(
              maxHeight: MediaQuery.sizeOf(context).height * 0.72,
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 16, 12, 8),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          widget.label,
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                      ),
                      IconButton(
                        tooltip: 'Cerrar',
                        onPressed: () => Navigator.of(context).pop(),
                        icon: const Icon(Icons.close),
                      ),
                    ],
                  ),
                ),
                Divider(color: colors.line, height: 1),
                Flexible(
                  child: ListView.builder(
                    shrinkWrap: true,
                    itemCount: widget.options.length,
                    itemBuilder: (context, index) {
                      final option = widget.options[index];
                      final active = option.value == widget.value;
                      return ListTile(
                        leading: option.leading,
                        title: Text(option.label),
                        subtitle: option.description == null
                            ? null
                            : Text(option.description!),
                        trailing: active
                            ? Icon(Icons.check, color: colors.accent)
                            : null,
                        selected: active,
                        onTap: () => Navigator.of(context).pop(option.value),
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

class BibliotecaSection extends StatelessWidget {
  const BibliotecaSection({
    super.key,
    required this.title,
    required this.child,
    this.description,
    this.actions = const [],
    this.padding = const EdgeInsets.all(20),
  });

  final String title;
  final String? description;
  final Widget child;
  final List<Widget> actions;
  final EdgeInsets padding;

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).extension<BibliotecaColors>()!;
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: colors.surface,
        border: Border.all(color: colors.line),
        borderRadius: BibliotecaRadii.md,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          LayoutBuilder(
            builder: (context, constraints) {
              final titleBlock = Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title.toUpperCase(),
                    style: Theme.of(context).textTheme.labelSmall,
                  ),
                  if (description != null) ...[
                    const SizedBox(height: 4),
                    Text(
                      description!,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ],
              );
              if (constraints.maxWidth < 560) {
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    titleBlock,
                    if (actions.isNotEmpty) ...[
                      const SizedBox(height: 10),
                      Wrap(spacing: 8, runSpacing: 8, children: actions),
                    ],
                  ],
                );
              }
              return Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(child: titleBlock),
                  if (actions.isNotEmpty) ...[
                    const SizedBox(width: 12),
                    Wrap(spacing: 8, runSpacing: 8, children: actions),
                  ],
                ],
              );
            },
          ),
          const SizedBox(height: 14),
          child,
        ],
      ),
    );
  }
}

class BibliotecaFormRow extends StatelessWidget {
  const BibliotecaFormRow({
    super.key,
    required this.title,
    required this.child,
    this.subtitle,
    this.controlWidth,
  });

  final String title;
  final String? subtitle;
  final Widget child;
  final double? controlWidth;

  @override
  Widget build(BuildContext context) {
    final text = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: Theme.of(context).textTheme.titleSmall),
        if (subtitle != null) ...[
          const SizedBox(height: 2),
          Text(subtitle!, style: Theme.of(context).textTheme.bodySmall),
        ],
      ],
    );
    return LayoutBuilder(
      builder: (context, constraints) {
        final control = controlWidth == null
            ? child
            : ConstrainedBox(
                constraints: BoxConstraints(maxWidth: controlWidth!),
                child: child,
              );
        if (constraints.maxWidth < 560) {
          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [text, const SizedBox(height: 10), control],
            ),
          );
        }
        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Expanded(child: text),
              const SizedBox(width: 20),
              control,
            ],
          ),
        );
      },
    );
  }
}

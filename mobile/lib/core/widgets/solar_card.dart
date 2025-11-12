import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../constants/app_constants.dart';

class SolarCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final EdgeInsetsGeometry? margin;
  final Color? color;
  final VoidCallback? onTap;
  final double? elevation;

  const SolarCard({
    required this.child,
    this.padding,
    this.margin,
    this.color,
    this.onTap,
    this.elevation,
    Key? key,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final card = Card(
      elevation: elevation ?? AppConstants.cardElevation,
      color: color,
      margin: margin ?? const EdgeInsets.symmetric(
        horizontal: AppConstants.defaultPadding,
        vertical: AppConstants.smallPadding,
      ),
      child: Padding(
        padding: padding ?? const EdgeInsets.all(AppConstants.defaultPadding),
        child: child,
      ),
    );

    if (onTap != null) {
      return InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppConstants.borderRadius),
        child: card,
      );
    }

    return card;
  }
}

class SolarInfoCard extends StatelessWidget {
  final String title;
  final String value;
  final String? subtitle;
  final IconData? icon;
  final Color? iconColor;
  final VoidCallback? onTap;

  const SolarInfoCard({
    required this.title,
    required this.value,
    this.subtitle,
    this.icon,
    this.iconColor,
    this.onTap,
    Key? key,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return SolarCard(
      onTap: onTap,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              if (icon != null) ...[
                Icon(
                  icon,
                  color: iconColor ?? theme.colorScheme.primary,
                  size: 24,
                ),
                const SizedBox(width: AppConstants.smallPadding),
              ],
              Expanded(
                child: Text(
                  title,
                  style: theme.textTheme.titleSmall?.copyWith(
                    color: theme.textTheme.bodySmall?.color,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppConstants.smallPadding),
          Text(
            value,
            style: theme.textTheme.headlineMedium?.copyWith(
              fontWeight: FontWeight.bold,
              color: theme.colorScheme.primary,
            ),
          ),
          if (subtitle != null) ...[
            const SizedBox(height: 4),
            Text(
              subtitle!,
              style: theme.textTheme.bodySmall,
            ),
          ],
        ],
      ),
    );
  }
}

class SolarStatusCard extends StatelessWidget {
  final String activityLevel;
  final double sunspotNumber;
  final double solarFlux;
  final double kpIndex;

  const SolarStatusCard({
    required this.activityLevel,
    required this.sunspotNumber,
    required this.solarFlux,
    required this.kpIndex,
    Key? key,
  }) : super(key: key);

  Color _getActivityColor() {
    switch (activityLevel.toLowerCase()) {
      case 'low':
        return AppColors.solarLow;
      case 'moderate':
        return AppColors.solarModerate;
      case 'high':
        return AppColors.solarHigh;
      case 'very high':
        return AppColors.solarVeryHigh;
      case 'extreme':
        return AppColors.solarExtreme;
      default:
        return AppColors.solarModerate;
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final activityColor = _getActivityColor();

    return SolarCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Solar Activity',
                style: theme.textTheme.titleLarge,
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: activityColor.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  activityLevel,
                  style: theme.textTheme.labelMedium?.copyWith(
                    color: activityColor,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppConstants.defaultPadding),
          Row(
            children: [
              Expanded(
                child: _buildMetric(
                  context,
                  'Sunspot Number',
                  sunspotNumber.toStringAsFixed(1),
                  Icons.wb_sunny,
                ),
              ),
              Expanded(
                child: _buildMetric(
                  context,
                  'Solar Flux',
                  solarFlux.toStringAsFixed(1),
                  Icons.radar,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppConstants.defaultPadding),
          _buildMetric(
            context,
            'Kp Index',
            kpIndex.toStringAsFixed(1),
            Icons.language,
          ),
        ],
      ),
    );
  }

  Widget _buildMetric(
    BuildContext context,
    String label,
    String value,
    IconData icon,
  ) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(
              icon,
              size: 16,
              color: theme.textTheme.bodySmall?.color,
            ),
            const SizedBox(width: 4),
            Text(
              label,
              style: theme.textTheme.bodySmall,
            ),
          ],
        ),
        const SizedBox(height: 4),
        Text(
          value,
          style: theme.textTheme.titleLarge?.copyWith(
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }
}

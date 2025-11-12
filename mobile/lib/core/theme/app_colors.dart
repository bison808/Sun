import 'package:flutter/material.dart';

class AppColors {
  // Private constructor to prevent instantiation
  AppColors._();

  // Light Theme Colors
  static const Color primaryLight = Color(0xFFFF6B35);  // Solar orange
  static const Color secondaryLight = Color(0xFF004E89);  // Deep space blue
  static const Color tertiaryLight = Color(0xFF1A659E);  // Sky blue
  static const Color surfaceLight = Color(0xFFFAFAFA);
  static const Color backgroundLight = Color(0xFFFFFFFF);
  static const Color errorLight = Color(0xFFD32F2F);
  static const Color successLight = Color(0xFF388E3C);
  static const Color warningLight = Color(0xFFFFA000);

  // Dark Theme Colors
  static const Color primaryDark = Color(0xFFFF8A5C);  // Lighter solar orange
  static const Color secondaryDark = Color(0xFF1E88E5);  // Lighter blue
  static const Color tertiaryDark = Color(0xFF42A5F5);  // Light sky blue
  static const Color surfaceDark = Color(0xFF1E1E1E);
  static const Color backgroundDark = Color(0xFF121212);
  static const Color errorDark = Color(0xFFEF5350);
  static const Color successDark = Color(0xFF66BB6A);
  static const Color warningDark = Color(0xFFFFB74D);

  // Solar Activity Level Colors
  static const Color solarLow = Color(0xFF4CAF50);  // Green
  static const Color solarModerate = Color(0xFFFFEB3B);  // Yellow
  static const Color solarHigh = Color(0xFFFF9800);  // Orange
  static const Color solarVeryHigh = Color(0xFFFF5722);  // Deep orange
  static const Color solarExtreme = Color(0xFFD32F2F);  // Red

  // Chart Colors
  static const List<Color> chartColors = [
    Color(0xFFFF6B35),  // Orange
    Color(0xFF004E89),  // Blue
    Color(0xFF1A659E),  // Light blue
    Color(0xFFF77F00),  // Yellow-orange
    Color(0xFF06A77D),  // Teal
    Color(0xFF9D4EDD),  // Purple
  ];

  // Gradient Colors
  static const List<Color> solarGradient = [
    Color(0xFFFF6B35),
    Color(0xFFF77F00),
  ];

  static const List<Color> spaceGradient = [
    Color(0xFF004E89),
    Color(0xFF1A659E),
  ];

  // Text Colors
  static const Color textPrimaryLight = Color(0xFF212121);
  static const Color textSecondaryLight = Color(0xFF757575);
  static const Color textPrimaryDark = Color(0xFFFFFFFF);
  static const Color textSecondaryDark = Color(0xFFBDBDBD);

  // Divider Colors
  static const Color dividerLight = Color(0xFFE0E0E0);
  static const Color dividerDark = Color(0xFF424242);
}

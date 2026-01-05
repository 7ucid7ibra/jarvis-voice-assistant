#!/usr/bin/env python3

import os
import sys
from pathlib import Path
from dmgbuild import build_dmg

def create_dmg():
    # Define paths
    project_root = Path(__file__).parent.parent
    app_bundle = project_root / "build" / "dist" / "Jarvis Assistant.app"
    dmg_output = project_root / "Jarvis Assistant.dmg"

    # DMG settings
    volume_name = "Jarvis Assistant"
    size = "200M"  # 200MB should be enough

    # Create DMG with custom settings
    build_dmg(
        filename=str(dmg_output),
        volume_name=volume_name,
        settings={
            'size': size,
            'files': [str(app_bundle)],
            'symlinks': { 'Applications': '/Applications' },
            'badge_icon': str(app_bundle / 'Contents' / 'Resources' / 'icon.icns'),
            'icon_locations': {
                'Jarvis Assistant.app': (140, 120),
                'Applications': (360, 120)
            },
            'background': None,  # Could add a background image later
            'show_status_bar': False,
            'show_tab_view': False,
            'show_toolbar': False,
            'show_pathbar': False,
            'show_sidebar': False,
            'sidebar_width': 180,
            'window_rect': ((100, 100), (400, 200)),  # Window position and size
            'default_view': 'icon-view',
            'show_icon_preview': False,
            'include_icon_view_settings': 'auto',
            'include_list_view_settings': 'auto',
            'arrange_by': None,
            'grid_offset': (0, 0),
            'grid_spacing': 100,
            'scroll_position': (0, 0),
            'label_pos': 'bottom',
            'text_size': 12,
            'icon_size': 64,
            'show_item_info': False,
            'show_empty_dirs': False,
        }
    )

    print(f"DMG created successfully: {dmg_output}")

if __name__ == "__main__":
    create_dmg()
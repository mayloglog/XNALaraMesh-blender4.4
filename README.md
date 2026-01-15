XPS Tools 
=========

Fork of XNALara Mesh import/export tool with Blender 5.0 compatibility.

Since the original author (johnzero7) has not updated the code for five years as of 2025, the old version of the plugin can no longer run on the new version of Blender. Therefore, I will maintain this version going forward.

Original addon by XNALara community.

With Blender 4.40 released there where many changes.

From v2.1.0 of this addon will only work with Blender 4.4.
From v2.2.0 of this addon will only work with Blender 5.0.

- Blender 5.00 ==> v2.2.0+
- Blender 4.40 ==> v2.1.0

Blender Toolshelf, an addon for Blender to:

Import/Export XPS Models, Poses.

Main Features:
- Imports and Exports XPS/XNALara models with armature.
- Imports and Exports Poses
- Imports and Exports Custom Normals
- Creates Materials on import
- Easily set a new rest pose for the model

### Known Issues

- Summary: Due to critical compatibility issues with the XPS binary format, I have disabled the native .xps binary export. The exporter now redirects to ASCII format by default, which ensures perfect compatibility and stability.

- Technical Details: The current mock_xps_data.py lacks the necessary file header logic. After I manually attempted to implement the header construction, it resulted in severe byte misalignment. While the file is generated, the scene appears empty upon re-import.
The XPS format requires strict alignment for the 1080-byte Settings Block. Due to changes in Blender 5.0's I/O handling, the logic that worked in older versions now causes offset shifts. As an individual developer, the binary structure of XPS remains a "black box" to me, and my current technical skills are insufficient to perform the precise byte-level adjustments required to fix this.

- Call for Help: I welcome any experienced developers to help fix this alignment issue. If you can resolve the binary header construction for Blender 5.0, please submit a Pull Request on GitHub. Thank you for your support!

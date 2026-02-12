# Simple Media Player v2 - Development Guide

This document provides comprehensive instructions for setting up the development environment, building the application, and deploying the Simple Media Player v2 project.

<details>
<summary><h2>Developer Setup Guide</h2></summary>

This guide outlines the essential steps to prepare a new development machine for contributing to or working with this project.

### Prerequisites

Ensure the following software components are installed on your system:

1.  **Git:**
    *   Version control system required for cloning the project repository.
    *   [Download Git](https://git-scm.com/downloads)
2.  **C++ Compiler:**
    *   **Windows:** Visual Studio (Community Edition or higher) with the "Desktop development with C++" workload selected during installation.
    *   **Linux/macOS:** GCC or Clang, typically available through system package managers (e.g., `build-essential` on Debian/Ubuntu, Xcode Command Line Tools on macOS).
3.  **CMake:**
    *   Cross-platform build system generator.
    *   [Download CMake](https://cmake.org/download/)
4.  **vcpkg:**
    *   C++ package manager for acquiring and managing project dependencies.
    *   Follow the [vcpkg Quick Start Guide](https://vcpkg.io/en/getting-started.html) for initial setup (cloning the repository and running the bootstrap script).
5.  **Integrated Development Environment (IDE) - Optional but Recommended:**
    *   Visual Studio (for Windows development)
    *   VS Code (with CMake Tools extension)
    *   Qt Creator (natively supports Qt and CMake projects)

### 1. Clone the Repository

Initiate the project setup by cloning the repository from its source:

```bash
git clone <your_repository_url>
cd simple-media-player-v2
```

### 2. Integrate vcpkg with CMake

This step establishes the necessary integration between vcpkg and CMake, allowing CMake to locate and utilize packages installed via vcpkg. This is typically a one-time configuration per development machine.

```bash
<path_to_vcpkg>/vcpkg integrate install
```
Replace `<path_to_vcpkg>` with the absolute path to your vcpkg installation directory (e.g., `C:\vcpkg`).

### 3. Configure CMake Project

Create a dedicated build directory and configure the project using CMake. During this configuration, CMake will read the `vcpkg.json` manifest to identify and install required dependencies (e.g., Qt6 components) if they are not already present on the system. Be aware that the initial installation and compilation of large dependencies like Qt can be time-consuming.

```bash
mkdir build
cd build
```

**For Windows (using Visual Studio Generator):**

```bash
cmake .. -DCMAKE_TOOLCHAIN_FILE="<path_to_vcpkg>/scripts/buildsystems/vcpkg.cmake" -G "Visual Studio 17 2022"
# Adjust "Visual Studio 17 2022" to match your installed Visual Studio version (e.g., "Visual Studio 16 2019")
```

**For Linux/macOS or other CMake Generators (e.g., Makefiles, Ninja):**

```bash
cmake .. -DCMAKE_TOOLCHAIN_FILE="<path_to_vcpkg>/scripts/buildsystems/vcpkg.cmake"
```

### 4. Build the Project

Execute the build process. The `--config Debug` option compiles the project with debugging symbols, suitable for development and troubleshooting.

```bash
cmake --build . --config Debug
```

### 5. Run the Application

*   **Recommended for Development:** Launch the application directly from your chosen IDE. Modern IDEs are typically configured to correctly set the environment variables (e.g., `PATH`, `QT_PLUGIN_PATH`) required for Qt applications to locate their runtime dependencies.
*   **Direct Execution from Build Directory:** If attempting to run the executable directly from the `build/Debug` or `build/Release` directory, you may encounter issues such as "no Qt platform plugin could be initialized." Refer to the "Runtime Dependencies and Troubleshooting" section for solutions.

</details>

<details>
<summary><h2>Deployment for Customer Distribution</h2></summary>

When preparing the application for end-user distribution, it is imperative to create a **release build** and bundle all necessary runtime dependencies.

1.  **Build a Release Version:**
    Compile the project in Release mode for optimized performance and reduced size.
    ```bash
    cmake --build . --config Release
    ```
    The compiled executable will typically be located in `build/Release/ArjunBiswasMediaPlayer.exe`.

2.  **Deploy Runtime Dependencies:**
    Qt applications require specific DLLs and plugin directories to function correctly on target systems where Qt is not installed.

    *   **Utilize `windeployqt.exe` (Windows):** The official Qt deployment tool automates the collection of required DLLs and plugins. Execute `windeployqt.exe` (found within your vcpkg Qt installation) against your release executable.
        ```bash
        # Example command, adjust paths as necessary
        <path_to_vcpkg>/x64-windows/tools/Qt6/bin/windeployqt.exe build/Release/ArjunBiswasMediaPlayer.exe
        ```
    *   **Manual Deployment:** If automated tools do not suffice or for specific deployment scenarios, manually copy the release versions of Qt DLLs (e.g., `Qt6Widgets.dll`) and the entire `plugins` directory (containing subdirectories such as `platforms`, `imageformats`, etc.) from your vcpkg installation to the directory containing your application's release executable.

</details>

<details>
<summary><h2>Version Control with Git & Troubleshooting</h2></summary>

### Excluding Build Artifacts from Git

It is a best practice to **exclude all generated build artifacts** from your Git repository. Version control systems should primarily manage source code and configuration files, not transient or derived files.

**Rationale for Exclusion:**
*   **Repository Size:** Build artifacts are often large binary files. Committing them will significantly bloat the repository history, leading to increased clone times and storage requirements.
*   **Reproducibility:** Build artifacts are specific to the build environment (compiler, OS, libraries). They can and should be regenerated from the source code on each developer's machine or CI/CD system.
*   **Platform Independence:** Binaries built on one platform are generally incompatible with others. Committing them hinders cross-platform development.
*   **Clean History:** Excluding artifacts keeps the Git history clean and focused on actual code changes, improving readability and maintainability.

**Files and Directories to Exclude (via `.gitignore`):**
*   Build directories (e.g., `build/`)
*   Package manager installation directories (e.g., `vcpkg_installed/`)
*   Executable files (`.exe`)
*   Dynamic Link Libraries (`.dll`, `.so`, `.dylib`)
*   Static Libraries (`.lib`, `.a`)
*   Object files (`.obj`, `.o`)
*   Program Database files (`.pdb`, `.ilk`)
*   IDE-specific files and folders (e.g., `.vs/`, `.vscode/` if not shared across team, `.user` files)
*   CMake generated files (e.g., `CMakeCache.txt`, `CMakeFiles/`)

### "No Qt Platform Plugin Could Be Initialized" Error

This runtime error indicates that the Qt application is unable to locate its required platform plugins (e.g., `qwindowsd.dll` on Windows) essential for initializing the graphical user interface. This typically occurs when the executable is run directly without the necessary runtime dependencies correctly deployed or environment variables configured.

**Resolution:**
Ensure that the `platforms` subdirectory, containing the relevant platform plugin (`qwindowsd.dll` for debug, `qwindows.dll` for release), is present in the same directory as your application's executable.
*   **For Debug Builds:** The plugin typically resides in `<path_to_vcpkg>/x64-windows/debug/Qt6/plugins/platforms`.
*   **For Release Builds:** The plugin typically resides in `<path_to_vcpkg>/x64-windows/Qt6/plugins/platforms`.
If `windeployqt` is unsuccessful, manually copying these directories to the executable's location provides a reliable solution.

</details>

#include <QApplication>
#include <QMainWindow>
#include <QWidget>
#include <QCoreApplication>
ok so#include <QDir>
 
int main(int argc, char* argv[]) {
    // Fix for "no Qt platform plugin" and "ASSERT: theme" errors.
    // We set the QT_PLUGIN_PATH environment variable to point explicitly to the vcpkg plugins folder.
    // This overrides any misconfiguration in qt.conf or default search paths.
    
    QDir baseDir(QCoreApplication::applicationDirPath());
    baseDir.cdUp(); // Go up from 'Debug' to 'build'
    
    // Construct the path to the plugins directory created by vcpkg
    // Path: build/vcpkg_installed/x64-windows/debug/plugins
    QString pluginsPath = baseDir.filePath("vcpkg_installed/x64-windows/debug/plugins");
    
    // If that doesn't exist (e.g. Release mode), try the release path
    if (!QDir(pluginsPath).exists()) {
        pluginsPath = baseDir.filePath("vcpkg_installed/x64-windows/plugins");
    }

    // Set the environment variable. This is the most reliable way to force Qt to find plugins.
    qputenv("QT_PLUGIN_PATH", pluginsPath.toUtf8());
    
    // Also add to the library path for good measure
    QCoreApplication::addLibraryPath(pluginsPath);

    QApplication app(argc, argv);
 
    QMainWindow window;
    window.setWindowTitle("ArjunBiswasMediaPlayer");
 
    // Create a central widget to act as our main canvas
    QWidget *centralWidget = new QWidget(&window);
    // Set its background to black using a modern stylesheet approach
    centralWidget->setStyleSheet("background-color: black;");
    window.setCentralWidget(centralWidget);

    window.resize(800, 600); // Optional: Set an initial size
    window.show();
 
    return app.exec();
}
#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QCoreApplication>
#include <QDir>
#include <QUrl>
#include <QDebug>

int main(int argc, char* argv[]) {
    QGuiApplication app(argc, argv);

    // Fix for "no Qt platform plugin" and "ASSERT: theme" errors.
    // We set the QT_PLUGIN_PATH environment variable to point explicitly to the vcpkg plugins folder.
    // This overrides any misconfiguration in qt.conf or default search paths.

    QDir baseDir(QCoreApplication::applicationDirPath());
    baseDir.cdUp(); // go up from build to project root when running from build/

    // Construct the path to the plugins directory created by vcpkg (macOS paths)
    QString pluginsPath = baseDir.filePath("vcpkg_installed/arm64-osx/plugins");
    if (!QDir(pluginsPath).exists()) {
        pluginsPath = baseDir.filePath("vcpkg_installed/arm64-osx/debug/plugins");
    }
    if (!QDir(pluginsPath).exists()) {
        pluginsPath = baseDir.filePath("build/vcpkg_installed/arm64-osx/plugins");
    }

    qputenv("QT_PLUGIN_PATH", pluginsPath.toUtf8());
    QCoreApplication::addLibraryPath(pluginsPath);

    QQmlApplicationEngine engine;
    QString qmlFile = baseDir.filePath("qml/main.qml");
    qDebug() << "Loading QML from:" << qmlFile << "pluginsPath:" << pluginsPath;
    engine.load(QUrl::fromLocalFile(qmlFile));

    if (engine.rootObjects().isEmpty()) {
        return -1;
    }

    return app.exec();
}
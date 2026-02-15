cmake_minimum_required(VERSION 3.16)
project(ArjunBiswasMediaPlayer LANGUAGES CXX)

find_package(Qt6 COMPONENTS Quick Qml REQUIRED)
find_package(ffmpeg CONFIG REQUIRED)
qt_standard_project_setup()

# Add executable and register QML module files so CMake knows about them
qt_add_executable(ArjunBiswasMediaPlayer main.cpp src/MediaPlayer.cpp src/MediaPlayer.h src/FFmpegDecoder.cpp src/FFmpegDecoder.h src/SubtitleManager.cpp src/SubtitleManager.h src/VideoFilter.h)

qt_add_qml_module(ArjunBiswasMediaPlayer
	URI ArjunBiswasMediaPlayer
	VERSION 1.0
	QML_FILES
		qml/main.qml
		qml/Player.qml
)

target_include_directories(ArjunBiswasMediaPlayer PRIVATE src)
target_link_libraries(ArjunBiswasMediaPlayer PRIVATE Qt6::Quick Qt6::Qml ffmpeg::ffmpeg)
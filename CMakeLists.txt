cmake_minimum_required(VERSION 3.16)
project(ArjunBiswasMediaPlayer LANGUAGES CXX)

find_package(Qt6 COMPONENTS Widgets REQUIRED)
qt_standard_project_setup()

# Uses Qt's wrapper to handle deployment, WinMain entry point, and plugins automatically
qt_add_executable(ArjunBiswasMediaPlayer main.cpp)

target_link_libraries(ArjunBiswasMediaPlayer PRIVATE Qt6::Widgets)
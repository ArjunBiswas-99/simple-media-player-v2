cmake_minimum_required(VERSION 3.20)
project(MediaPlayer VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Use Ninja for fast builds
if(NOT CMAKE_GENERATOR STREQUAL "Ninja")
    message(STATUS "Consider using Ninja for faster builds: cmake -G Ninja")
endif()

# Platform detection
if(APPLE)
    set(PLATFORM_NAME "macOS")
    set(VIDEO_BACKEND "Metal")
    set(AUDIO_BACKEND "CoreAudio")
    
    find_library(COCOA_LIBRARY Cocoa REQUIRED)
    find_library(METAL_LIBRARY Metal REQUIRED)
    find_library(METALKIT_LIBRARY MetalKit REQUIRED)
    find_library(QUARTZCORE_LIBRARY QuartzCore REQUIRED)
    find_library(COREAUDIO_LIBRARY CoreAudio REQUIRED)
    find_library(AUDIOTOOLBOX_LIBRARY AudioToolbox REQUIRED)
    find_library(GAMECONTROLLER_LIBRARY GameController REQUIRED)
    
    set(PLATFORM_LIBS
        ${COCOA_LIBRARY}
        ${METAL_LIBRARY}
        ${METALKIT_LIBRARY}
        ${QUARTZCORE_LIBRARY}
        ${COREAUDIO_LIBRARY}
        ${AUDIOTOOLBOX_LIBRARY}
        ${GAMECONTROLLER_LIBRARY}
    )
    
    # Use libc++
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -stdlib=libc++")
    
    # Enable some optimization even in debug mode for faster iteration
    set(CMAKE_CXX_FLAGS_DEBUG "${CMAKE_CXX_FLAGS_DEBUG} -O1")
    
elseif(WIN32)
    set(PLATFORM_NAME "Windows")
    set(VIDEO_BACKEND "Direct3D11")
    set(AUDIO_BACKEND "WASAPI")
    
    set(PLATFORM_LIBS
        d3d11.lib
        dxgi.lib
        d3dcompiler.lib
    )
    
    # Enable incremental linking
    set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} /INCREMENTAL")
endif()

message(STATUS "Building for ${PLATFORM_NAME}")
message(STATUS "Video Backend: ${VIDEO_BACKEND}")
message(STATUS "Audio Backend: ${AUDIO_BACKEND}")

# Dear ImGui
set(IMGUI_DIR ${CMAKE_CURRENT_SOURCE_DIR}/external/imgui)
if(NOT EXISTS ${IMGUI_DIR})
    message(FATAL_ERROR "Dear ImGui not found at ${IMGUI_DIR}. Please run: git clone https://github.com/ocornut/imgui.git external/imgui")
endif()

add_library(imgui STATIC
    ${IMGUI_DIR}/imgui.cpp
    ${IMGUI_DIR}/imgui_demo.cpp
    ${IMGUI_DIR}/imgui_draw.cpp
    ${IMGUI_DIR}/imgui_tables.cpp
    ${IMGUI_DIR}/imgui_widgets.cpp
)

# Platform-specific ImGui backends
if(APPLE)
    target_sources(imgui PRIVATE
        ${IMGUI_DIR}/backends/imgui_impl_osx.mm
        ${IMGUI_DIR}/backends/imgui_impl_metal.mm
    )
elseif(WIN32)
    target_sources(imgui PRIVATE
        ${IMGUI_DIR}/backends/imgui_impl_win32.cpp
        ${IMGUI_DIR}/backends/imgui_impl_dx11.cpp
    )
endif()

target_include_directories(imgui PUBLIC
    ${IMGUI_DIR}
    ${IMGUI_DIR}/backends
)

if(APPLE)
    target_link_libraries(imgui PUBLIC ${PLATFORM_LIBS})
endif()

# FFmpeg - TODO: Add FFmpeg integration in Phase 2
# For now, we'll create a placeholder
# find_package(FFmpeg COMPONENTS avcodec avformat avutil swscale REQUIRED)

# Main executable
add_executable(MediaPlayer
    src/main.cpp
)

target_include_directories(MediaPlayer PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src
)

target_link_libraries(MediaPlayer PRIVATE
    imgui
    ${PLATFORM_LIBS}
)

if(APPLE)
    # Enable Objective-C++ for macOS
    set_source_files_properties(src/main.cpp PROPERTIES
        COMPILE_FLAGS "-x objective-c++"
    )
endif()

# Hot-reloadable UI library (will be implemented later)
# add_library(PlayerUI SHARED
#     src/ui/player_ui.cpp
#     src/ui/controls.cpp
#     src/ui/progress_bar.cpp
# )

# Copy resources (if any) to build directory
# add_custom_command(TARGET MediaPlayer POST_BUILD
#     COMMAND ${CMAKE_COMMAND} -E copy_directory
#     ${CMAKE_SOURCE_DIR}/resources $<TARGET_FILE_DIR:MediaPlayer>/resources
# )

message(STATUS "Configuration complete. Build with: cmake --build build")

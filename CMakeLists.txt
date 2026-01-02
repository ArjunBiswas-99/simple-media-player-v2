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
    
    # Require MSVC compiler (MinGW doesn't support Direct3D)
    if(NOT MSVC)
        message(FATAL_ERROR "Windows build requires MSVC compiler. Please use Visual Studio or run cmake with: cmake -G \"Visual Studio 17 2022\" -B build")
    endif()
    
    set(PLATFORM_LIBS
        d3d11.lib
        dxgi.lib
        d3dcompiler.lib
        ole32.lib
        shell32.lib
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

# FFmpeg integration
if(APPLE)
    set(FFMPEG_ROOT ${CMAKE_CURRENT_SOURCE_DIR}/external/ffmpeg/macos)
    set(FFMPEG_INCLUDE_DIR ${FFMPEG_ROOT}/include)
    set(FFMPEG_LIB_DIR ${FFMPEG_ROOT}/lib)
    
    # Find FFmpeg libraries (with version suffixes)
    find_library(AVCODEC_LIBRARY NAMES avcodec.62 avcodec PATHS ${FFMPEG_LIB_DIR} NO_DEFAULT_PATH)
    find_library(AVFORMAT_LIBRARY NAMES avformat.62 avformat PATHS ${FFMPEG_LIB_DIR} NO_DEFAULT_PATH)
    find_library(AVUTIL_LIBRARY NAMES avutil.60 avutil PATHS ${FFMPEG_LIB_DIR} NO_DEFAULT_PATH)
    find_library(SWSCALE_LIBRARY NAMES swscale.9 swscale PATHS ${FFMPEG_LIB_DIR} NO_DEFAULT_PATH)
    find_library(SWRESAMPLE_LIBRARY NAMES swresample.6 swresample PATHS ${FFMPEG_LIB_DIR} NO_DEFAULT_PATH)
    
    set(FFMPEG_LIBRARIES
        ${AVCODEC_LIBRARY}
        ${AVFORMAT_LIBRARY}
        ${AVUTIL_LIBRARY}
        ${SWSCALE_LIBRARY}
        ${SWRESAMPLE_LIBRARY}
    )
    
    message(STATUS "FFmpeg libraries: ${FFMPEG_LIBRARIES}")
    
elseif(WIN32)
    # Windows FFmpeg setup
    set(FFMPEG_ROOT ${CMAKE_CURRENT_SOURCE_DIR}/external/ffmpeg/windows)
    set(FFMPEG_INCLUDE_DIR ${FFMPEG_ROOT}/include)
    set(FFMPEG_LIB_DIR ${FFMPEG_ROOT}/lib)
    
    # FFmpeg libraries for Windows
    set(FFMPEG_LIBRARIES
        ${FFMPEG_LIB_DIR}/avcodec.lib
        ${FFMPEG_LIB_DIR}/avformat.lib
        ${FFMPEG_LIB_DIR}/avutil.lib
        ${FFMPEG_LIB_DIR}/swscale.lib
        ${FFMPEG_LIB_DIR}/swresample.lib
    )
    
    # Windows system libraries
    list(APPEND PLATFORM_LIBS
        d3d11.lib
        dxgi.lib
        d3dcompiler.lib
        ole32.lib
        shell32.lib
    )
endif()

# Main executable
add_executable(MediaPlayer
    src/main.cpp
    src/VideoDecoder.cpp
    src/VideoDecoder.h
    src/AudioOutput.cpp
    src/AudioOutput.h
    src/platform.h
)

# Platform-specific source files
if(APPLE)
    target_sources(MediaPlayer PRIVATE src/platform_macos.mm)
elseif(WIN32)
    target_sources(MediaPlayer PRIVATE src/platform_windows.cpp)
endif()

target_include_directories(MediaPlayer PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src
    ${FFMPEG_INCLUDE_DIR}
)

target_link_libraries(MediaPlayer PRIVATE
    imgui
    ${PLATFORM_LIBS}
    ${FFMPEG_LIBRARIES}
)

if(APPLE)
    # Enable Objective-C++ for macOS
    set_source_files_properties(src/main.cpp src/platform_macos.mm PROPERTIES
        COMPILE_FLAGS "-x objective-c++"
    )
    
    # Set rpath for FFmpeg dynamic libraries
    set_target_properties(MediaPlayer PROPERTIES
        BUILD_RPATH "${FFMPEG_LIB_DIR}"
        INSTALL_RPATH "@executable_path/../Frameworks"
    )
    
    # Copy FFmpeg dylibs to build directory
    add_custom_command(TARGET MediaPlayer POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_directory
        ${FFMPEG_LIB_DIR} $<TARGET_FILE_DIR:MediaPlayer>
        COMMENT "Copying FFmpeg libraries to build directory"
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

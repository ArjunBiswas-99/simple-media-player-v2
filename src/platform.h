#pragma once

#include <string>

// Platform-specific types and functions

#ifdef __APPLE__
    #import <Metal/Metal.h>
    #import <Cocoa/Cocoa.h>
    
    using PlatformTexture = id<MTLTexture>;
    using PlatformWindow = NSWindow*;
    
#elif defined(_WIN32)
    #define NOMINMAX  // Prevent Windows.h from defining min/max macros
    #include <d3d11.h>
    #include <windows.h>
    
    using PlatformTexture = ID3D11ShaderResourceView*;
    using PlatformWindow = HWND;
    
#endif

// Cross-platform file dialog
std::string OpenFileDialog();

// Cross-platform fullscreen toggle
void ToggleFullscreen(PlatformWindow window, bool& isFullscreen);

// Platform initialization
bool InitializePlatform();
void ShutdownPlatform();

// Texture management
PlatformTexture CreateVideoTexture(int width, int height);
void UpdateVideoTexture(PlatformTexture texture, uint8_t* rgbaData, int width, int height);
void DestroyVideoTexture(PlatformTexture texture);

#ifdef _WIN32
// Windows-specific: Get D3D11 device for ImGui
ID3D11Device* GetD3D11Device();
ID3D11DeviceContext* GetD3D11DeviceContext();
void SetD3D11Device(ID3D11Device* device, ID3D11DeviceContext* context, IDXGISwapChain* swapChain, ID3D11RenderTargetView* rtv);
#endif

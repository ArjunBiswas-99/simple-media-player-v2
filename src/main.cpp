//
// Simple Media Player V2 - Netflix-Inspired Media Player
// Main Entry Point
//

#include "imgui.h"

#ifdef __APPLE__
#include "imgui_impl_osx.h"
#include "imgui_impl_metal.h"
#import <Cocoa/Cocoa.h>
#import <Metal/Metal.h>
#import <MetalKit/MetalKit.h>
#import <QuartzCore/QuartzCore.h>
#else
#include "imgui_impl_win32.h"
#include "imgui_impl_dx11.h"
#include <d3d11.h>
#include <tchar.h>
#endif

#include <iostream>
#include <chrono>
#include <cmath>
#include <string>
#include <vector>

// Application State
struct AppState {
    bool showControls = true;
    bool showMenuBar = false;
    float controlsTimer = 3.0f;
    bool isPlaying = false;
    float currentTime = 0.0f;
    float duration = 125.0f;
    float volume = 0.5f;
    bool isMuted = false;
    float playbackSpeed = 1.0f;
    int aspectRatioIndex = 0; // 0=Original, 1=16:9, etc.
    int cropIndex = 0;
    std::string currentFile = "Demo_Video_2024.mp4";
    std::string currentTitle = "Simple Media Player V2";
};

// Forward declarations
void SetupNetflixTheme();
void RenderMenuBar(AppState& state);
void RenderNetflixUI(AppState& state);
std::string FormatTime(float seconds);
void DrawGradientOverlay(ImDrawList* draw, ImVec2 start, ImVec2 end, ImU32 colorTop, ImU32 colorBottom);
void DrawPlayIcon(ImDrawList* draw, ImVec2 center, float size, ImU32 color);
void DrawPauseIcon(ImDrawList* draw, ImVec2 center, float size, ImU32 color);
void DrawSkipIcon(ImDrawList* draw, ImVec2 center, float size, bool forward, ImU32 color);
void DrawVolumeIcon(ImDrawList* draw, ImVec2 pos, float volume, bool muted, ImU32 color);
void DrawSettingsIcon(ImDrawList* draw, ImVec2 center, float size, ImU32 color);
void DrawSubtitlesIcon(ImDrawList* draw, ImVec2 center, float size, ImU32 color);
void DrawFullscreenIcon(ImDrawList* draw, ImVec2 center, float size, ImU32 color);

#ifdef __APPLE__
// macOS-specific implementation
@interface AppViewController : NSViewController <MTKViewDelegate>
@end

@interface AppViewController ()
@property (nonatomic, readonly) MTKView *mtkView;
@property (nonatomic, strong) id <MTLDevice> device;
@property (nonatomic, strong) id <MTLCommandQueue> commandQueue;
@end

@implementation AppViewController

- (MTKView *)mtkView {
    return (MTKView *)self.view;
}

- (void)loadView {
    self.view = [[MTKView alloc] initWithFrame:CGRectMake(0, 0, 1280, 720)];
}

- (void)viewDidLoad {
    [super viewDidLoad];

    self.device = MTLCreateSystemDefaultDevice();
    self.commandQueue = [self.device newCommandQueue];

    if (!self.device) {
        NSLog(@"Metal is not supported");
        abort();
    }

    self.mtkView.device = self.device;
    self.mtkView.delegate = self;
    self.mtkView.clearColor = MTLClearColorMake(0.0, 0.0, 0.0, 1.0);

    // Setup Dear ImGui context
    IMGUI_CHECKVERSION();
    ImGui::CreateContext();
    ImGuiIO& io = ImGui::GetIO();
    io.ConfigFlags |= ImGuiConfigFlags_NavEnableKeyboard;
    
    // Setup style
    SetupNetflixTheme();

    // Setup Platform/Renderer backends
    ImGui_ImplOSX_Init(self.view);
    ImGui_ImplMetal_Init(self.device);
}

- (void)drawInMTKView:(MTKView *)view {
    ImGuiIO& io = ImGui::GetIO();
    io.DisplaySize.x = view.bounds.size.width;
    io.DisplaySize.y = view.bounds.size.height;

    CGFloat framebufferScale = view.window.screen.backingScaleFactor ?: NSScreen.mainScreen.backingScaleFactor;
    io.DisplayFramebufferScale = ImVec2(framebufferScale, framebufferScale);

    id<MTLCommandBuffer> commandBuffer = [self.commandQueue commandBuffer];

    MTLRenderPassDescriptor* renderPassDescriptor = view.currentRenderPassDescriptor;
    if (renderPassDescriptor == nil) {
        [commandBuffer commit];
        return;
    }

    // Start ImGui frame
    ImGui_ImplMetal_NewFrame(renderPassDescriptor);
    ImGui_ImplOSX_NewFrame(view);
    ImGui::NewFrame();

    // Application state
    static AppState state;

    // Render UI
    RenderMenuBar(state);
    RenderNetflixUI(state);

    // Rendering
    ImGui::Render();
    ImDrawData* drawData = ImGui::GetDrawData();

    id<MTLRenderCommandEncoder> renderEncoder = [commandBuffer renderCommandEncoderWithDescriptor:renderPassDescriptor];
    ImGui_ImplMetal_RenderDrawData(drawData, commandBuffer, renderEncoder);
    [renderEncoder endEncoding];

    [commandBuffer presentDrawable:view.currentDrawable];
    [commandBuffer commit];
}

- (void)mtkView:(MTKView *)view drawableSizeWillChange:(CGSize)size {
}

@end

int main(int argc, const char * argv[]) {
    @autoreleasepool {
        NSApp = [NSApplication sharedApplication];
        [NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];

        NSWindow* window = [[NSWindow alloc] initWithContentRect:NSMakeRect(0, 0, 1280, 720)
                                                        styleMask:NSWindowStyleMaskTitled | NSWindowStyleMaskClosable | NSWindowStyleMaskResizable | NSWindowStyleMaskMiniaturizable
                                                          backing:NSBackingStoreBuffered
                                                            defer:NO];
        [window center];
        [window setTitle:@"Simple Media Player V2"];

        AppViewController* viewController = [[AppViewController alloc] init];
        [window setContentViewController:viewController];
        [window makeKeyAndOrderFront:nil];

        [NSApp activateIgnoringOtherApps:YES];
        [NSApp run];
    }
    return 0;
}

#else
// Windows-specific implementation
static ID3D11Device*            g_pd3dDevice = nullptr;
static ID3D11DeviceContext*     g_pd3dDeviceContext = nullptr;
static IDXGISwapChain*          g_pSwapChain = nullptr;
static ID3D11RenderTargetView*  g_mainRenderTargetView = nullptr;

bool CreateDeviceD3D(HWND hWnd);
void CleanupDeviceD3D();
void CreateRenderTarget();
void CleanupRenderTarget();
LRESULT WINAPI WndProc(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam);

int main(int, char**) {
    // Create application window
    WNDCLASSEXW wc = { sizeof(wc), CS_CLASSDC, WndProc, 0L, 0L, GetModuleHandle(nullptr), nullptr, nullptr, nullptr, nullptr, L"MediaPlayer", nullptr };
    RegisterClassExW(&wc);
    HWND hwnd = CreateWindowW(wc.lpszClassName, L"Simple Media Player V2", WS_OVERLAPPEDWINDOW, 100, 100, 1280, 720, nullptr, nullptr, wc.hInstance, nullptr);

    // Initialize Direct3D
    if (!CreateDeviceD3D(hwnd)) {
        CleanupDeviceD3D();
        UnregisterClassW(wc.lpszClassName, wc.hInstance);
        return 1;
    }

    ShowWindow(hwnd, SW_SHOWDEFAULT);
    UpdateWindow(hwnd);

    // Setup Dear ImGui context
    IMGUI_CHECKVERSION();
    ImGui::CreateContext();
    ImGuiIO& io = ImGui::GetIO();
    io.ConfigFlags |= ImGuiConfigFlags_NavEnableKeyboard;

    SetupNetflixTheme();

    // Setup Platform/Renderer backends
    ImGui_ImplWin32_Init(hwnd);
    ImGui_ImplDX11_Init(g_pd3dDevice, g_pd3dDeviceContext);

    // Application state
    AppState state;

    // Main loop
    bool done = false;
    while (!done) {
        MSG msg;
        while (PeekMessage(&msg, nullptr, 0U, 0U, PM_REMOVE)) {
            TranslateMessage(&msg);
            DispatchMessage(&msg);
            if (msg.message == WM_QUIT)
                done = true;
        }
        if (done)
            break;

        // Start ImGui frame
        ImGui_ImplDX11_NewFrame();
        ImGui_ImplWin32_NewFrame();
        ImGui::NewFrame();

        // Render UI
        RenderMenuBar(state);
        RenderNetflixUI(state);

        // Rendering
        ImGui::Render();
        const float clear_color[4] = { 0.0f, 0.0f, 0.0f, 1.0f };
        g_pd3dDeviceContext->OMSetRenderTargets(1, &g_mainRenderTargetView, nullptr);
        g_pd3dDeviceContext->ClearRenderTargetView(g_mainRenderTargetView, clear_color);
        ImGui_ImplDX11_RenderDrawData(ImGui::GetDrawData());

        g_pSwapChain->Present(1, 0);
    }

    // Cleanup
    ImGui_ImplDX11_Shutdown();
    ImGui_ImplWin32_Shutdown();
    ImGui::DestroyContext();

    CleanupDeviceD3D();
    DestroyWindow(hwnd);
    UnregisterClassW(wc.lpszClassName, wc.hInstance);

    return 0;
}

bool CreateDeviceD3D(HWND hWnd) {
    DXGI_SWAP_CHAIN_DESC sd;
    ZeroMemory(&sd, sizeof(sd));
    sd.BufferCount = 2;
    sd.BufferDesc.Width = 0;
    sd.BufferDesc.Height = 0;
    sd.BufferDesc.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    sd.BufferDesc.RefreshRate.Numerator = 60;
    sd.BufferDesc.RefreshRate.Denominator = 1;
    sd.Flags = DXGI_SWAP_CHAIN_FLAG_ALLOW_MODE_SWITCH;
    sd.BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT;
    sd.OutputWindow = hWnd;
    sd.SampleDesc.Count = 1;
    sd.SampleDesc.Quality = 0;
    sd.Windowed = TRUE;
    sd.SwapEffect = DXGI_SWAP_EFFECT_DISCARD;

    UINT createDeviceFlags = 0;
    D3D_FEATURE_LEVEL featureLevel;
    const D3D_FEATURE_LEVEL featureLevelArray[2] = { D3D_FEATURE_LEVEL_11_0, D3D_FEATURE_LEVEL_10_0, };
    HRESULT res = D3D11CreateDeviceAndSwapChain(nullptr, D3D_DRIVER_TYPE_HARDWARE, nullptr, createDeviceFlags, featureLevelArray, 2, D3D11_SDK_VERSION, &sd, &g_pSwapChain, &g_pd3dDevice, &featureLevel, &g_pd3dDeviceContext);
    if (res != S_OK)
        return false;

    CreateRenderTarget();
    return true;
}

void CleanupDeviceD3D() {
    CleanupRenderTarget();
    if (g_pSwapChain) { g_pSwapChain->Release(); g_pSwapChain = nullptr; }
    if (g_pd3dDeviceContext) { g_pd3dDeviceContext->Release(); g_pd3dDeviceContext = nullptr; }
    if (g_pd3dDevice) { g_pd3dDevice->Release(); g_pd3dDevice = nullptr; }
}

void CreateRenderTarget() {
    ID3D11Texture2D* pBackBuffer;
    g_pSwapChain->GetBuffer(0, IID_PPV_ARGS(&pBackBuffer));
    g_pd3dDevice->CreateRenderTargetView(pBackBuffer, nullptr, &g_mainRenderTargetView);
    pBackBuffer->Release();
}

void CleanupRenderTarget() {
    if (g_mainRenderTargetView) { g_mainRenderTargetView->Release(); g_mainRenderTargetView = nullptr; }
}

extern IMGUI_IMPL_API LRESULT ImGui_ImplWin32_WndProcHandler(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam);

LRESULT WINAPI WndProc(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam) {
    if (ImGui_ImplWin32_WndProcHandler(hWnd, msg, wParam, lParam))
        return true;

    switch (msg) {
    case WM_SIZE:
        if (wParam == SIZE_MINIMIZED)
            return 0;
        if (g_pd3dDevice != nullptr) {
            CleanupRenderTarget();
            g_pSwapChain->ResizeBuffers(0, (UINT)LOWORD(lParam), (UINT)HIWORD(lParam), DXGI_FORMAT_UNKNOWN, 0);
            CreateRenderTarget();
        }
        return 0;
    case WM_SYSCOMMAND:
        if ((wParam & 0xfff0) == SC_KEYMENU)
            return 0;
        break;
    case WM_DESTROY:
        PostQuitMessage(0);
        return 0;
    }
    return DefWindowProcW(hWnd, msg, wParam, lParam);
}
#endif

// ===== Netflix UI Implementation =====

void SetupNetflixTheme() {
    ImGuiStyle& style = ImGui::GetStyle();
    ImVec4* colors = style.Colors;

    // Netflix color palette
    const ImVec4 netflixRed = ImVec4(0.898f, 0.035f, 0.078f, 1.0f);      // #E50914
    const ImVec4 darkBg = ImVec4(0.08f, 0.08f, 0.08f, 0.95f);            // #141414
    const ImVec4 menuBg = ImVec4(0.078f, 0.078f, 0.078f, 0.98f);         // #141414
    const ImVec4 darkGray = ImVec4(0.29f, 0.29f, 0.29f, 1.0f);           // #4A4A4A
    const ImVec4 lightGray = ImVec4(0.75f, 0.75f, 0.75f, 1.0f);          // #BEBEBE
    const ImVec4 white = ImVec4(1.0f, 1.0f, 1.0f, 1.0f);

    // Main colors
    colors[ImGuiCol_WindowBg] = darkBg;
    colors[ImGuiCol_ChildBg] = ImVec4(0.0f, 0.0f, 0.0f, 0.0f);
    colors[ImGuiCol_PopupBg] = menuBg;
    colors[ImGuiCol_Border] = ImVec4(0.3f, 0.3f, 0.3f, 0.3f);
    colors[ImGuiCol_FrameBg] = darkGray;
    colors[ImGuiCol_FrameBgHovered] = ImVec4(0.3f, 0.3f, 0.3f, 1.0f);
    colors[ImGuiCol_FrameBgActive] = ImVec4(0.4f, 0.4f, 0.4f, 1.0f);
    colors[ImGuiCol_TitleBg] = darkBg;
    colors[ImGuiCol_TitleBgActive] = darkBg;
    colors[ImGuiCol_TitleBgCollapsed] = darkBg;
    colors[ImGuiCol_MenuBarBg] = ImVec4(0.0f, 0.0f, 0.0f, 0.85f);
    
    // Button colors
    colors[ImGuiCol_Button] = netflixRed;
    colors[ImGuiCol_ButtonHovered] = ImVec4(1.0f, 0.05f, 0.09f, 1.0f);
    colors[ImGuiCol_ButtonActive] = ImVec4(0.7f, 0.03f, 0.06f, 1.0f);
    
    // Slider colors
    colors[ImGuiCol_SliderGrab] = white;
    colors[ImGuiCol_SliderGrabActive] = lightGray;
    
    // Header colors (for menu hover)
    colors[ImGuiCol_Header] = ImVec4(1.0f, 1.0f, 1.0f, 0.08f);
    colors[ImGuiCol_HeaderHovered] = ImVec4(1.0f, 1.0f, 1.0f, 0.12f);
    colors[ImGuiCol_HeaderActive] = ImVec4(1.0f, 1.0f, 1.0f, 0.15f);
    
    // Text
    colors[ImGuiCol_Text] = white;
    colors[ImGuiCol_TextDisabled] = ImVec4(0.4f, 0.4f, 0.4f, 1.0f);
    
    // Rounding
    style.WindowRounding = 0.0f;
    style.ChildRounding = 0.0f;
    style.FrameRounding = 4.0f;
    style.GrabRounding = 12.0f;
    style.PopupRounding = 8.0f;
    style.ScrollbarRounding = 9.0f;
    
    // Spacing (8px grid system)
    style.WindowPadding = ImVec2(0, 0);
    style.FramePadding = ImVec2(8, 4);
    style.ItemSpacing = ImVec2(16, 8);
    style.ItemInnerSpacing = ImVec2(8, 6);
    style.IndentSpacing = 25.0f;
    style.ScrollbarSize = 15.0f;
    style.GrabMinSize = 16.0f;
    
    // Menu specific
    style.PopupBorderSize = 0.0f;
    style.WindowMenuButtonPosition = ImGuiDir_None;
}

std::string FormatTime(float seconds) {
    int hrs = (int)seconds / 3600;
    int mins = ((int)seconds % 3600) / 60;
    int secs = (int)seconds % 60;
    
    char buf[32];
    if (hrs > 0) {
        snprintf(buf, sizeof(buf), "%d:%02d:%02d", hrs, mins, secs);
    } else {
        snprintf(buf, sizeof(buf), "%d:%02d", mins, secs);
    }
    return std::string(buf);
}

void DrawGradientOverlay(ImDrawList* draw, ImVec2 start, ImVec2 end, ImU32 colorTop, ImU32 colorBottom) {
    draw->AddRectFilledMultiColor(start, end, colorTop, colorTop, colorBottom, colorBottom);
}

void DrawPlayIcon(ImDrawList* draw, ImVec2 center, float size, ImU32 color) {
    ImVec2 points[3] = {
        ImVec2(center.x - size * 0.3f, center.y - size * 0.45f),
        ImVec2(center.x - size * 0.3f, center.y + size * 0.45f),
        ImVec2(center.x + size * 0.45f, center.y)
    };
    draw->AddTriangleFilled(points[0], points[1], points[2], color);
}

void DrawPauseIcon(ImDrawList* draw, ImVec2 center, float size, ImU32 color) {
    float barWidth = size * 0.22f;
    float barHeight = size * 0.9f;
    float spacing = size * 0.2f;
    
    draw->AddRectFilled(
        ImVec2(center.x - spacing - barWidth, center.y - barHeight * 0.5f),
        ImVec2(center.x - spacing, center.y + barHeight * 0.5f),
        color, 2.0f
    );
    draw->AddRectFilled(
        ImVec2(center.x + spacing, center.y - barHeight * 0.5f),
        ImVec2(center.x + spacing + barWidth, center.y + barHeight * 0.5f),
        color, 2.0f
    );
}

void DrawSkipIcon(ImDrawList* draw, ImVec2 center, float size, bool forward, ImU32 color) {
    float direction = forward ? 1.0f : -1.0f;
    
    // Arrow triangle
    ImVec2 points[3] = {
        ImVec2(center.x + direction * size * 0.15f, center.y),
        ImVec2(center.x + direction * size * -0.25f, center.y - size * 0.35f),
        ImVec2(center.x + direction * size * -0.25f, center.y + size * 0.35f)
    };
    draw->AddTriangleFilled(points[0], points[1], points[2], color);
    
    // "10" text
    char text[] = "10";
    ImVec2 textSize = ImGui::CalcTextSize(text);
    ImVec2 textPos = ImVec2(
        center.x + direction * size * -0.05f - textSize.x * 0.5f,
        center.y + size * 0.6f
    );
    draw->AddText(ImGui::GetFont(), 10.0f, textPos, color, text);
}

void DrawVolumeIcon(ImDrawList* draw, ImVec2 pos, float volume, bool muted, ImU32 color) {
    float size = 20.0f;
    
    // Speaker cone
    draw->AddRectFilled(
        ImVec2(pos.x, pos.y + size * 0.3f),
        ImVec2(pos.x + size * 0.25f, pos.y + size * 0.7f),
        color, 1.0f
    );
    
    ImVec2 triangle[3] = {
        ImVec2(pos.x + size * 0.25f, pos.y + size * 0.3f),
        ImVec2(pos.x + size * 0.25f, pos.y + size * 0.7f),
        ImVec2(pos.x + size * 0.5f, pos.y + size * 0.85f),
    };
    draw->AddQuadFilled(
        ImVec2(pos.x + size * 0.25f, pos.y + size * 0.3f),
        ImVec2(pos.x + size * 0.5f, pos.y + size * 0.15f),
        ImVec2(pos.x + size * 0.5f, pos.y + size * 0.85f),
        ImVec2(pos.x + size * 0.25f, pos.y + size * 0.7f),
        color
    );
    
    if (muted) {
        // X mark
        draw->AddLine(
            ImVec2(pos.x + size * 0.6f, pos.y + size * 0.3f),
            ImVec2(pos.x + size * 0.95f, pos.y + size * 0.7f),
            color, 2.0f
        );
        draw->AddLine(
            ImVec2(pos.x + size * 0.95f, pos.y + size * 0.3f),
            ImVec2(pos.x + size * 0.6f, pos.y + size * 0.7f),
            color, 2.0f
        );
    } else {
        // Sound waves based on volume
        int waves = volume > 0.66f ? 3 : (volume > 0.33f ? 2 : 1);
        for (int i = 0; i < waves; i++) {
            float offset = (i + 1) * 0.15f;
            draw->AddCircle(
                ImVec2(pos.x + size * 0.5f, pos.y + size * 0.5f),
                size * (0.35f + offset),
                color, 8, 1.5f
            );
        }
    }
}

void DrawSettingsIcon(ImDrawList* draw, ImVec2 center, float size, ImU32 color) {
    int teeth = 8;
    float outerRadius = size * 0.5f;
    float innerRadius = size * 0.35f;
    float centerRadius = size * 0.2f;
    const float PI = 3.14159265358979323846f;
    
    // Draw gear teeth
    for (int i = 0; i < teeth * 2; i++) {
        float angle = (i * PI / teeth);
        float radius = (i % 2 == 0) ? outerRadius : innerRadius;
        float nextAngle = ((i + 1) * PI / teeth);
        float nextRadius = ((i + 1) % 2 == 0) ? outerRadius : innerRadius;
        
        ImVec2 p1 = ImVec2(center.x + cosf(angle) * radius, center.y + sinf(angle) * radius);
        ImVec2 p2 = ImVec2(center.x + cosf(nextAngle) * nextRadius, center.y + sinf(nextAngle) * nextRadius);
        
        if (i < teeth * 2 - 1) {
            draw->AddLine(p1, p2, color, 2.0f);
        }
    }
    
    // Center circle
    draw->AddCircle(center, centerRadius, color, 16, 2.0f);
}

void DrawSubtitlesIcon(ImDrawList* draw, ImVec2 center, float size, ImU32 color) {
    float rectWidth = size * 0.8f;
    float rectHeight = size * 0.6f;
    
    // Outline rectangle
    draw->AddRect(
        ImVec2(center.x - rectWidth * 0.5f, center.y - rectHeight * 0.5f),
        ImVec2(center.x + rectWidth * 0.5f, center.y + rectHeight * 0.5f),
        color, 2.0f, 0, 2.0f
    );
    
    // "CC" text
    draw->AddText(ImGui::GetFont(), size * 0.4f,
        ImVec2(center.x - size * 0.2f, center.y - size * 0.2f),
        color, "CC");
}

void DrawFullscreenIcon(ImDrawList* draw, ImVec2 center, float size, ImU32 color) {
    float cornerSize = size * 0.25f;
    float gap = size * 0.4f;
    
    // Four corners pointing outward
    // Top-left
    draw->AddLine(ImVec2(center.x - gap, center.y - gap), 
                  ImVec2(center.x - gap + cornerSize, center.y - gap), color, 2.0f);
    draw->AddLine(ImVec2(center.x - gap, center.y - gap), 
                  ImVec2(center.x - gap, center.y - gap + cornerSize), color, 2.0f);
    
    // Top-right
    draw->AddLine(ImVec2(center.x + gap, center.y - gap), 
                  ImVec2(center.x + gap - cornerSize, center.y - gap), color, 2.0f);
    draw->AddLine(ImVec2(center.x + gap, center.y - gap), 
                  ImVec2(center.x + gap, center.y - gap + cornerSize), color, 2.0f);
    
    // Bottom-left
    draw->AddLine(ImVec2(center.x - gap, center.y + gap), 
                  ImVec2(center.x - gap + cornerSize, center.y + gap), color, 2.0f);
    draw->AddLine(ImVec2(center.x - gap, center.y + gap), 
                  ImVec2(center.x - gap, center.y + gap - cornerSize), color, 2.0f);
    
    // Bottom-right
    draw->AddLine(ImVec2(center.x + gap, center.y + gap), 
                  ImVec2(center.x + gap - cornerSize, center.y + gap), color, 2.0f);
    draw->AddLine(ImVec2(center.x + gap, center.y + gap), 
                  ImVec2(center.x + gap, center.y + gap - cornerSize), color, 2.0f);
}

void RenderMenuBar(AppState& state) {
    ImGuiIO& io = ImGui::GetIO();
    
    // Check if mouse is in top 50px
    if (io.MousePos.y < 50.0f || ImGui::IsPopupOpen("", ImGuiPopupFlags_AnyPopup)) {
        state.showMenuBar = true;
    } else if (!ImGui::IsPopupOpen("", ImGuiPopupFlags_AnyPopup)) {
        state.showMenuBar = state.showControls;
    }
    
    if (!state.showMenuBar) return;
    
    if (ImGui::BeginMainMenuBar()) {
        // Media Menu
        if (ImGui::BeginMenu("Media")) {
            if (ImGui::MenuItem("Open File...", "Cmd+O")) { /* TODO */ }
            if (ImGui::MenuItem("Open Folder...", "Cmd+Shift+O")) { /* TODO */ }
            if (ImGui::BeginMenu("Open Recent")) {
                ImGui::MenuItem("(No recent files)", nullptr, false, false);
                ImGui::EndMenu();
            }
            ImGui::Separator();
            if (ImGui::MenuItem("Open Network Stream...", "Cmd+N")) { /* TODO */ }
            ImGui::Separator();
            if (ImGui::MenuItem("Quit", "Cmd+Q")) { /* TODO: Exit */ }
            ImGui::EndMenu();
        }
        
        // Playback Menu
        if (ImGui::BeginMenu("Playback")) {
            if (ImGui::MenuItem(state.isPlaying ? "Pause" : "Play", "Space")) {
                state.isPlaying = !state.isPlaying;
            }
            if (ImGui::MenuItem("Stop", "Cmd+S", false, state.isPlaying)) {
                state.isPlaying = false;
                state.currentTime = 0.0f;
            }
            ImGui::Separator();
            
            // Speed submenu
            if (ImGui::BeginMenu("Speed")) {
                const char* speeds[] = { "0.25x", "0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "1.75x", "2.0x" };
                float speedValues[] = { 0.25f, 0.5f, 0.75f, 1.0f, 1.25f, 1.5f, 1.75f, 2.0f };
                for (int i = 0; i < 8; i++) {
                    bool selected = (fabs(state.playbackSpeed - speedValues[i]) < 0.01f);
                    if (ImGui::MenuItem(speeds[i], nullptr, selected)) {
                        state.playbackSpeed = speedValues[i];
                    }
                }
                ImGui::EndMenu();
            }
            
            ImGui::Separator();
            if (ImGui::MenuItem("Jump Forward", "Cmd+Alt+Right", false, state.currentTime < state.duration)) {
                state.currentTime = fminf(state.currentTime + 10.0f, state.duration);
            }
            if (ImGui::MenuItem("Jump Backward", "Cmd+Alt+Left", false, state.currentTime > 0)) {
                state.currentTime = fmaxf(state.currentTime - 10.0f, 0.0f);
            }
            ImGui::EndMenu();
        }
        
        // Audio Menu
        if (ImGui::BeginMenu("Audio")) {
            if (ImGui::BeginMenu("Audio Track")) {
                ImGui::MenuItem("Track 1 - Stereo", nullptr, true);
                ImGui::Separator();
                ImGui::MenuItem("Disable", nullptr, false);
                ImGui::EndMenu();
            }
            ImGui::Separator();
            if (ImGui::MenuItem("Increase Volume", "Cmd+Up")) {
                state.volume = fminf(state.volume + 0.1f, 1.0f);
            }
            if (ImGui::MenuItem("Decrease Volume", "Cmd+Down")) {
                state.volume = fmaxf(state.volume - 0.1f, 0.0f);
            }
            if (ImGui::MenuItem(state.isMuted ? "Unmute" : "Mute", "M")) {
                state.isMuted = !state.isMuted;
            }
            ImGui::EndMenu();
        }
        
        // Video Menu
        if (ImGui::BeginMenu("Video")) {
            if (ImGui::BeginMenu("Video Track")) {
                ImGui::MenuItem("Track 1 - H.264", nullptr, true);
                ImGui::EndMenu();
            }
            ImGui::Separator();
            if (ImGui::MenuItem("Fullscreen", "F")) { /* TODO */ }
            ImGui::Separator();
            
            // Aspect Ratio submenu
            if (ImGui::BeginMenu("Aspect Ratio")) {
                const char* aspects[] = { "Original", "16:9", "16:10", "4:3", "1.85:1", "2.35:1" };
                for (int i = 0; i < 6; i++) {
                    if (ImGui::MenuItem(aspects[i], nullptr, state.aspectRatioIndex == i)) {
                        state.aspectRatioIndex = i;
                    }
                }
                ImGui::EndMenu();
            }
            
            // Crop submenu
            if (ImGui::BeginMenu("Crop")) {
                const char* crops[] = { "None", "16:9", "4:3", "1.85:1", "2.35:1" };
                for (int i = 0; i < 5; i++) {
                    if (ImGui::MenuItem(crops[i], nullptr, state.cropIndex == i)) {
                        state.cropIndex = i;
                    }
                }
                ImGui::EndMenu();
            }
            
            ImGui::Separator();
            if (ImGui::MenuItem("Take Snapshot", "Cmd+Shift+S")) { /* TODO */ }
            ImGui::EndMenu();
        }
        
        // Subtitles Menu
        if (ImGui::BeginMenu("Subtitles")) {
            if (ImGui::BeginMenu("Subtitle Track")) {
                ImGui::MenuItem("Disabled", nullptr, true);
                ImGui::Separator();
                ImGui::MenuItem("Load Subtitle File...", "Cmd+Shift+L");
                ImGui::EndMenu();
            }
            ImGui::EndMenu();
        }
        
        // Tools Menu
        if (ImGui::BeginMenu("Tools")) {
            if (ImGui::MenuItem("Media Information...", "Cmd+I")) { /* TODO */ }
            if (ImGui::MenuItem("Codec Information...", "Cmd+J")) { /* TODO */ }
            ImGui::Separator();
            if (ImGui::MenuItem("Playlist", "Cmd+L")) { /* TODO */ }
            ImGui::Separator();
            if (ImGui::MenuItem("Preferences...", "Cmd+,")) { /* TODO */ }
            ImGui::EndMenu();
        }
        
        // View Menu
        if (ImGui::BeginMenu("View")) {
            if (ImGui::MenuItem("Playlist Panel", "Cmd+Shift+L", false)) { /* TODO */ }
            ImGui::MenuItem("Control Bar", nullptr, true);
            ImGui::EndMenu();
        }
        
        // Help Menu
        if (ImGui::BeginMenu("Help")) {
            if (ImGui::MenuItem("Documentation")) { /* TODO */ }
            if (ImGui::MenuItem("Keyboard Shortcuts", "Cmd+?")) { /* TODO */ }
            ImGui::Separator();
            if (ImGui::MenuItem("About")) { /* TODO */ }
            ImGui::EndMenu();
        }
        
        ImGui::EndMainMenuBar();
    }
}

void RenderNetflixUI(AppState& state) {
    ImGuiIO& io = ImGui::GetIO();
    ImVec2 screenSize = io.DisplaySize;
    ImDrawList* drawList = ImGui::GetBackgroundDrawList();
    
    // Fullscreen window
    ImGui::SetNextWindowPos(ImVec2(0, 0));
    ImGui::SetNextWindowSize(screenSize);
    ImGui::Begin("##MainWindow", nullptr, 
        ImGuiWindowFlags_NoDecoration | 
        ImGuiWindowFlags_NoMove | 
        ImGuiWindowFlags_NoResize | 
        ImGuiWindowFlags_NoSavedSettings |
        ImGuiWindowFlags_NoBackground |
        ImGuiWindowFlags_NoBringToFrontOnFocus);
    
    // Video surface (black background with gradient)
    drawList->AddRectFilled(ImVec2(0, 0), screenSize, IM_COL32(0, 0, 0, 255));
    
    // Mock video content (subtle gradient)
    ImU32 gradientTop = IM_COL32(15, 15, 20, 255);
    ImU32 gradientBottom = IM_COL32(8, 8, 12, 255);
    DrawGradientOverlay(drawList, ImVec2(0, 0), screenSize, gradientTop, gradientBottom);
    
    // Centered branding
    const char* brandText = "SIMPLE MEDIA PLAYER V2";
    const char* subText = "Netflix-Inspired UI  |  Phase 1: GUI Complete";
    ImVec2 brandSize = ImGui::CalcTextSize(brandText);
    ImVec2 subSize = ImGui::CalcTextSize(subText);
    
    drawList->AddText(
        ImGui::GetFont(), 42.0f,
        ImVec2(screenSize.x * 0.5f - brandSize.x * 1.4f, screenSize.y * 0.45f - 30),
        IM_COL32(255, 255, 255, 80),
        brandText
    );
    drawList->AddText(
        ImVec2(screenSize.x * 0.5f - subSize.x * 0.5f, screenSize.y * 0.45f + 30),
        IM_COL32(190, 190, 190, 60),
        subText
    );
    
    // Click anywhere to play/pause
    ImGui::SetCursorPos(ImVec2(0, 0));
    ImGui::InvisibleButton("##VideoSurface", screenSize);
    if (ImGui::IsItemClicked(0)) {
        state.isPlaying = !state.isPlaying;
        state.showControls = true;
        state.controlsTimer = 3.0f;
    }
    
    // Detect mouse movement
    static ImVec2 lastMousePos = io.MousePos;
    if (io.MousePos.x != lastMousePos.x || io.MousePos.y != lastMousePos.y) {
        state.showControls = true;
        state.showMenuBar = true;
        state.controlsTimer = 3.0f;
        lastMousePos = io.MousePos;
    }
    
    // Auto-hide controls
    if (state.isPlaying && state.showControls && state.controlsTimer > 0.0f) {
        state.controlsTimer -= io.DeltaTime;
        if (state.controlsTimer <= 0.0f) {
            state.showControls = false;
            state.showMenuBar = false;
        }
    }
    
    // Mock playback
    if (state.isPlaying) {
        state.currentTime += io.DeltaTime * state.playbackSpeed;
        if (state.currentTime > state.duration) {
            state.currentTime = state.duration;
            state.isPlaying = false;
        }
    }
    
    // Controls overlay
    if (state.showControls) {
        float alpha = 1.0f;
        if (state.controlsTimer < 0.5f && state.controlsTimer > 0.0f) {
            alpha = state.controlsTimer * 2.0f;
        }
        
        ImGui::PushStyleVar(ImGuiStyleVar_Alpha, alpha);
        
        // Gradient overlay (300px from bottom)
        float gradientHeight = 300.0f;
        ImVec2 gradientStart = ImVec2(0, screenSize.y - gradientHeight);
        ImU32 gradTop = IM_COL32(0, 0, 0, 0);
        ImU32 gradMid = IM_COL32(0, 0, 0, 128);
        ImU32 gradBot = IM_COL32(0, 0, 0, 200);
        
        // Draw gradient in segments for smooth transition
        float segmentHeight = gradientHeight / 3.0f;
        DrawGradientOverlay(drawList, 
            ImVec2(0, gradientStart.y), 
            ImVec2(screenSize.x, gradientStart.y + segmentHeight),
            gradTop, IM_COL32(0, 0, 0, 50));
        DrawGradientOverlay(drawList,
            ImVec2(0, gradientStart.y + segmentHeight),
            ImVec2(screenSize.x, gradientStart.y + segmentHeight * 2),
            IM_COL32(0, 0, 0, 50), gradMid);
        DrawGradientOverlay(drawList,
            ImVec2(0, gradientStart.y + segmentHeight * 2),
            screenSize,
            gradMid, gradBot);
        
        // Title (top of controls area)
        float titleY = screenSize.y - 260;
        drawList->AddText(ImGui::GetFont(), 28.0f,
            ImVec2(50, titleY),
            IM_COL32(255, 255, 255, (int)(255 * alpha)),
            state.currentTitle.c_str()
        );
        
        // Progress bar (80px from bottom, 50px from sides)
        float progressY = screenSize.y - 80;
        float progressWidth = screenSize.x - 100;
        
        ImGui::SetCursorPos(ImVec2(50, progressY));
        ImGui::PushStyleColor(ImGuiCol_FrameBg, ImVec4(0.16f, 0.16f, 0.16f, 0.8f));
        ImGui::PushStyleColor(ImGuiCol_SliderGrab, ImVec4(0.898f, 0.035f, 0.078f, 1.0f));
        ImGui::PushStyleColor(ImGuiCol_SliderGrabActive, ImVec4(1.0f, 0.05f, 0.09f, 1.0f));
        ImGui::PushStyleVar(ImGuiStyleVar_GrabMinSize, 16.0f);
        
        ImGui::PushItemWidth(progressWidth);
        bool progressHovered = false;
        if (ImGui::SliderFloat("##Progress", &state.currentTime, 0.0f, state.duration, "")) {
            // Seeking
        }
        progressHovered = ImGui::IsItemHovered();
        ImGui::PopItemWidth();
        
        // Draw custom progress bar appearance
        ImVec2 progressBarMin = ImVec2(50, progressY);
        ImVec2 progressBarMax = ImVec2(50 + progressWidth, progressY + 6);
        float progress = state.currentTime / state.duration;
        
        // Background track
        drawList->AddRectFilled(progressBarMin, progressBarMax, 
            IM_COL32(70, 70, 70, (int)(200 * alpha)), 2.0f);
        
        // Progress fill (Netflix red)
        drawList->AddRectFilled(progressBarMin, 
            ImVec2(progressBarMin.x + progressWidth * progress, progressBarMax.y),
            IM_COL32(229, 9, 20, (int)(255 * alpha)), 2.0f);
        
        // Scrubber circle
        if (progressHovered) {
            ImVec2 scrubberPos = ImVec2(progressBarMin.x + progressWidth * progress, progressY + 3);
            drawList->AddCircleFilled(scrubberPos, 8.0f, 
                IM_COL32(229, 9, 20, (int)(255 * alpha)), 16);
        }
        
        ImGui::PopStyleVar();
        ImGui::PopStyleColor(3);
        
        // Control buttons (40px from bottom)
        float controlsY = screenSize.y - 40;
        ImGui::SetCursorPos(ImVec2(50, controlsY - 24));
        
        ImGui::PushStyleColor(ImGuiCol_Button, ImVec4(0, 0, 0, 0));
        ImGui::PushStyleColor(ImGuiCol_ButtonHovered, ImVec4(1, 1, 1, 0.1f));
        ImGui::PushStyleColor(ImGuiCol_ButtonActive, ImVec4(1, 1, 1, 0.15f));
        
        // Play/Pause button (48x48)
        ImVec2 playButtonPos = ImGui::GetCursorScreenPos();
        if (ImGui::Button("##PlayPause", ImVec2(48, 48))) {
            state.isPlaying = !state.isPlaying;
        }
        ImVec2 playIconCenter = ImVec2(playButtonPos.x + 24, playButtonPos.y + 24);
        if (state.isPlaying) {
            DrawPauseIcon(drawList, playIconCenter, 24.0f, IM_COL32(255, 255, 255, (int)(255 * alpha)));
        } else {
            DrawPlayIcon(drawList, playIconCenter, 24.0f, IM_COL32(255, 255, 255, (int)(255 * alpha)));
        }
        
        ImGui::SameLine(0, 8);
        
        // Skip backward button (40x40)
        ImVec2 skipBackPos = ImGui::GetCursorScreenPos();
        if (ImGui::Button("##SkipBack", ImVec2(40, 40))) {
            state.currentTime = fmaxf(state.currentTime - 10.0f, 0.0f);
        }
        DrawSkipIcon(drawList, ImVec2(skipBackPos.x + 20, skipBackPos.y + 20), 16.0f, false,
            IM_COL32(255, 255, 255, (int)(255 * alpha)));
        
        ImGui::SameLine(0, 8);
        
        // Skip forward button (40x40)
        ImVec2 skipForwardPos = ImGui::GetCursorScreenPos();
        if (ImGui::Button("##SkipForward", ImVec2(40, 40))) {
            state.currentTime = fminf(state.currentTime + 10.0f, state.duration);
        }
        DrawSkipIcon(drawList, ImVec2(skipForwardPos.x + 20, skipForwardPos.y + 20), 16.0f, true,
            IM_COL32(255, 255, 255, (int)(255 * alpha)));
        
        ImGui::SameLine(0, 16);
        
        // Volume icon and slider
        ImVec2 volumeIconPos = ImGui::GetCursorScreenPos();
        if (ImGui::Button("##VolumeIcon", ImVec2(32, 32))) {
            state.isMuted = !state.isMuted;
        }
        DrawVolumeIcon(drawList, ImVec2(volumeIconPos.x + 6, volumeIconPos.y + 6), 
            state.volume, state.isMuted, IM_COL32(255, 255, 255, (int)(255 * alpha)));
        
        ImGui::SameLine(0, 8);
        
        // Volume slider
        ImGui::SetCursorPosY(controlsY - 16);
        ImGui::PushItemWidth(100);
        ImGui::SliderFloat("##Volume", &state.volume, 0.0f, 1.0f, "");
        ImGui::PopItemWidth();
        
        ImGui::SameLine(0, 24);
        
        // Time display
        std::string timeStr = FormatTime(state.currentTime) + " / " + FormatTime(state.duration);
        drawList->AddText(ImVec2(ImGui::GetCursorScreenPos().x, controlsY - 8),
            IM_COL32(255, 255, 255, (int)(230 * alpha)), timeStr.c_str());
        
        // Right-side controls
        float rightControlsX = screenSize.x - 200;
        ImGui::SetCursorPos(ImVec2(rightControlsX, controlsY - 16));
        
        // Settings button
        ImVec2 settingsPos = ImGui::GetCursorScreenPos();
        if (ImGui::Button("##Settings", ImVec2(32, 32))) {
            // TODO: Open settings
        }
        DrawSettingsIcon(drawList, ImVec2(settingsPos.x + 16, settingsPos.y + 16), 20.0f,
            IM_COL32(255, 255, 255, (int)(255 * alpha)));
        
        ImGui::SameLine(0, 8);
        
        // Subtitles button
        ImVec2 subtitlesPos = ImGui::GetCursorScreenPos();
        if (ImGui::Button("##Subtitles", ImVec2(32, 32))) {
            // TODO: Open subtitles menu
        }
        DrawSubtitlesIcon(drawList, ImVec2(subtitlesPos.x + 16, subtitlesPos.y + 16), 20.0f,
            IM_COL32(255, 255, 255, (int)(255 * alpha)));
        
        ImGui::SameLine(0, 8);
        
        // Fullscreen button
        ImVec2 fullscreenPos = ImGui::GetCursorScreenPos();
        if (ImGui::Button("##Fullscreen", ImVec2(32, 32))) {
            // TODO: Toggle fullscreen
        }
        DrawFullscreenIcon(drawList, ImVec2(fullscreenPos.x + 16, fullscreenPos.y + 16), 18.0f,
            IM_COL32(255, 255, 255, (int)(255 * alpha)));
        
        ImGui::PopStyleColor(3);
        
        // "Next in Folder" button (Netflix style, bottom-right)
        ImGui::SetCursorPos(ImVec2(screenSize.x - 260, screenSize.y - 100));
        ImGui::PushStyleColor(ImGuiCol_Button, ImVec4(0.95f, 0.95f, 0.95f, 0.92f));
        ImGui::PushStyleColor(ImGuiCol_ButtonHovered, ImVec4(1.0f, 1.0f, 1.0f, 1.0f));
        ImGui::PushStyleColor(ImGuiCol_ButtonActive, ImVec4(0.9f, 0.9f, 0.9f, 1.0f));
        ImGui::PushStyleColor(ImGuiCol_Text, ImVec4(0.0f, 0.0f, 0.0f, 1.0f));
        
        if (ImGui::Button("Next in Folder  \xE2\x96\xB6", ImVec2(200, 50))) {
            // TODO: Open playlist panel
        }
        
        ImGui::PopStyleColor(4);
        
        ImGui::PopStyleVar(); // Alpha
    }
    
    ImGui::End();
}

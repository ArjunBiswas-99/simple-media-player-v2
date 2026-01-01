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

// Forward declarations
void SetupNetflixTheme();
void RenderNetflixUI(bool& showControls, float& controlsTimer, bool& isPlaying, 
                     float& currentTime, float& duration, float& volume, bool& isMuted);

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

    // State management
    static bool showControls = true;
    static float controlsTimer = 3.0f;
    static bool isPlaying = false;
    static float currentTime = 0.0f;
    static float duration = 125.0f; // Mock duration (2:05)
    static float volume = 1.0f;
    static bool isMuted = false;

    // Render Netflix UI
    RenderNetflixUI(showControls, controlsTimer, isPlaying, currentTime, duration, volume, isMuted);

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

    // State
    bool showControls = true;
    float controlsTimer = 3.0f;
    bool isPlaying = false;
    float currentTime = 0.0f;
    float duration = 125.0f;
    float volume = 1.0f;
    bool isMuted = false;

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

        // Render Netflix UI
        RenderNetflixUI(showControls, controlsTimer, isPlaying, currentTime, duration, volume, isMuted);

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
    const ImVec4 darkGray = ImVec4(0.2f, 0.2f, 0.2f, 1.0f);              // #333333
    const ImVec4 lightGray = ImVec4(0.7f, 0.7f, 0.7f, 1.0f);             // #B3B3B3
    const ImVec4 white = ImVec4(1.0f, 1.0f, 1.0f, 1.0f);

    // Main colors
    colors[ImGuiCol_WindowBg] = darkBg;
    colors[ImGuiCol_ChildBg] = ImVec4(0.0f, 0.0f, 0.0f, 0.0f);
    colors[ImGuiCol_PopupBg] = darkBg;
    colors[ImGuiCol_Border] = ImVec4(0.3f, 0.3f, 0.3f, 0.5f);
    colors[ImGuiCol_FrameBg] = darkGray;
    colors[ImGuiCol_FrameBgHovered] = ImVec4(0.3f, 0.3f, 0.3f, 1.0f);
    colors[ImGuiCol_FrameBgActive] = ImVec4(0.4f, 0.4f, 0.4f, 1.0f);
    colors[ImGuiCol_TitleBg] = darkBg;
    colors[ImGuiCol_TitleBgActive] = darkBg;
    colors[ImGuiCol_TitleBgCollapsed] = darkBg;
    
    // Button colors
    colors[ImGuiCol_Button] = netflixRed;
    colors[ImGuiCol_ButtonHovered] = ImVec4(1.0f, 0.05f, 0.09f, 1.0f);
    colors[ImGuiCol_ButtonActive] = ImVec4(0.7f, 0.03f, 0.06f, 1.0f);
    
    // Slider colors
    colors[ImGuiCol_SliderGrab] = white;
    colors[ImGuiCol_SliderGrabActive] = lightGray;
    
    // Text
    colors[ImGuiCol_Text] = white;
    colors[ImGuiCol_TextDisabled] = lightGray;
    
    // Rounding
    style.WindowRounding = 0.0f;
    style.ChildRounding = 0.0f;
    style.FrameRounding = 4.0f;
    style.GrabRounding = 12.0f;
    style.PopupRounding = 4.0f;
    style.ScrollbarRounding = 9.0f;
    
    // Spacing
    style.WindowPadding = ImVec2(0, 0);
    style.FramePadding = ImVec2(8, 4);
    style.ItemSpacing = ImVec2(12, 8);
    style.ItemInnerSpacing = ImVec2(8, 6);
    style.IndentSpacing = 25.0f;
    style.ScrollbarSize = 15.0f;
    style.GrabMinSize = 12.0f;
}

std::string FormatTime(float seconds) {
    int mins = (int)seconds / 60;
    int secs = (int)seconds % 60;
    char buf[32];
    snprintf(buf, sizeof(buf), "%d:%02d", mins, secs);
    return std::string(buf);
}

void DrawPlayIcon(ImDrawList* draw, ImVec2 center, float size, ImU32 color) {
    ImVec2 points[3] = {
        ImVec2(center.x - size * 0.3f, center.y - size * 0.5f),
        ImVec2(center.x - size * 0.3f, center.y + size * 0.5f),
        ImVec2(center.x + size * 0.5f, center.y)
    };
    draw->AddTriangleFilled(points[0], points[1], points[2], color);
}

void DrawPauseIcon(ImDrawList* draw, ImVec2 center, float size, ImU32 color) {
    float barWidth = size * 0.25f;
    float barHeight = size;
    float spacing = size * 0.3f;
    
    draw->AddRectFilled(
        ImVec2(center.x - spacing - barWidth, center.y - barHeight * 0.5f),
        ImVec2(center.x - spacing, center.y + barHeight * 0.5f),
        color
    );
    draw->AddRectFilled(
        ImVec2(center.x + spacing, center.y - barHeight * 0.5f),
        ImVec2(center.x + spacing + barWidth, center.y + barHeight * 0.5f),
        color
    );
}

void RenderNetflixUI(bool& showControls, float& controlsTimer, bool& isPlaying, 
                     float& currentTime, float& duration, float& volume, bool& isMuted) {
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
        ImGuiWindowFlags_NoBackground);
    
    // Mock video surface (black background)
    drawList->AddRectFilled(ImVec2(0, 0), screenSize, IM_COL32(0, 0, 0, 255));
    
    // Mock video content (gradient for visual feedback)
    ImU32 gradientTop = IM_COL32(20, 20, 30, 255);
    ImU32 gradientBottom = IM_COL32(10, 10, 15, 255);
    drawList->AddRectFilledMultiColor(
        ImVec2(0, 0), screenSize,
        gradientTop, gradientTop, gradientBottom, gradientBottom
    );
    
    // Add centered text showing it's a mock player
    const char* mockText = "Netflix-Style Media Player";
    const char* mockSubtext = "(GUI Demo - Video playback in Phase 2)";
    ImVec2 textSize = ImGui::CalcTextSize(mockText);
    ImVec2 subtextSize = ImGui::CalcTextSize(mockSubtext);
    
    drawList->AddText(
        ImGui::GetFont(), 48.0f,
        ImVec2(screenSize.x * 0.5f - textSize.x, screenSize.y * 0.5f - 50),
        IM_COL32(255, 255, 255, 100),
        mockText
    );
    drawList->AddText(
        ImVec2(screenSize.x * 0.5f - subtextSize.x * 0.5f, screenSize.y * 0.5f + 10),
        IM_COL32(180, 180, 180, 80),
        mockSubtext
    );
    
    // Click anywhere to play/pause
    ImGui::SetCursorPos(ImVec2(0, 0));
    ImGui::InvisibleButton("##VideoSurface", screenSize);
    if (ImGui::IsItemClicked(0)) {
        isPlaying = !isPlaying;
        showControls = true;
        controlsTimer = 3.0f;
    }
    
    // Detect mouse movement
    static ImVec2 lastMousePos = io.MousePos;
    if (io.MousePos.x != lastMousePos.x || io.MousePos.y != lastMousePos.y) {
        showControls = true;
        controlsTimer = 3.0f;
        lastMousePos = io.MousePos;
    }
    
    // Auto-hide controls
    if (isPlaying && showControls && controlsTimer > 0.0f) {
        controlsTimer -= io.DeltaTime;
        if (controlsTimer <= 0.0f) {
            showControls = false;
        }
    }
    
    // Mock playback
    if (isPlaying) {
        currentTime += io.DeltaTime;
        if (currentTime > duration) {
            currentTime = 0.0f;
            isPlaying = false;
        }
    }
    
    // Controls overlay
    if (showControls) {
        float alpha = 1.0f;
        if (controlsTimer < 0.5f && controlsTimer > 0.0f) {
            alpha = controlsTimer * 2.0f; // Fade out
        }
        
        ImGui::PushStyleVar(ImGuiStyleVar_Alpha, alpha);
        
        // Bottom gradient overlay
        float gradientHeight = screenSize.y * 0.35f;
        ImVec2 gradientStart = ImVec2(0, screenSize.y - gradientHeight);
        drawList->AddRectFilledMultiColor(
            gradientStart, screenSize,
            IM_COL32(0, 0, 0, 0), IM_COL32(0, 0, 0, 0),
            IM_COL32(0, 0, 0, 200), IM_COL32(0, 0, 0, 200)
        );
        
        // Controls container
        float controlsY = screenSize.y - 150;
        ImGui::SetCursorPos(ImVec2(60, controlsY));
        ImGui::BeginGroup();
        
        // Play/Pause button
        ImGui::PushStyleColor(ImGuiCol_Button, ImVec4(0, 0, 0, 0));
        ImGui::PushStyleColor(ImGuiCol_ButtonHovered, ImVec4(1, 1, 1, 0.1f));
        ImGui::PushStyleColor(ImGuiCol_ButtonActive, ImVec4(1, 1, 1, 0.2f));
        
        ImVec2 buttonPos = ImGui::GetCursorScreenPos();
        ImVec2 buttonSize(50, 50);
        
        if (ImGui::Button("##PlayPause", buttonSize)) {
            isPlaying = !isPlaying;
        }
        
        // Draw play/pause icon
        ImVec2 iconCenter = ImVec2(buttonPos.x + 25, buttonPos.y + 25);
        if (isPlaying) {
            DrawPauseIcon(drawList, iconCenter, 20.0f, IM_COL32(255, 255, 255, 255));
        } else {
            DrawPlayIcon(drawList, iconCenter, 20.0f, IM_COL32(255, 255, 255, 255));
        }
        
        ImGui::PopStyleColor(3);
        
        ImGui::SameLine();
        
        // Volume control (simplified for now)
        ImGui::PushItemWidth(100);
        ImGui::SliderFloat("##Volume", &volume, 0.0f, 1.0f, "");
        ImGui::PopItemWidth();
        
        ImGui::SameLine();
        ImGui::Text("   %s / %s", FormatTime(currentTime).c_str(), FormatTime(duration).c_str());
        
        ImGui::EndGroup();
        
        // Progress bar
        float progressBarY = screenSize.y - 80;
        ImGui::SetCursorPos(ImVec2(60, progressBarY));
        
        ImGui::PushStyleColor(ImGuiCol_FrameBg, ImVec4(0.5f, 0.5f, 0.5f, 0.3f));
        ImGui::PushStyleColor(ImGuiCol_SliderGrab, ImVec4(0.898f, 0.035f, 0.078f, 1.0f)); // Netflix red
        ImGui::PushStyleColor(ImGuiCol_SliderGrabActive, ImVec4(1.0f, 0.05f, 0.09f, 1.0f));
        ImGui::PushStyleVar(ImGuiStyleVar_GrabMinSize, 12.0f);
        
        ImGui::PushItemWidth(screenSize.x - 120);
        if (ImGui::SliderFloat("##Progress", &currentTime, 0.0f, duration, "")) {
            // Seeking
        }
        ImGui::PopItemWidth();
        
        ImGui::PopStyleVar();
        ImGui::PopStyleColor(3);
        
        // "Next in Folder" button (bottom-right)
        ImGui::SetCursorPos(ImVec2(screenSize.x - 260, screenSize.y - 100));
        ImGui::PushStyleColor(ImGuiCol_Button, ImVec4(0.9f, 0.9f, 0.9f, 0.9f));
        ImGui::PushStyleColor(ImGuiCol_ButtonHovered, ImVec4(1.0f, 1.0f, 1.0f, 1.0f));
        ImGui::PushStyleColor(ImGuiCol_Text, ImVec4(0.0f, 0.0f, 0.0f, 1.0f));
        
        if (ImGui::Button("Next in Folder  >", ImVec2(200, 50))) {
            // Open playlist panel (Phase 3)
        }
        
        ImGui::PopStyleColor(3);
        
        ImGui::PopStyleVar(); // Alpha
    }
    
    ImGui::End();
}

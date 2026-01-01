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
#include <filesystem>
#include <algorithm>
#include <numeric>

#include "VideoDecoder.h"
#include "AudioOutput.h"

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
    bool showPlaylistPanel = false;
    float timeSinceFileLoad = 0.0f;  // Track time since file opened
    bool isFullscreen = false;  // Fullscreen state
    
    // Directory playlist (files in same folder as current video)
    std::vector<std::string> playlistFiles;  // Full paths
    std::vector<std::string> playlistNames;  // Display names (filenames only)
    int currentPlaylistIndex = -1;
    std::string currentDirectory = "";
    
    // Skip animation state
    bool showSkipAnimation = false;
    float skipAnimationTimer = 0.0f;
    int skipAnimationDirection = 0;  // -1 = backward, +1 = forward
    
    // Subtitle/audio selection
    bool showSubtitleMenu = false;
    bool showAudioMenu = false;
    
    // Video playback
    VideoDecoder* decoder = nullptr;
    AudioOutput* audioOutput = nullptr;
    id<MTLTexture> videoTexture = nil;
    bool fileLoaded = false;
    
    // A/V sync state
    VideoFrame* pendingFrame = nullptr;  // Frame waiting to be displayed
    double lastVideoFramePTS = 0.0;      // PTS of last displayed frame
    double videoStartTime = 0.0;         // System time when video started
    int droppedFrames = 0;               // Count of dropped frames
    int displayedFrames = 0;             // Count of displayed frames
};

#ifdef __APPLE__
// File picker dialog for macOS
std::string openFileDialog() {
    @autoreleasepool {
        NSOpenPanel* panel = [NSOpenPanel openPanel];
        [panel setCanChooseFiles:YES];
        [panel setCanChooseDirectories:NO];
        [panel setAllowsMultipleSelection:NO];
        [panel setTitle:@"Open Media File"];
        
        // File type filters
        [panel setAllowedFileTypes:@[@"mp4", @"mov", @"ts", @"mpeg", @"mpg", @"wmv", @"avi", @"mkv", @"mp3", @"wav"]];
        
        if ([panel runModal] == NSModalResponseOK) {
            NSURL* url = [[panel URLs] objectAtIndex:0];
            NSString* path = [url path];
            return std::string([path UTF8String]);
        }
    }
    return "";
}
#endif

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
void DrawAudioIcon(ImDrawList* draw, ImVec2 center, float size, ImU32 color);
void DrawFullscreenIcon(ImDrawList* draw, ImVec2 center, float size, ImU32 color);
void DrawPlaylistIcon(ImDrawList* draw, ImVec2 center, float size, ImU32 color);
void RenderPlaylistPanel(AppState& state, ImVec2 screenSize);

// Scan directory for media files
void ScanDirectoryForMediaFiles(AppState& state, const std::string& filePath) {
    namespace fs = std::filesystem;
    
    // Clear existing playlist
    state.playlistFiles.clear();
    state.playlistNames.clear();
    state.currentPlaylistIndex = -1;
    
    try {
        fs::path currentFile(filePath);
        fs::path directory = currentFile.parent_path();
        state.currentDirectory = directory.string();
        
        // Supported video extensions
        std::vector<std::string> videoExtensions = {
            ".mp4", ".mov", ".avi", ".mkv", ".wmv", ".ts", ".mpeg", ".mpg", ".m4v", ".flv"
        };
        
        // Iterate through files in directory
        for (const auto& entry : fs::directory_iterator(directory)) {
            if (entry.is_regular_file()) {
                std::string ext = entry.path().extension().string();
                // Convert extension to lowercase for comparison
                std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);
                
                // Check if file has video extension
                if (std::find(videoExtensions.begin(), videoExtensions.end(), ext) != videoExtensions.end()) {
                    state.playlistFiles.push_back(entry.path().string());
                    state.playlistNames.push_back(entry.path().filename().string());
                    
                    // Check if this is the current file
                    if (entry.path() == currentFile) {
                        state.currentPlaylistIndex = state.playlistFiles.size() - 1;
                    }
                }
            }
        }
        
        // Sort by filename if we have files
        if (!state.playlistFiles.empty()) {
            std::vector<size_t> indices(state.playlistFiles.size());
            std::iota(indices.begin(), indices.end(), 0);
            std::sort(indices.begin(), indices.end(), [&](size_t a, size_t b) {
                return state.playlistNames[a] < state.playlistNames[b];
            });
        
            std::vector<std::string> sortedFiles, sortedNames;
            int newCurrentIndex = -1;
            for (size_t i = 0; i < indices.size(); i++) {
                sortedFiles.push_back(state.playlistFiles[indices[i]]);
                sortedNames.push_back(state.playlistNames[indices[i]]);
                if (indices[i] == (size_t)state.currentPlaylistIndex) {
                    newCurrentIndex = i;
                }
            }
        
            state.playlistFiles = sortedFiles;
            state.playlistNames = sortedNames;
            state.currentPlaylistIndex = newCurrentIndex;
        }
        
    } catch (const std::exception& e) {
        std::cerr << "Error scanning directory: " << e.what() << std::endl;
    }
}

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
    
    // Load fonts - Netflix Sans alternative (SF Pro on macOS)
    // Try to load system font, fallback to default
    io.Fonts->Clear();
    
    // Primary font: SF Pro Display (similar to Netflix Sans)
    ImFontConfig fontConfig;
    fontConfig.SizePixels = 16.0f;
    strcpy(fontConfig.Name, "SF Pro Display");
    
    // Try to load SF Pro Display, fallback to Helvetica Neue
    ImFont* mainFont = io.Fonts->AddFontFromFileTTF("/System/Library/Fonts/SFCompact.ttf", 16.0f, &fontConfig);
    if (!mainFont) {
        mainFont = io.Fonts->AddFontFromFileTTF("/System/Library/Fonts/Helvetica.ttc", 16.0f, &fontConfig);
    }
    if (!mainFont) {
        io.Fonts->AddFontDefault();
    }
    
    // Large font for titles (28px)
    fontConfig.SizePixels = 28.0f;
    strcpy(fontConfig.Name, "SF Pro Display Bold");
    ImFont* titleFont = io.Fonts->AddFontFromFileTTF("/System/Library/Fonts/SFCompact.ttf", 28.0f, &fontConfig);
    
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
    
    // Get Metal device for texture operations
    id<MTLDevice> metalDevice = self.device;
    
    // Process video frames with A/V synchronization
    if (state.fileLoaded && state.decoder && state.decoder->hasVideo() && state.isPlaying) {
        // Get audio clock for synchronization
        double audioClock = 0.0;
        bool useAudioSync = false;
        
        if (state.audioOutput && state.decoder->hasAudio()) {
            audioClock = state.audioOutput->getAudioClock();
            // Only use audio sync if audio has actually started (clock > 0.01s)
            useAudioSync = (audioClock > 0.01);
        }
        
        // CRITICAL FIX: Only fetch new frame if we don't have a pending one
        // This prevents draining the queue too fast
        if (!state.pendingFrame) {
            state.pendingFrame = state.decoder->getNextVideoFrame();
            
            // Check if we reached end of stream
            if (!state.pendingFrame) {
                // No more frames - check if decoder is done
                if (!state.decoder->isPlaying()) {
                    state.isPlaying = false;
                    if (state.audioOutput) {
                        state.audioOutput->pause();
                    }
                }
            }
        }
        
        // Process the pending frame
        if (state.pendingFrame && state.pendingFrame->data && state.pendingFrame->width > 0 && state.pendingFrame->height > 0) {
            double videoPTS = state.pendingFrame->pts;
            double drift = 0.0;
            bool shouldDisplay = false;
            
            // Calculate drift based on sync mode
            if (useAudioSync) {
                drift = videoPTS - audioClock;
                
                // More aggressive thresholds for better sync
                const double SYNC_THRESHOLD = 0.040;  // 40ms - one frame at 25fps
                const double DROP_THRESHOLD = 0.100;  // 100ms - drop if too far behind
                const double NOSYNC_THRESHOLD = 0.5;  // 500ms - force resync
                
                // Check if we need to resync (after seek, audio glitch, etc)
                if (fabs(drift) > NOSYNC_THRESHOLD) {
                    // Large drift - force resync by setting audio clock to video
                    if (state.audioOutput) {
                        state.audioOutput->setAudioClock(videoPTS);
                    }
                    shouldDisplay = true;
                }
                // Video is too far behind - drop this frame to catch up
                else if (drift < -DROP_THRESHOLD) {
                    // Drop frame
                    delete state.pendingFrame;
                    state.pendingFrame = nullptr;
                    state.droppedFrames++;
                    shouldDisplay = false;
                }
                // Video is slightly ahead - wait a bit (but still display after threshold)
                else if (drift > SYNC_THRESHOLD) {
                    // Display it anyway to prevent freeze
                    // The slight ahead is tolerable and better than stuttering
                    shouldDisplay = true;
                }
                // In sync range - display it
                else {
                    shouldDisplay = true;
                }
            } else {
                // No audio sync - display all frames immediately
                shouldDisplay = true;
            }
            
            // Display the frame if it's time
            if (shouldDisplay && state.pendingFrame) {
                VideoFrame* frame = state.pendingFrame;
                state.pendingFrame = nullptr;  // Frame consumed
                
                // Update tracking
                state.lastVideoFramePTS = videoPTS;
                state.currentTime = (float)videoPTS;
                state.displayedFrames++;
                
                // Validate frame data before processing
                if (!frame || !frame->data || frame->width <= 0 || frame->height <= 0) {
                    std::cerr << "Invalid frame data, skipping frame" << std::endl;
                    if (frame) {
                        delete frame;
                    }
                } else {
                    // Create or update texture
                    if (!state.videoTexture || 
                        state.videoTexture.width != frame->width || 
                        state.videoTexture.height != frame->height) {
                        
                        MTLTextureDescriptor* textureDescriptor = [MTLTextureDescriptor
                            texture2DDescriptorWithPixelFormat:MTLPixelFormatRGBA8Unorm
                            width:frame->width
                            height:frame->height
                            mipmapped:NO];
                        textureDescriptor.usage = MTLTextureUsageShaderRead;
                        
                        state.videoTexture = [metalDevice newTextureWithDescriptor:textureDescriptor];
                        
                        if (!state.videoTexture) {
                            std::cerr << "Failed to create Metal texture" << std::endl;
                            delete frame;
                            frame = nullptr;
                        }
                    }
                    
                    if (frame && frame->data) {
                        // Convert RGB24 to RGBA8 and upload to texture
                        size_t rgbaSize = frame->width * frame->height * 4;
                        uint8_t* rgbaData = (uint8_t*)malloc(rgbaSize);
                        
                        if (rgbaData) {
                            // Convert RGB24 to RGBA8, accounting for linesize
                            for (int y = 0; y < frame->height; y++) {
                                for (int x = 0; x < frame->width; x++) {
                                    int srcIdx = y * frame->linesize + x * 3;
                                    int dstIdx = (y * frame->width + x) * 4;
                                    
                                    rgbaData[dstIdx + 0] = frame->data[srcIdx + 0]; // R
                                    rgbaData[dstIdx + 1] = frame->data[srcIdx + 1]; // G
                                    rgbaData[dstIdx + 2] = frame->data[srcIdx + 2]; // B
                                    rgbaData[dstIdx + 3] = 255;                      // A
                                }
                            }
                            
                            MTLRegion region = MTLRegionMake2D(0, 0, frame->width, frame->height);
                            [state.videoTexture replaceRegion:region
                                                  mipmapLevel:0
                                                    withBytes:rgbaData
                                                  bytesPerRow:frame->width * 4];
                            
                            free(rgbaData);
                        }
                        
                        // Update current time
                        state.currentTime = (float)frame->pts;
                    }
                    
                    // Always delete the frame after use
                    if (frame) {
                        delete frame;
                    }
                }
            }
        } else if (state.pendingFrame && (!state.pendingFrame->data || state.pendingFrame->width <= 0 || state.pendingFrame->height <= 0)) {
            // Pending frame is invalid, discard it
            delete state.pendingFrame;
            state.pendingFrame = nullptr;
        }
        
        // Process audio frames
        if (state.audioOutput && state.decoder->hasAudio()) {
            AudioFrame* audioFrame = state.decoder->getNextAudioFrame();
            if (audioFrame && audioFrame->data && audioFrame->size > 0) {
                state.audioOutput->pushAudioFrame(audioFrame);
            }
        }
    }

    // Render UI
    RenderMenuBar(state);
    RenderNetflixUI(state);
    RenderPlaylistPanel(state, ImVec2((float)view.bounds.size.width, (float)view.bounds.size.height));

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
        RenderPlaylistPanel(state, ImVec2((float)io.DisplaySize.x, (float)io.DisplaySize.y));

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

void DrawAudioIcon(ImDrawList* draw, ImVec2 center, float size, ImU32 color) {
    float radius = size * 0.4f;
    
    // Speaker cone (left side)
    ImVec2 speakerPoints[4] = {
        ImVec2(center.x - radius * 0.8f, center.y - radius * 0.5f),
        ImVec2(center.x - radius * 0.3f, center.y - radius * 0.5f),
        ImVec2(center.x - radius * 0.3f, center.y + radius * 0.5f),
        ImVec2(center.x - radius * 0.8f, center.y + radius * 0.5f)
    };
    draw->AddConvexPolyFilled(speakerPoints, 4, color);
    
    // Speaker base (small rectangle)
    draw->AddRectFilled(
        ImVec2(center.x - radius, center.y - radius * 0.3f),
        ImVec2(center.x - radius * 0.8f, center.y + radius * 0.3f),
        color
    );
    
    // Sound waves (three arcs)
    for (int i = 0; i < 3; i++) {
        float arcRadius = radius * 0.4f + i * radius * 0.3f;
        float startAngle = -0.5f;
        float endAngle = 0.5f;
        int segments = 8;
        
        for (int j = 0; j < segments; j++) {
            float angle1 = startAngle + (endAngle - startAngle) * j / segments;
            float angle2 = startAngle + (endAngle - startAngle) * (j + 1) / segments;
            
            ImVec2 p1 = ImVec2(center.x + cosf(angle1) * arcRadius, center.y + sinf(angle1) * arcRadius);
            ImVec2 p2 = ImVec2(center.x + cosf(angle2) * arcRadius, center.y + sinf(angle2) * arcRadius);
            
            draw->AddLine(p1, p2, color, 1.5f);
        }
    }
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

void DrawPlaylistIcon(ImDrawList* draw, ImVec2 center, float size, ImU32 color) {
    float lineWidth = size * 0.6f;
    float lineSpacing = size * 0.25f;
    
    // Three horizontal lines (playlist/hamburger menu style)
    draw->AddLine(
        ImVec2(center.x - lineWidth * 0.5f, center.y - lineSpacing),
        ImVec2(center.x + lineWidth * 0.5f, center.y - lineSpacing),
        color, 2.0f
    );
    draw->AddLine(
        ImVec2(center.x - lineWidth * 0.5f, center.y),
        ImVec2(center.x + lineWidth * 0.5f, center.y),
        color, 2.0f
    );
    draw->AddLine(
        ImVec2(center.x - lineWidth * 0.5f, center.y + lineSpacing),
        ImVec2(center.x + lineWidth * 0.5f, center.y + lineSpacing),
        color, 2.0f
    );
}

void RenderPlaylistPanel(AppState& state, ImVec2 screenSize) {
    if (!state.showPlaylistPanel) return;
    
    float panelWidth = 400.0f;
    float panelX = screenSize.x - panelWidth;
    
    ImGui::SetNextWindowPos(ImVec2(panelX, 0));
    ImGui::SetNextWindowSize(ImVec2(panelWidth, screenSize.y));
    
    ImGui::PushStyleColor(ImGuiCol_WindowBg, ImVec4(0.08f, 0.08f, 0.08f, 0.98f));
    ImGui::PushStyleVar(ImGuiStyleVar_WindowPadding, ImVec2(0, 0));
    ImGui::PushStyleVar(ImGuiStyleVar_WindowBorderSize, 0.0f);
    
    ImGui::Begin("##Playlist", nullptr, 
        ImGuiWindowFlags_NoDecoration | 
        ImGuiWindowFlags_NoMove | 
        ImGuiWindowFlags_NoResize |
        ImGuiWindowFlags_NoSavedSettings);
    
    ImDrawList* draw = ImGui::GetWindowDrawList();
    
    // Header
    ImGui::SetCursorPos(ImVec2(24, 24));
    ImGui::PushFont(ImGui::GetIO().Fonts->Fonts.Size > 1 ? ImGui::GetIO().Fonts->Fonts[1] : ImGui::GetFont());
    ImGui::Text("Playlist");
    ImGui::PopFont();
    
    // File count
    ImGui::SameLine();
    ImGui::SetCursorPosX(120);
    char countText[32];
    snprintf(countText, sizeof(countText), "(%zu files)", state.playlistFiles.size());
    ImGui::TextColored(ImVec4(0.6f, 0.6f, 0.6f, 1.0f), "%s", countText);
    
    // Close button
    ImGui::SetCursorPos(ImVec2(panelWidth - 50, 20));
    ImGui::PushStyleColor(ImGuiCol_Button, ImVec4(0, 0, 0, 0));
    ImGui::PushStyleColor(ImGuiCol_ButtonHovered, ImVec4(1, 1, 1, 0.1f));
    ImGui::PushStyleColor(ImGuiCol_ButtonActive, ImVec4(1, 1, 1, 0.15f));
    
    if (ImGui::Button("X##ClosePlaylist", ImVec2(32, 32))) {
        state.showPlaylistPanel = false;
    }
    
    ImGui::PopStyleColor(3);
    
    // Separator
    draw->AddLine(
        ImVec2(panelX + 24, 70),
        ImVec2(panelX + panelWidth - 24, 70),
        IM_COL32(80, 80, 80, 255),
        1.0f
    );
    
    // Playlist items
    ImGui::SetCursorPos(ImVec2(0, 90));
    ImGui::BeginChild("##PlaylistItems", ImVec2(panelWidth, screenSize.y - 90), false);
    
    for (size_t i = 0; i < state.playlistFiles.size(); i++) {
        ImGui::PushID((int)i);
        
        bool isPlaying = (state.currentPlaylistIndex >= 0 && i == (size_t)state.currentPlaylistIndex);
        
        // Item background
        ImVec2 itemPos = ImGui::GetCursorScreenPos();
        ImVec2 itemSize = ImVec2(panelWidth, 80);
        
        if (isPlaying) {
            draw->AddRectFilled(itemPos, 
                ImVec2(itemPos.x + itemSize.x, itemPos.y + itemSize.y),
                IM_COL32(229, 9, 20, 30)); // Netflix red tint
        }
        
        // Clickable area
        ImGui::SetCursorPos(ImVec2(0, ImGui::GetCursorPosY()));
        if (ImGui::InvisibleButton("##Item", itemSize)) {
            // Load the selected file
            if (state.decoder) {
                std::string filepath = state.playlistFiles[i];
                if (state.decoder->open(filepath)) {
                    state.currentPlaylistIndex = (int)i;
                    state.fileLoaded = true;
                    state.duration = (float)state.decoder->getDuration();
                    state.currentTime = 0.0f;
                    state.currentTitle = state.playlistNames[i];
                    state.currentFile = state.currentTitle;
                    
                    // Reset A/V sync state
                    state.lastVideoFramePTS = 0.0;
                    state.videoStartTime = 0.0;
                    state.droppedFrames = 0;
                    state.displayedFrames = 0;
                    if (state.pendingFrame) {
                        delete state.pendingFrame;
                        state.pendingFrame = nullptr;
                    }
                    
                    // Initialize audio if available
                    if (state.decoder->hasAudio() && state.audioOutput) {
                        state.audioOutput->clearQueue();
                        state.audioOutput->setAudioClock(0.0);
                    }
                    
                    // Auto-start playback
                    state.isPlaying = true;
                    state.decoder->play();
                    if (state.audioOutput) {
                        state.audioOutput->play();
                    }
                    
                    state.timeSinceFileLoad = 0.0f;
                }
            }
        }
        
        bool hovered = ImGui::IsItemHovered();
        if (hovered && !isPlaying) {
            draw->AddRectFilled(itemPos,
                ImVec2(itemPos.x + itemSize.x, itemPos.y + itemSize.y),
                IM_COL32(255, 255, 255, 15));
        }
        
        // File name
        ImGui::SetCursorPos(ImVec2(24, itemPos.y - ImGui::GetWindowPos().y + 25));
        
        if (isPlaying) {
            ImGui::PushStyleColor(ImGuiCol_Text, ImVec4(0.898f, 0.035f, 0.078f, 1.0f));
        }
        
        ImGui::Text("%s", state.playlistNames[i].c_str());
        
        if (isPlaying) {
            ImGui::PopStyleColor();
        }
        
        // Now playing indicator
        if (isPlaying) {
            ImGui::SetCursorPos(ImVec2(panelWidth - 120, itemPos.y - ImGui::GetWindowPos().y + 30));
            ImGui::TextColored(ImVec4(0.898f, 0.035f, 0.078f, 1.0f), "Now Playing");
        }
        
        ImGui::PopID();
        
        // Separator
        if (i < state.playlistFiles.size() - 1) {
            ImVec2 sepStart = ImVec2(itemPos.x + 24, itemPos.y + itemSize.y);
            draw->AddLine(sepStart,
                ImVec2(sepStart.x + panelWidth - 48, sepStart.y),
                IM_COL32(50, 50, 50, 255), 1.0f);
        }
    }
    
    ImGui::EndChild();
    ImGui::End();
    
    ImGui::PopStyleVar(2);
    ImGui::PopStyleColor();
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
            if (ImGui::MenuItem("Open File...", "Cmd+O")) {
                std::string filepath = openFileDialog();
                if (!filepath.empty()) {
                    // Initialize decoder if needed
                    if (!state.decoder) {
                        state.decoder = new VideoDecoder();
                    }
                    if (!state.audioOutput) {
                        state.audioOutput = new AudioOutput();
                    }
                    
                    // Open file
                    if (state.decoder->open(filepath)) {
                        state.fileLoaded = true;
                        state.duration = (float)state.decoder->getDuration();
                        state.currentTime = 0.0f;
                        
                        // Extract filename for title
                        size_t lastSlash = filepath.find_last_of("/\\");
                        state.currentTitle = (lastSlash != std::string::npos) 
                            ? filepath.substr(lastSlash + 1) 
                            : filepath;
                        state.currentFile = state.currentTitle;
                        
                        // Scan directory for playlist
                        ScanDirectoryForMediaFiles(state, filepath);
                        
                        // CRITICAL: Clear any stale pending frame
                        if (state.pendingFrame) {
                            delete state.pendingFrame;
                            state.pendingFrame = nullptr;
                        }
                        
                        // Initialize audio if available
                        if (state.decoder->hasAudio()) {
                            state.audioOutput->initialize(
                                state.decoder->getSampleRate(),
                                state.decoder->getChannels()
                            );
                        }
                        
                        // Auto-start playback
                        state.isPlaying = true;
                        state.showControls = true;  // Show controls on start
                        state.showMenuBar = true;   // Show menu bar too
                        state.controlsTimer = 5.0f; // Give 5 seconds before auto-hide
                        state.timeSinceFileLoad = 0.0f;  // Reset file load timer
                        
                        // Reset A/V sync state
                        state.lastVideoFramePTS = 0.0;
                        state.videoStartTime = 0.0;
                        state.droppedFrames = 0;
                        state.displayedFrames = 0;
                        if (state.pendingFrame) {
                            delete state.pendingFrame;
                            state.pendingFrame = nullptr;
                        }
                        
                        state.decoder->play();
                        if (state.audioOutput) {
                            state.audioOutput->play();
                        }
                        
                        std::cout << "Loaded: " << state.currentTitle << std::endl;
                    }
                }
            }
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
    
    // Get window draw list for controls (drawn on top of video)
    ImDrawList* controlDrawList = ImGui::GetWindowDrawList();
    
    // Video surface (black background with gradient)
    drawList->AddRectFilled(ImVec2(0, 0), screenSize, IM_COL32(0, 0, 0, 255));
    
    // Render video texture if available
    if (state.videoTexture) {
        // Calculate aspect ratio letterboxing
        float videoAspect = (float)state.videoTexture.width / (float)state.videoTexture.height;
        float screenAspect = screenSize.x / screenSize.y;
        
        ImVec2 videoPos, videoSize;
        
        if (videoAspect > screenAspect) {
            // Video is wider - fit to width
            videoSize.x = screenSize.x;
            videoSize.y = screenSize.x / videoAspect;
            videoPos.x = 0;
            videoPos.y = (screenSize.y - videoSize.y) * 0.5f;
        } else {
            // Video is taller - fit to height
            videoSize.y = screenSize.y;
            videoSize.x = screenSize.y * videoAspect;
            videoPos.x = (screenSize.x - videoSize.x) * 0.5f;
            videoPos.y = 0;
        }
        
        // Draw video texture
        ImGui::SetCursorPos(videoPos);
        ImGui::Image((ImTextureID)(void*)state.videoTexture, videoSize);
    } else {
        // Mock video content (subtle gradient) - shown when no file loaded
        ImU32 gradientTop = IM_COL32(15, 15, 20, 255);
        ImU32 gradientBottom = IM_COL32(8, 8, 12, 255);
        DrawGradientOverlay(drawList, ImVec2(0, 0), screenSize, gradientTop, gradientBottom);
        
        // Centered branding
        const char* brandText = "SIMPLE MEDIA PLAYER V2";
        const char* subText = state.fileLoaded ? "Loading video..." : "Open a file to start playing";
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
    }
    
    // Click on video area (not controls) to play/pause
    // Controls are in bottom 150px, so make clickable area exclude that
    ImVec2 clickableSize = ImVec2(screenSize.x, screenSize.y - 150);
    ImGui::SetCursorPos(ImVec2(0, 0));
    ImGui::InvisibleButton("##VideoSurface", clickableSize);
    if (ImGui::IsItemClicked(0)) {
        state.isPlaying = !state.isPlaying;
        state.showControls = true;
        state.controlsTimer = 3.0f;
        
        // Control decoder and audio
        if (state.decoder) {
            if (state.isPlaying) {
                state.decoder->play();
                if (state.audioOutput) {
                    state.audioOutput->play();
                }
            } else {
                state.decoder->pause();
                if (state.audioOutput) {
                    state.audioOutput->pause();
                }
            }
        }
    }
    
    // Detect mouse movement
    static ImVec2 lastMousePos = io.MousePos;
    if (io.MousePos.x != lastMousePos.x || io.MousePos.y != lastMousePos.y) {
        state.showControls = true;
        state.showMenuBar = true;
        state.controlsTimer = 3.0f;
        lastMousePos = io.MousePos;
    }
    
    // Track time since file loaded
    if (state.fileLoaded) {
        state.timeSinceFileLoad += io.DeltaTime;
    }
    
    // Only auto-hide controls in fullscreen mode
    if (state.isFullscreen) {
        // Check if mouse is in control area (bottom 150px)
        bool mouseInControlArea = io.MousePos.y > (screenSize.y - 150);
        
        // Don't auto-hide for first 5 seconds after file loads
        bool allowAutoHide = state.timeSinceFileLoad > 5.0f;
        
        // Auto-hide controls only if:
        // - Fullscreen
        // - Playing
        // - Mouse not in control area
        // - At least 5 seconds since file loaded
        if (state.isPlaying && state.showControls && !mouseInControlArea && allowAutoHide) {
            state.controlsTimer -= io.DeltaTime;
            if (state.controlsTimer <= 0.0f) {
                state.showControls = false;
                state.showMenuBar = false;
            }
        }
        
        // If mouse in control area during playback, keep controls visible and reset timer
        if (mouseInControlArea && state.isPlaying) {
            state.showControls = true;
            state.showMenuBar = true;
            state.controlsTimer = 3.0f;
        }
    } else {
        // In windowed mode, always keep controls visible
        state.showControls = true;
    }
    
    // Update playback state from decoder
    if (state.decoder && state.fileLoaded) {
        if (!state.decoder->isPlaying() && state.isPlaying) {
            // Decoder stopped (end of file)
            state.isPlaying = false;
            if (state.audioOutput) {
                state.audioOutput->pause();
            }
        }
        
        // Note: currentTime is updated from frame PTS in the video processing loop
        // Don't update it here to avoid conflicts
    }
    
    // Controls overlay
    if (state.showControls) {
        // Smooth fade out animation (ease-out cubic)
        float alpha = 1.0f;
        if (state.controlsTimer < 0.5f && state.controlsTimer > 0.0f) {
            float t = state.controlsTimer / 0.5f;  // 0 to 1
            // Ease-out cubic: 1 - (1-t)^3
            alpha = 1.0f - powf(1.0f - t, 3.0f);
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
        DrawGradientOverlay(controlDrawList, 
            ImVec2(0, gradientStart.y), 
            ImVec2(screenSize.x, gradientStart.y + segmentHeight),
            gradTop, IM_COL32(0, 0, 0, 50));
        DrawGradientOverlay(controlDrawList,
            ImVec2(0, gradientStart.y + segmentHeight),
            ImVec2(screenSize.x, gradientStart.y + segmentHeight * 2),
            IM_COL32(0, 0, 0, 50), gradMid);
        DrawGradientOverlay(controlDrawList,
            ImVec2(0, gradientStart.y + segmentHeight * 2),
            screenSize,
            gradMid, gradBot);
        
        // Title (top of controls area)
        float titleY = screenSize.y - 260;
        controlDrawList->AddText(ImGui::GetFont(), 28.0f,
            ImVec2(50, titleY),
            IM_COL32(255, 255, 255, (int)(255 * alpha)),
            state.currentTitle.c_str()
        );
        
        // Progress bar (80px from bottom, 50px from sides)
        float progressY = screenSize.y - 80;
        float progressWidth = screenSize.x - 100;
        
        ImGui::SetCursorPos(ImVec2(50, progressY));
        // Make the ImGui slider invisible - we'll draw our own custom appearance
        ImGui::PushStyleColor(ImGuiCol_FrameBg, ImVec4(0.0f, 0.0f, 0.0f, 0.0f)); // Transparent background
        ImGui::PushStyleColor(ImGuiCol_FrameBgHovered, ImVec4(0.0f, 0.0f, 0.0f, 0.0f)); // Transparent on hover
        ImGui::PushStyleColor(ImGuiCol_FrameBgActive, ImVec4(0.0f, 0.0f, 0.0f, 0.0f)); // Transparent when active
        ImGui::PushStyleColor(ImGuiCol_SliderGrab, ImVec4(0.0f, 0.0f, 0.0f, 0.0f)); // Invisible grab
        ImGui::PushStyleColor(ImGuiCol_SliderGrabActive, ImVec4(0.0f, 0.0f, 0.0f, 0.0f)); // Invisible grab when active
        ImGui::PushStyleVar(ImGuiStyleVar_GrabMinSize, 16.0f);
        
        ImGui::PushItemWidth(progressWidth);
        bool progressHovered = false;
        if (ImGui::SliderFloat("##Progress", &state.currentTime, 0.0f, state.duration, "")) {
            // Seeking - decode frames until we reach exact position
            if (state.decoder) {
                // CRITICAL: Clear pending frame BEFORE seek to prevent stale data
                if (state.pendingFrame) {
                    delete state.pendingFrame;
                    state.pendingFrame = nullptr;
                }
                
                state.decoder->seek(state.currentTime);
                
                // Reset audio clock to match seek position
                if (state.audioOutput) {
                    state.audioOutput->clearQueue();
                    state.audioOutput->setAudioClock(state.currentTime);
                }
                // Reset video timing
                state.lastVideoFramePTS = state.currentTime;
            }
        }
        progressHovered = ImGui::IsItemHovered();
        
        // Change cursor to hand when hovering over progress bar
        if (progressHovered) {
            ImGui::SetMouseCursor(ImGuiMouseCursor_Hand);
        }
        
        ImGui::PopItemWidth();
        
        // Draw custom progress bar appearance
        ImVec2 progressBarMin = ImVec2(50, progressY);
        ImVec2 progressBarMax = ImVec2(50 + progressWidth, progressY + 6);
        float progress = state.currentTime / state.duration;
        
        // Background track
        controlDrawList->AddRectFilled(progressBarMin, progressBarMax, 
            IM_COL32(70, 70, 70, (int)(200 * alpha)), 2.0f);
        
        // Progress fill (Netflix red)
        controlDrawList->AddRectFilled(progressBarMin, 
            ImVec2(progressBarMin.x + progressWidth * progress, progressBarMax.y),
            IM_COL32(229, 9, 20, (int)(255 * alpha)), 2.0f);
        
        // Scrubber circle
        if (progressHovered) {
            ImVec2 scrubberPos = ImVec2(progressBarMin.x + progressWidth * progress, progressY + 3);
            controlDrawList->AddCircleFilled(scrubberPos, 8.0f, 
                IM_COL32(229, 9, 20, (int)(255 * alpha)), 16);
        }
        
        ImGui::PopStyleVar();
        ImGui::PopStyleColor(5); // Pop 5 colors now (was 3)
        
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
            
            // Control decoder and audio
            if (state.decoder) {
                if (state.isPlaying) {
                    state.decoder->play();
                    if (state.audioOutput) {
                        state.audioOutput->play();
                    }
                } else {
                    state.decoder->pause();
                    if (state.audioOutput) {
                        state.audioOutput->pause();
                    }
                }
            }
        }
        ImVec2 playIconCenter = ImVec2(playButtonPos.x + 24, playButtonPos.y + 24);
        if (state.isPlaying) {
            DrawPauseIcon(controlDrawList, playIconCenter, 24.0f, IM_COL32(255, 255, 255, (int)(255 * alpha)));
        } else {
            DrawPlayIcon(controlDrawList, playIconCenter, 24.0f, IM_COL32(255, 255, 255, (int)(255 * alpha)));
        }
        
        ImGui::SameLine(0, 8);
        
        // Skip backward button (40x40)
        ImVec2 skipBackPos = ImGui::GetCursorScreenPos();
        if (ImGui::Button("##SkipBack", ImVec2(40, 40))) {
            state.currentTime = fmaxf(state.currentTime - 10.0f, 0.0f);
            
            // Trigger skip animation
            state.showSkipAnimation = true;
            state.skipAnimationTimer = 0.8f;  // Show for 0.8 seconds
            state.skipAnimationDirection = -1;  // Backward
            
            // CRITICAL: Clear pending frame BEFORE seek
            if (state.pendingFrame) {
                delete state.pendingFrame;
                state.pendingFrame = nullptr;
            }
            
            if (state.decoder) {
                state.decoder->seek(state.currentTime);
                // Reset audio clock to match seek position
                if (state.audioOutput) {
                    state.audioOutput->clearQueue();
                    state.audioOutput->setAudioClock(state.currentTime);
                }
                // Reset video timing
                state.lastVideoFramePTS = state.currentTime;
            }
        }
        DrawSkipIcon(controlDrawList, ImVec2(skipBackPos.x + 20, skipBackPos.y + 20), 16.0f, false,
            IM_COL32(255, 255, 255, (int)(255 * alpha)));
        
        ImGui::SameLine(0, 8);
        
        // Skip forward button (40x40)
        ImVec2 skipForwardPos = ImGui::GetCursorScreenPos();
        if (ImGui::Button("##SkipForward", ImVec2(40, 40))) {
            state.currentTime = fminf(state.currentTime + 10.0f, state.duration);
            
            // Trigger skip animation
            state.showSkipAnimation = true;
            state.skipAnimationTimer = 0.8f;  // Show for 0.8 seconds
            state.skipAnimationDirection = 1;  // Forward
            
            // CRITICAL: Clear pending frame BEFORE seek
            if (state.pendingFrame) {
                delete state.pendingFrame;
                state.pendingFrame = nullptr;
            }
            
            if (state.decoder) {
                state.decoder->seek(state.currentTime);
                // Reset audio clock to match seek position
                if (state.audioOutput) {
                    state.audioOutput->clearQueue();
                    state.audioOutput->setAudioClock(state.currentTime);
                }
                // Reset video timing
                state.lastVideoFramePTS = state.currentTime;
            }
        }
        DrawSkipIcon(controlDrawList, ImVec2(skipForwardPos.x + 20, skipForwardPos.y + 20), 16.0f, true,
            IM_COL32(255, 255, 255, (int)(255 * alpha)));
        
        ImGui::SameLine(0, 16);
        
        // Volume icon and slider
        ImVec2 volumeIconPos = ImGui::GetCursorScreenPos();
        if (ImGui::Button("##VolumeIcon", ImVec2(32, 32))) {
            state.isMuted = !state.isMuted;
            if (state.audioOutput) {
                state.audioOutput->setVolume(state.isMuted ? 0.0f : state.volume);
            }
        }
        DrawVolumeIcon(controlDrawList, ImVec2(volumeIconPos.x + 6, volumeIconPos.y + 6), 
            state.volume, state.isMuted, IM_COL32(255, 255, 255, (int)(255 * alpha)));
        
        ImGui::SameLine(0, 8);
        
        // Volume slider
        ImGui::SetCursorPosY(controlsY - 16);
        ImGui::PushItemWidth(100);
        if (ImGui::SliderFloat("##Volume", &state.volume, 0.0f, 1.0f, "")) {
            if (state.audioOutput) {
                state.audioOutput->setVolume(state.volume);
            }
        }
        ImGui::PopItemWidth();
        
        ImGui::SameLine(0, 24);
        
        // Time display
        std::string timeStr = FormatTime(state.currentTime) + " / " + FormatTime(state.duration);
        controlDrawList->AddText(ImVec2(ImGui::GetCursorScreenPos().x, controlsY - 8),
            IM_COL32(255, 255, 255, (int)(230 * alpha)), timeStr.c_str());
        
        // Right-side controls
        float rightControlsX = screenSize.x - 250;
        ImGui::SetCursorPos(ImVec2(rightControlsX, controlsY - 16));
        
        // Playlist/Episodes button (disabled when no file loaded)
        ImVec2 playlistPos = ImGui::GetCursorScreenPos();
        bool playlistEnabled = state.fileLoaded && !state.playlistFiles.empty();
        if (!playlistEnabled) {
            ImGui::PushStyleVar(ImGuiStyleVar_Alpha, alpha * 0.3f);  // Dim when disabled
        }
        if (ImGui::Button("##Playlist", ImVec2(32, 32)) && playlistEnabled) {
            state.showPlaylistPanel = !state.showPlaylistPanel;
        }
        DrawPlaylistIcon(controlDrawList, ImVec2(playlistPos.x + 16, playlistPos.y + 16), 18.0f,
            IM_COL32(255, 255, 255, (int)(255 * alpha * (playlistEnabled ? 1.0f : 0.3f))));
        if (!playlistEnabled) {
            ImGui::PopStyleVar();
        }
        
        ImGui::SameLine(0, 8);
        
        // Settings button
        ImVec2 settingsPos = ImGui::GetCursorScreenPos();
        if (ImGui::Button("##Settings", ImVec2(32, 32))) {
            // TODO: Open settings
        }
        DrawSettingsIcon(controlDrawList, ImVec2(settingsPos.x + 16, settingsPos.y + 16), 20.0f,
            IM_COL32(255, 255, 255, (int)(255 * alpha)));
        
        ImGui::SameLine(0, 8);
        
        // Audio button
        ImVec2 audioPos = ImGui::GetCursorScreenPos();
        if (ImGui::Button("##Audio", ImVec2(32, 32))) {
            state.showAudioMenu = !state.showAudioMenu;
        }
        DrawAudioIcon(controlDrawList, ImVec2(audioPos.x + 16, audioPos.y + 16), 20.0f,
            IM_COL32(255, 255, 255, (int)(255 * alpha)));
        
        ImGui::SameLine(0, 8);
        
        // Subtitles button
        ImVec2 subtitlesPos = ImGui::GetCursorScreenPos();
        if (ImGui::Button("##Subtitles", ImVec2(32, 32))) {
            state.showSubtitleMenu = !state.showSubtitleMenu;
        }
        DrawSubtitlesIcon(controlDrawList, ImVec2(subtitlesPos.x + 16, subtitlesPos.y + 16), 20.0f,
            IM_COL32(255, 255, 255, (int)(255 * alpha)));
        
        ImGui::SameLine(0, 8);
        
        // Fullscreen button
        ImVec2 fullscreenPos = ImGui::GetCursorScreenPos();
        if (ImGui::Button("##Fullscreen", ImVec2(32, 32))) {
            // TODO: Toggle fullscreen
        }
        DrawFullscreenIcon(controlDrawList, ImVec2(fullscreenPos.x + 16, fullscreenPos.y + 16), 18.0f,
            IM_COL32(255, 255, 255, (int)(255 * alpha)));
        
        ImGui::PopStyleColor(3);
        
        ImGui::PopStyleVar(); // Alpha
    }
    
    // Skip animation (±10 seconds overlay)
    if (state.showSkipAnimation) {
        state.skipAnimationTimer -= io.DeltaTime;
        if (state.skipAnimationTimer <= 0.0f) {
            state.showSkipAnimation = false;
        } else {
            // Animation parameters
            float animAlpha = fminf(state.skipAnimationTimer / 0.8f, 1.0f);  // Fade out
            float circleRadius = 60.0f;
            ImVec2 center = ImVec2(screenSize.x * 0.5f, screenSize.y * 0.5f);
            
            // Use window draw list for overlay (safe to use here)
            ImDrawList* animDrawList = ImGui::GetWindowDrawList();
            
            // Semi-transparent circle background
            animDrawList->AddCircleFilled(center, circleRadius, 
                IM_COL32(0, 0, 0, (int)(180 * animAlpha)), 32);
            
            // Circle outline
            animDrawList->AddCircle(center, circleRadius, 
                IM_COL32(255, 255, 255, (int)(200 * animAlpha)), 32, 3.0f);
            
            // Skip icon
            float iconSize = 24.0f;
            DrawSkipIcon(animDrawList, center, iconSize, 
                state.skipAnimationDirection > 0,
                IM_COL32(255, 255, 255, (int)(255 * animAlpha)));
            
            // "+10" or "-10" text below icon
            const char* skipText = state.skipAnimationDirection > 0 ? "+10" : "-10";
            ImVec2 textSize = ImGui::CalcTextSize(skipText);
            ImVec2 textPos = ImVec2(center.x - textSize.x * 0.5f, center.y + 15);
            animDrawList->AddText(ImGui::GetFont(), 18.0f, textPos,
                IM_COL32(255, 255, 255, (int)(255 * animAlpha)), skipText);
        }
    }
    
    ImGui::End();
}

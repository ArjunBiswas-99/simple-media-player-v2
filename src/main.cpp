//
// Simple Media Player V2 - Netflix-Inspired Media Player
// Main Entry Point
//

#ifdef _WIN32
#define NOMINMAX  // Prevent Windows.h from defining min/max macros
#endif

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
#include "platform.h"

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
    int skipAnimationSeconds = 5;    // How many seconds to show (5s for arrow keys)
    
    // Netflix-style accumulating seek animation
    double lastSkipBackTime = 0.0;
    double lastSkipForwardTime = 0.0;
    int accumulatedSkipBackSeconds = 0;
    int accumulatedSkipForwardSeconds = 0;
    float skipBackAnimTimer = 0.0f;
    float skipForwardAnimTimer = 0.0f;
    bool showSkipBackAccumulation = false;
    bool showSkipForwardAccumulation = false;
    ImVec2 skipBackButtonPos = ImVec2(0, 0);  // Position of skip back button for animation
    ImVec2 skipForwardButtonPos = ImVec2(0, 0);  // Position of skip forward button for animation
    float controlButtonSize = 48.0f;  // Size of control buttons
    
    // Pause overlay state (Netflix-style large icons)
    float pauseOverlayTimer = 3.0f;  // Fade after 3 seconds of pause
    
    // 2x speed mode (click and hold)
    bool is2xSpeedMode = false;
    bool show2xSpeedIndicator = false;
    float normalPlaybackSpeed = 1.0f;  // Store original speed
    
    // Subtitle/audio selection
    bool showSubtitleMenu = false;
    bool showAudioMenu = false;
    
    // Hover states for animations
    bool playButtonHovered = false;
    bool skipBackHovered = false;
    bool skipForwardHovered = false;
    bool volumeHovered = false;
    bool playlistHovered = false;
    bool settingsHovered = false;
    bool audioButtonHovered = false;
    bool subtitlesHovered = false;
    bool fullscreenHovered = false;
    
    // Hover animation timers (0.0 to 1.0)
    float playButtonHoverAnim = 0.0f;
    float skipBackHoverAnim = 0.0f;
    float skipForwardHoverAnim = 0.0f;
    float volumeHoverAnim = 0.0f;
    float playlistHoverAnim = 0.0f;
    float settingsHoverAnim = 0.0f;
    float audioButtonHoverAnim = 0.0f;
    float subtitlesHoverAnim = 0.0f;
    float fullscreenHoverAnim = 0.0f;
    
    // Tooltip state
    float tooltipHoverTime = 0.0f;
    const char* tooltipText = nullptr;
    ImVec2 tooltipPos = ImVec2(0, 0);
    
    // Video playback
    VideoDecoder* decoder = nullptr;
    AudioOutput* audioOutput = nullptr;
    PlatformTexture videoTexture = nullptr;
    int videoTextureWidth = 0;
    int videoTextureHeight = 0;
    bool fileLoaded = false;
    bool ignoreNextClick = false;  // Skip next click event (e.g., after file dialog)
    
    // A/V sync state
    VideoFrame* pendingFrame = nullptr;  // Frame waiting to be displayed
    double lastVideoFramePTS = 0.0;      // PTS of last displayed frame
    double videoStartTime = 0.0;         // System time when video started
    int droppedFrames = 0;               // Count of dropped frames
    int displayedFrames = 0;             // Count of displayed frames
    bool justSeeked = false;             // Flag to ignore old frame timestamps after seek
};

// Forward declarations
void SetupNetflixTheme();
void RenderMenuBar(AppState& state);
void RenderNetflixUI(AppState& state, PlatformWindow window);
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
    // At higher playback speeds, process multiple frames per UI loop
    if (state.fileLoaded && state.decoder && state.decoder->hasVideo() && state.isPlaying) {
        // Determine how many frames to process this loop
        // At 2x speed, try to process 2 frames; at 1x speed, process 1 frame
        int maxFramesToProcess = std::max(1, (int)(state.playbackSpeed * 1.5));
        int framesProcessed = 0;
        
        // Loop to process multiple frames when speed > 1
        for (int frameLoop = 0; frameLoop < maxFramesToProcess && state.isPlaying; frameLoop++) {
            // Get audio clock for synchronization
            double audioClock = 0.0;
            bool useAudioSync = false;
            
            if (state.audioOutput && state.decoder->hasAudio()) {
                audioClock = state.audioOutput->getAudioClock();
                // Only use audio sync if audio has actually started (clock > 0.1s)
                // This allows initial frames to display before audio callback starts
                useAudioSync = (audioClock > 0.1);
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
                    break;  // Exit loop if no more frames
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
                    
                    // Adjust thresholds based on playback speed
                    // At 2x speed, frames arrive faster so we need tighter sync
                    const double speedMultiplier = state.playbackSpeed;
                    const double SYNC_THRESHOLD = 0.040 / speedMultiplier;  // Tighter at higher speeds
                    const double DROP_THRESHOLD = 0.100 / speedMultiplier;
                    const double NOSYNC_THRESHOLD = 0.5;  // Keep this absolute
                    
                    static int logCounter = 0;
                    if (logCounter++ % 30 == 0) {  // Log every 30 frames
                        std::cout << "[VIDEO SYNC] speedMultiplier=" << speedMultiplier 
                                  << " videoPTS=" << videoPTS 
                                  << " audioClock=" << audioClock 
                                  << " drift=" << drift << std::endl;
                    }
                    
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
                        continue;  // Try next frame
                    }
                    // Video is slightly ahead - wait a bit
                    else if (drift > SYNC_THRESHOLD) {
                        // At normal speed, don't display yet
                        // At high speed, be more aggressive and display anyway
                        if (state.playbackSpeed > 1.5) {
                            shouldDisplay = true;
                        } else {
                            shouldDisplay = false;
                            break;  // Stop processing, wait for audio to catch up
                        }
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
                    framesProcessed++;
                    
                    // Update tracking
                    state.lastVideoFramePTS = videoPTS;
                    
                    // Only update currentTime from frame if we haven't just seeked
                    if (!state.justSeeked) {
                        state.currentTime = (float)videoPTS;
                    } else if (videoPTS >= state.currentTime - 0.5) {
                        // We've reached frames near/past our seek target, resume normal sync
                        state.currentTime = (float)videoPTS;
                        state.justSeeked = false;
                    }
                    
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
                            state.videoTextureWidth != frame->width || 
                            state.videoTextureHeight != frame->height) {
                            
                            // Destroy old texture if exists
                            if (state.videoTexture) {
                                DestroyVideoTexture(state.videoTexture);
                            }
                            
                            // Create new texture
                            state.videoTexture = CreateVideoTexture(frame->width, frame->height);
                            state.videoTextureWidth = frame->width;
                            state.videoTextureHeight = frame->height;
                            
                            if (!state.videoTexture) {
                                std::cerr << "Failed to create video texture" << std::endl;
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
                                
                                // Upload to texture
                                UpdateVideoTexture(state.videoTexture, rgbaData, frame->width, frame->height);
                                
                                free(rgbaData);
                            }
                        }
                        
                        // Always delete the frame after use
                        if (frame) {
                            delete frame;
                        }
                    }
                } else if (!shouldDisplay) {
                    // Frame not ready to display yet, keep it pending
                    break;  // Exit loop and try again next UI frame
                }
            } else if (state.pendingFrame && (!state.pendingFrame->data || state.pendingFrame->width <= 0 || state.pendingFrame->height <= 0)) {
                // Pending frame is invalid, discard it
                delete state.pendingFrame;
                state.pendingFrame = nullptr;
            }
        }  // End of frame processing loop
        
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
#ifdef __APPLE__
    RenderNetflixUI(state, view.window);
#else
    RenderNetflixUI(state);
#endif
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
void LoadMediaFile(AppState& state, const std::string& filepath, PlatformWindow window);
LRESULT WINAPI WndProc(HWND hWnd, UINT msg, WPARAM wParam, LPARAM lParam);

// Windows entry point
int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow) {
    // Allocate console for debug output
    AllocConsole();
    FILE* fDummy;
    freopen_s(&fDummy, "CONOUT$", "w", stdout);
    freopen_s(&fDummy, "CONOUT$", "w", stderr);
    freopen_s(&fDummy, "CONIN$", "r", stdin);
    std::cout.clear();
    std::cerr.clear();
    std::cin.clear();
    
    std::cout << "=== Simple Media Player V2 - Debug Console ===" << std::endl;
    std::cout << "Windows build with Direct3D11 and WASAPI" << std::endl;
    std::cout << "===============================================" << std::endl;
    
    // Parse command line to get initial file (if provided)
    std::string initialFile;
    if (lpCmdLine && strlen(lpCmdLine) > 0) {
        // Remove quotes if present
        std::string cmdLine(lpCmdLine);
        if (!cmdLine.empty() && cmdLine.front() == '"' && cmdLine.back() == '"') {
            cmdLine = cmdLine.substr(1, cmdLine.length() - 2);
        }
        initialFile = cmdLine;
        std::cout << "Command line file: " << initialFile << std::endl;
    }
    
    // Alternative: parse using GetCommandLineW for better Unicode support
    if (initialFile.empty()) {
        int nArgs;
        LPWSTR* szArglist = CommandLineToArgvW(GetCommandLineW(), &nArgs);
        if (szArglist != nullptr && nArgs > 1) {
            // Convert wide string to narrow string
            int size = WideCharToMultiByte(CP_UTF8, 0, szArglist[1], -1, nullptr, 0, nullptr, nullptr);
            if (size > 0) {
                initialFile.resize(size - 1);
                WideCharToMultiByte(CP_UTF8, 0, szArglist[1], -1, &initialFile[0], size, nullptr, nullptr);
                std::cout << "Command line file (Unicode): " << initialFile << std::endl;
            }
            LocalFree(szArglist);
        }
    }
    
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

    // Set the D3D device for platform-specific texture functions
    SetD3D11Device(g_pd3dDevice, g_pd3dDeviceContext, g_pSwapChain, g_mainRenderTargetView);

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
    
    // Load initial file if provided via command line
    if (!initialFile.empty()) {
        std::cout << "Loading file from command line: " << initialFile << std::endl;
        LoadMediaFile(state, initialFile, hwnd);
    }

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

        // Process video frames with A/V synchronization (Windows)
        if (state.fileLoaded && state.decoder && state.decoder->hasVideo() && state.isPlaying) {
            // Get audio clock for synchronization
            double audioClock = 0.0;
            bool useAudioSync = false;
            
            if (state.audioOutput && state.decoder->hasAudio()) {
                audioClock = state.audioOutput->getAudioClock();
                useAudioSync = (audioClock > 0.1);
            }
            
            // Fetch new frame if we don't have a pending one
            if (!state.pendingFrame) {
                state.pendingFrame = state.decoder->getNextVideoFrame();
                
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
            if (state.pendingFrame && state.pendingFrame->data) {
                double videoPTS = state.pendingFrame->pts;
                double drift = 0.0;
                bool shouldDisplay = false;
                
                if (useAudioSync) {
                    drift = videoPTS - audioClock;
                    const double SYNC_THRESHOLD = 0.040;
                    const double DROP_THRESHOLD = 0.100;
                    
                    static int logCounter = 0;
                    if (logCounter++ % 30 == 0) {
                        std::cout << "[VIDEO SYNC] videoPTS=" << videoPTS 
                                  << " audioClock=" << audioClock 
                                  << " drift=" << drift << std::endl;
                    }
                    
                    if (drift < -DROP_THRESHOLD) {
                        // Drop frame
                        delete state.pendingFrame;
                        state.pendingFrame = nullptr;
                    } else if (drift < -SYNC_THRESHOLD) {
                        shouldDisplay = true;
                    } else if (drift > SYNC_THRESHOLD) {
                        // Video ahead - wait (keep frame pending)
                        shouldDisplay = false;
                    } else {
                        shouldDisplay = true;
                    }
                } else {
                    // No audio sync - just display
                    shouldDisplay = true;
                }
                
                if (shouldDisplay && state.pendingFrame) {
                    // Create or update texture
                    if (!state.videoTexture || 
                        state.videoTextureWidth != state.pendingFrame->width || 
                        state.videoTextureHeight != state.pendingFrame->height) {
                        
                        if (state.videoTexture) {
                            DestroyVideoTexture(state.videoTexture);
                        }
                        
                        state.videoTexture = CreateVideoTexture(state.pendingFrame->width, state.pendingFrame->height);
                        state.videoTextureWidth = state.pendingFrame->width;
                        state.videoTextureHeight = state.pendingFrame->height;
                        std::cout << "Created D3D11 texture: " << state.videoTextureWidth << "x" << state.videoTextureHeight << std::endl;
                    }
                    
                    // Update texture with frame data
                    if (state.videoTexture) {
                        UpdateVideoTexture(state.videoTexture, state.pendingFrame->data, 
                                         state.pendingFrame->width, state.pendingFrame->height);
                    }
                    
                    // Update time
                    state.currentTime = (float)videoPTS;
                    
                    // Release frame
                    delete state.pendingFrame;
                    state.pendingFrame = nullptr;
                }
            }
        }

        // Start ImGui frame
        ImGui_ImplDX11_NewFrame();
        ImGui_ImplWin32_NewFrame();
        ImGui::NewFrame();

        // Render UI
        RenderMenuBar(state);
        RenderNetflixUI(state, hwnd);
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

// Helper function to load a media file
void LoadMediaFile(AppState& state, const std::string& filepath, PlatformWindow window) {
    std::cout << "[LoadMediaFile] Starting to load: " << filepath << std::endl;
    
    // Initialize decoder if needed
    if (!state.decoder) {
        std::cout << "[LoadMediaFile] Creating VideoDecoder" << std::endl;
        state.decoder = new VideoDecoder();
    }
    if (!state.audioOutput) {
        std::cout << "[LoadMediaFile] Creating AudioOutput" << std::endl;
        state.audioOutput = new AudioOutput();
    }
    
    // Open file
    std::cout << "[LoadMediaFile] Calling decoder->open()" << std::endl;
    if (state.decoder->open(filepath)) {
        std::cout << "[LoadMediaFile] File opened successfully!" << std::endl;
        state.fileLoaded = true;
        state.duration = (float)state.decoder->getDuration();
        state.currentTime = 0.0f;
        std::cout << "[LoadMediaFile] Duration: " << state.duration << " seconds" << std::endl;
        
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
            std::cout << "[LoadMediaFile] Has audio - initializing AudioOutput" << std::endl;
            std::cout << "[LoadMediaFile] Sample rate: " << state.decoder->getSampleRate() << " Hz" << std::endl;
            std::cout << "[LoadMediaFile] Channels: " << state.decoder->getChannels() << std::endl;
            bool audioInit = state.audioOutput->initialize(
                state.decoder->getSampleRate(),
                state.decoder->getChannels()
            );
            std::cout << "[LoadMediaFile] Audio initialized: " << (audioInit ? "SUCCESS" : "FAILED") << std::endl;
        } else {
            std::cout << "[LoadMediaFile] No audio stream found" << std::endl;
        }
        
        // Auto-start playback
        state.isPlaying = true;
        state.showControls = true;
        state.showMenuBar = true;
        state.controlsTimer = 5.0f;
        state.timeSinceFileLoad = 0.0f;
        
        // Reset A/V sync state
        state.lastVideoFramePTS = 0.0;
        state.videoStartTime = 0.0;
        state.droppedFrames = 0;
        state.displayedFrames = 0;
        if (state.pendingFrame) {
            delete state.pendingFrame;
            state.pendingFrame = nullptr;
        }
        
        std::cout << "[LoadMediaFile] Starting playback..." << std::endl;
        state.decoder->play();
        if (state.audioOutput) {
            state.audioOutput->play();
        }
        
        std::cout << "[LoadMediaFile] Load complete!" << std::endl;
    } else {
        std::cerr << "[LoadMediaFile] FAILED to open file!" << std::endl;
    }
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
    colors[ImGuiCol_Header] = ImVec4(0.898f, 0.078f, 0.078f, 0.2f);         // Netflix red for menu items
    colors[ImGuiCol_HeaderHovered] = ImVec4(0.898f, 0.078f, 0.078f, 0.4f);  // Brighter red on hover
    colors[ImGuiCol_HeaderActive] = ImVec4(0.898f, 0.078f, 0.078f, 0.6f);   // Even brighter on click
    
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

// Netflix-style tooltip helper
void ShowTooltip(AppState& state, const char* text, float hoverTime = 0.5f) {
    if (ImGui::IsItemHovered()) {
        state.tooltipHoverTime += ImGui::GetIO().DeltaTime;
        if (state.tooltipHoverTime >= hoverTime) {
            state.tooltipText = text;
            state.tooltipPos = ImGui::GetItemRectMin();
            state.tooltipPos.y -= 35;  // Above the button
            state.tooltipPos.x += ImGui::GetItemRectSize().x * 0.5f;  // Center
        }
    } else {
        state.tooltipHoverTime = 0.0f;
    }
}

// Render accumulated tooltip
void RenderTooltip(AppState& state) {
    if (state.tooltipText && state.tooltipHoverTime >= 0.5f) {
        ImDrawList* draw = ImGui::GetWindowDrawList();
        ImVec2 textSize = ImGui::CalcTextSize(state.tooltipText);
        float padding = 8.0f;
        ImVec2 bgMin = ImVec2(state.tooltipPos.x - textSize.x * 0.5f - padding, state.tooltipPos.y - padding);
        ImVec2 bgMax = ImVec2(state.tooltipPos.x + textSize.x * 0.5f + padding, state.tooltipPos.y + textSize.y + padding);
        
        // Dark background with slight transparency
        draw->AddRectFilled(bgMin, bgMax, IM_COL32(20, 20, 20, 240), 4.0f);
        draw->AddRect(bgMin, bgMax, IM_COL32(80, 80, 80, 255), 4.0f, 0, 1.0f);
        
        // White text
        draw->AddText(ImVec2(state.tooltipPos.x - textSize.x * 0.5f, state.tooltipPos.y),
            IM_COL32(255, 255, 255, 255), state.tooltipText);
    }
    // Reset for next frame
    state.tooltipText = nullptr;
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
    
    // First triangle
    ImVec2 tri1[3] = {
        ImVec2(center.x + direction * size * 0.2f, center.y),
        ImVec2(center.x + direction * size * -0.2f, center.y - size * 0.4f),
        ImVec2(center.x + direction * size * -0.2f, center.y + size * 0.4f)
    };
    draw->AddTriangleFilled(tri1[0], tri1[1], tri1[2], color);
    
    // Second triangle (offset)
    float offset = size * 0.35f;
    ImVec2 tri2[3] = {
        ImVec2(center.x + direction * (size * 0.2f + offset), center.y),
        ImVec2(center.x + direction * (size * -0.2f + offset), center.y - size * 0.4f),
        ImVec2(center.x + direction * (size * -0.2f + offset), center.y + size * 0.4f)
    };
    draw->AddTriangleFilled(tri2[0], tri2[1], tri2[2], color);
    
    // "5" text below
    char text[] = "5";
    ImVec2 textSize = ImGui::CalcTextSize(text);
    ImVec2 textPos = ImVec2(
        center.x - textSize.x * 0.5f,
        center.y + size * 0.65f
    );
    draw->AddText(ImGui::GetFont(), 16.0f, textPos, color, text);
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
    
    float panelWidth = 450.0f;  // Wider for better visibility
    float panelX = screenSize.x - panelWidth;
    
    ImGui::SetNextWindowPos(ImVec2(panelX, 0));
    ImGui::SetNextWindowSize(ImVec2(panelWidth, screenSize.y));
    
    // Dark background with gradient
    ImGui::PushStyleColor(ImGuiCol_WindowBg, ImVec4(0.06f, 0.06f, 0.06f, 0.98f));
    ImGui::PushStyleVar(ImGuiStyleVar_WindowPadding, ImVec2(0, 0));
    ImGui::PushStyleVar(ImGuiStyleVar_WindowBorderSize, 0.0f);
    
    ImGui::Begin("##Playlist", nullptr, 
        ImGuiWindowFlags_NoDecoration | 
        ImGuiWindowFlags_NoMove | 
        ImGuiWindowFlags_NoResize |
        ImGuiWindowFlags_NoSavedSettings);
    
    ImDrawList* draw = ImGui::GetWindowDrawList();
    
    // Header with Netflix styling
    ImGui::SetCursorPos(ImVec2(32, 32));
    ImGui::PushFont(ImGui::GetIO().Fonts->Fonts.Size > 1 ? ImGui::GetIO().Fonts->Fonts[1] : ImGui::GetFont());
    ImGui::TextColored(ImVec4(1.0f, 1.0f, 1.0f, 1.0f), "Playlist");
    ImGui::PopFont();
    
    // File count with better styling
    ImGui::SameLine();
    ImGui::SetCursorPosX(140);
    char countText[32];
    snprintf(countText, sizeof(countText), "(%zu videos)", state.playlistFiles.size());
    ImGui::TextColored(ImVec4(0.7f, 0.7f, 0.7f, 1.0f), "%s", countText);
    
    // Close button with Netflix red hover
    ImGui::SetCursorPos(ImVec2(panelWidth - 60, 28));
    ImGui::PushStyleColor(ImGuiCol_Button, ImVec4(0, 0, 0, 0));
    ImGui::PushStyleColor(ImGuiCol_ButtonHovered, ImVec4(0.898f, 0.078f, 0.078f, 0.3f));
    ImGui::PushStyleColor(ImGuiCol_ButtonActive, ImVec4(0.898f, 0.078f, 0.078f, 0.5f));
    
    if (ImGui::Button("✕##ClosePlaylist", ImVec2(40, 40))) {
        state.showPlaylistPanel = false;
    }
    
    ImGui::PopStyleColor(3);
    
    // Separator with gradient effect
    ImVec2 sepStart = ImVec2(panelX + 32, 90);
    ImVec2 sepEnd = ImVec2(panelX + panelWidth - 32, 90);
    draw->AddLine(sepStart, sepEnd, IM_COL32(60, 60, 60, 255), 1.0f);
    
    // Scrollable playlist items
    ImGui::SetCursorPos(ImVec2(0, 110));
    ImGui::BeginChild("##PlaylistItems", ImVec2(panelWidth, screenSize.y - 110), false);
    
    for (size_t i = 0; i < state.playlistFiles.size(); i++) {
        ImGui::PushID((int)i);
        
        bool isPlaying = (state.currentPlaylistIndex >= 0 && i == (size_t)state.currentPlaylistIndex);
        
        // Item background with better styling
        ImVec2 itemPos = ImGui::GetCursorScreenPos();
        ImVec2 itemSize = ImVec2(panelWidth, 90);  // Taller items
        
        // Playing item has Netflix red accent
        if (isPlaying) {
            // Left accent bar
            draw->AddRectFilled(
                ImVec2(itemPos.x, itemPos.y),
                ImVec2(itemPos.x + 4, itemPos.y + itemSize.y),
                IM_COL32(229, 9, 20, 255));
            // Background tint
            draw->AddRectFilled(itemPos, 
                ImVec2(itemPos.x + itemSize.x, itemPos.y + itemSize.y),
                IM_COL32(229, 9, 20, 25));
        }
        
        // Clickable area
        ImGui::SetCursorPos(ImVec2(0, ImGui::GetCursorPosY()));
        if (ImGui::InvisibleButton("##Item", itemSize)) {
            // Load the selected file
            if (state.decoder) {
                std::string filepath = state.playlistFiles[i];
                
                // CRITICAL: Stop and cleanup current playback before loading new file
                state.isPlaying = false;
                if (state.decoder) {
                    state.decoder->pause();
                }
                if (state.audioOutput) {
                    state.audioOutput->pause();
                    state.audioOutput->clearQueue();
                }
                
                // Clear pending frame BEFORE opening new file
                if (state.pendingFrame) {
                    delete state.pendingFrame;
                    state.pendingFrame = nullptr;
                }
                
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
            // Subtle hover effect
            draw->AddRectFilled(itemPos,
                ImVec2(itemPos.x + itemSize.x, itemPos.y + itemSize.y),
                IM_COL32(255, 255, 255, 20));
        }
        
        // Number badge (Netflix style)
        char numText[8];
        snprintf(numText, sizeof(numText), "%zu", i + 1);
        ImVec2 numTextSize = ImGui::CalcTextSize(numText);
        ImGui::SetCursorPos(ImVec2(24, itemPos.y - ImGui::GetWindowPos().y + 35));
        ImGui::PushStyleColor(ImGuiCol_Text, isPlaying ? 
            ImVec4(0.898f, 0.035f, 0.078f, 1.0f) : ImVec4(0.5f, 0.5f, 0.5f, 1.0f));
        ImGui::Text("%s.", numText);
        ImGui::PopStyleColor();
        
        // File name with better spacing
        ImGui::SetCursorPos(ImVec2(60, itemPos.y - ImGui::GetWindowPos().y + 28));
        
        if (isPlaying) {
            ImGui::PushStyleColor(ImGuiCol_Text, ImVec4(1.0f, 1.0f, 1.0f, 1.0f));  // Bright white
        }
        
        // Truncate long file names
        std::string displayName = state.playlistNames[i];
        if (displayName.length() > 35) {
            displayName = displayName.substr(0, 32) + "...";
        }
        ImGui::Text("%s", displayName.c_str());
        
        if (isPlaying) {
            ImGui::PopStyleColor();
        }
        
        // Now playing indicator
        if (isPlaying) {
            ImGui::SetCursorPos(ImVec2(60, itemPos.y - ImGui::GetWindowPos().y + 52));
            ImGui::PushFont(ImGui::GetIO().Fonts->Fonts[0]);  // Smaller font
            ImGui::TextColored(ImVec4(0.898f, 0.035f, 0.078f, 1.0f), "▶ Now Playing");
            ImGui::PopFont();
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
    // Hide menu bar in fullscreen mode
    if (state.isFullscreen) {
        state.showMenuBar = false;
        return;
    }
    
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
                std::string filepath = OpenFileDialog();
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
                        
                        state.ignoreNextClick = true;  // Prevent file dialog click from toggling play/pause
                        
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

#ifdef __APPLE__
void RenderNetflixUI(AppState& state, NSWindow* window) {
#else
void RenderNetflixUI(AppState& state, HWND window) {
#endif
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
        float videoAspect = (float)state.videoTextureWidth / (float)state.videoTextureHeight;
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
    // State tracking for click-and-hold behavior (static, outside conditional)
    static double mouseDownTime = 0.0;
    static bool mouseWasDown = false;
    static bool wasDoubleClick = false;
    static double doubleClickTime = 0.0;
    static bool playPauseHandled = false;
    static double lastHoldDuration = 0.0;
    static double lastClickTime = 0.0;
    static bool hasPendingClick = false;
    static double pendingClickTime = 0.0;
    
    bool isDoubleClick = false;
    bool itemActive = false;
    
    // Only create video surface button when playing (let pause overlay handle clicks when paused)
    if (state.isPlaying || !state.fileLoaded) {
        ImVec2 clickableSize = ImVec2(screenSize.x, screenSize.y - 150);
        ImGui::SetCursorPos(ImVec2(0, 0));
        ImGui::InvisibleButton("##VideoSurface", clickableSize);
        itemActive = ImGui::IsItemActive();
        isDoubleClick = ImGui::IsItemHovered() && ImGui::IsMouseDoubleClicked(0);
    }
    
    const double HOLD_THRESHOLD = 0.2;
    bool mouseDown = ImGui::IsMouseDown(0);
    double currentTime = ImGui::GetTime();
    
    // Detect double-click first
    if (isDoubleClick) {
        wasDoubleClick = true;
        doubleClickTime = currentTime;
        playPauseHandled = true;
        hasPendingClick = false;
    }
    
    // Clear double-click flag after 500ms
    if (wasDoubleClick && (currentTime - doubleClickTime) > 0.5) {
        wasDoubleClick = false;
    }
    
    // Process pending click if enough time has passed without double-click
    // Wait 150ms (half of typical 300ms double-click threshold) to be safe
    if (hasPendingClick && (currentTime - pendingClickTime) > 0.15 && !wasDoubleClick) {
        if (state.ignoreNextClick) {
            state.ignoreNextClick = false;
            hasPendingClick = false;
        } else {
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
            hasPendingClick = false;
        }
    }
    
    // Track mouse down event
    if (itemActive && mouseDown && !mouseWasDown && !wasDoubleClick) {
        // Mouse just pressed down
        mouseDownTime = currentTime;
        playPauseHandled = false;
    }
    
    // Calculate hold duration
    double holdDuration = (itemActive && mouseDown) ? (currentTime - mouseDownTime) : lastHoldDuration;
    
    // Preserve hold duration when mouse is down
    if (itemActive && mouseDown) {
        lastHoldDuration = holdDuration;
    }
    
    // Click-and-hold: 2x speed (YouTube-style)
    // Only activate after hold threshold and if video is playing
    bool wasHoldingMouse = state.is2xSpeedMode;
    bool shouldActivate2x = itemActive && mouseDown && 
                           holdDuration > HOLD_THRESHOLD && 
                           state.isPlaying && 
                           !wasDoubleClick;
    
    state.is2xSpeedMode = shouldActivate2x;
    
    // Entering 2x speed mode
    if (state.is2xSpeedMode && !wasHoldingMouse && state.fileLoaded) {
        state.normalPlaybackSpeed = state.playbackSpeed;
        state.playbackSpeed = 2.0f;
        state.show2xSpeedIndicator = true;
        // Apply 2x speed to audio
        if (state.audioOutput) {
            state.audioOutput->setPlaybackRate(2.0f);
        }
    }
    
    // Exiting 2x speed mode
    if (!state.is2xSpeedMode && wasHoldingMouse) {
        state.playbackSpeed = state.normalPlaybackSpeed;
        state.show2xSpeedIndicator = false;
        // Restore normal speed to audio
        if (state.audioOutput) {
            state.audioOutput->setPlaybackRate(1.0f);
        }
    }
    
    // Handle play/pause on mouse RELEASE (not on press)
    // Only if it was a quick click (not a hold) and not a double-click
    if (mouseWasDown && !mouseDown) {
        // Check if we should ignore this click
        if (state.ignoreNextClick) {
            state.ignoreNextClick = false;
        } else {
            // Mouse just released
            // Check if click was in controls area (bottom 150px)
            ImVec2 mousePos = io.MousePos;
            ImVec2 windowPos = ImGui::GetWindowPos();
            float relativeY = mousePos.y - windowPos.y;
            bool clickInControlsArea = relativeY > (io.DisplaySize.y - 150);
            
            // Check if this might be part of a double-click sequence
            // If we clicked within 300ms of last click, don't process as play/pause
            double timeSinceLastClick = currentTime - lastClickTime;
            bool mightBeDoubleClick = timeSinceLastClick < 0.3;
            
            // Only toggle play/pause if not handled, not a double-click, file is loaded, AND not in controls area
            if (!playPauseHandled && lastHoldDuration < HOLD_THRESHOLD && !wasDoubleClick && !mightBeDoubleClick && state.fileLoaded && !clickInControlsArea) {
                // Don't toggle immediately - set pending flag to wait one frame for potential double-click
                hasPendingClick = true;
                pendingClickTime = currentTime;

            }
        }
        // Reset for next interaction only after mouse is fully released
        if (!mouseDown) {
            playPauseHandled = false;
            lastHoldDuration = 0.0;
            lastClickTime = currentTime;  // Update last click time on release
        }
    }
    
    // Update previous state
    mouseWasDown = mouseDown;
    
    // Double-click: Toggle fullscreen
    // Use static to prevent repeated toggles
    static double lastFullscreenToggle = 0.0;
    
    if (isDoubleClick) {
        double currentTime = ImGui::GetTime();
        // Only toggle if at least 500ms has passed since last toggle
        if (currentTime - lastFullscreenToggle > 0.5) {
#ifdef __APPLE__
            ToggleFullscreen(window, state.isFullscreen);
#else
            state.isFullscreen = !state.isFullscreen;
#endif
            lastFullscreenToggle = currentTime;
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
    
    // ===== KEYBOARD SHORTCUTS (Netflix-style) =====
    if (state.fileLoaded) {
        // Space bar: Play/Pause
        if (ImGui::IsKeyPressed(ImGuiKey_Space)) {
            state.isPlaying = !state.isPlaying;
            if (state.decoder) {
                if (state.isPlaying) {
                    state.decoder->play();
                    if (state.audioOutput) state.audioOutput->play();
                } else {
                    state.decoder->pause();
                    if (state.audioOutput) state.audioOutput->pause();
                }
            }
            state.showControls = true;
            state.controlsTimer = 3.0f;
        }
        
        // Left Arrow: Skip backward 5s
        if (ImGui::IsKeyPressed(ImGuiKey_LeftArrow) && state.fileLoaded && state.decoder) {
            std::cout << "[DEBUG] Left arrow pressed - fileLoaded=" << state.fileLoaded 
                      << " decoder=" << (void*)state.decoder << std::endl;
            state.currentTime = fmaxf(state.currentTime - 5.0f, 0.0f);
            std::cout << "[DEBUG] Seeking to: " << state.currentTime << std::endl;
            if (state.pendingFrame) {
                std::cout << "[DEBUG] Deleting pending frame" << std::endl;
                delete state.pendingFrame;
                state.pendingFrame = nullptr;
            }
            std::cout << "[DEBUG] Calling decoder->seek()" << std::endl;
            state.decoder->seek(state.currentTime);
            std::cout << "[DEBUG] Seek completed" << std::endl;
            
            // Set flag to prevent old frames from resetting currentTime
            state.justSeeked = true;
            state.videoStartTime = 0.0;
            
            if (state.audioOutput) {
                std::cout << "[DEBUG] Clearing audio queue" << std::endl;
                state.audioOutput->clearQueue();
                state.audioOutput->setAudioClock(state.currentTime);
            }
            state.lastVideoFramePTS = state.currentTime;
            std::cout << "[DEBUG] Left arrow handler completed" << std::endl;
            // Show skip animation for 0.8s
            state.showSkipAnimation = true;
            state.skipAnimationTimer = 0.8f;
            state.skipAnimationDirection = -1;
            state.skipAnimationSeconds = 5;
            state.showControls = true;
            state.controlsTimer = 3.0f;
        }
        
        // Right Arrow: Skip forward 5s
        if (ImGui::IsKeyPressed(ImGuiKey_RightArrow) && state.fileLoaded && state.decoder) {
            std::cout << "[DEBUG] Right arrow pressed - fileLoaded=" << state.fileLoaded 
                      << " decoder=" << (void*)state.decoder << std::endl;
            state.currentTime = fminf(state.currentTime + 5.0f, state.duration);
            std::cout << "[DEBUG] Seeking to: " << state.currentTime << std::endl;
            if (state.pendingFrame) {
                std::cout << "[DEBUG] Deleting pending frame" << std::endl;
                delete state.pendingFrame;
                state.pendingFrame = nullptr;
            }
            std::cout << "[DEBUG] Calling decoder->seek()" << std::endl;
            state.decoder->seek(state.currentTime);
            std::cout << "[DEBUG] Seek completed" << std::endl;
            
            // Set flag to prevent old frames from resetting currentTime
            state.justSeeked = true;
            state.videoStartTime = 0.0;
            
            if (state.audioOutput) {
                std::cout << "[DEBUG] Clearing audio queue" << std::endl;
                state.audioOutput->clearQueue();
                state.audioOutput->setAudioClock(state.currentTime);
            }
            state.lastVideoFramePTS = state.currentTime;
            std::cout << "[DEBUG] Right arrow handler completed" << std::endl;
            // Show skip animation for 0.8s
            state.showSkipAnimation = true;
            state.skipAnimationTimer = 0.8f;
            state.skipAnimationDirection = 1;
            state.skipAnimationSeconds = 5;
            state.showControls = true;
            state.controlsTimer = 3.0f;
        }
        
        // Up Arrow: Volume up
        if (ImGui::IsKeyPressed(ImGuiKey_UpArrow)) {
            state.volume = fminf(state.volume + 0.1f, 1.0f);
            if (state.audioOutput) {
                state.audioOutput->setVolume(state.volume);
            }
            state.showControls = true;
            state.controlsTimer = 3.0f;
        }
        
        // Down Arrow: Volume down
        if (ImGui::IsKeyPressed(ImGuiKey_DownArrow)) {
            state.volume = fmaxf(state.volume - 0.1f, 0.0f);
            if (state.audioOutput) {
                state.audioOutput->setVolume(state.volume);
            }
            state.showControls = true;
            state.controlsTimer = 3.0f;
        }
        
        // M key: Mute/Unmute
        if (ImGui::IsKeyPressed(ImGuiKey_M)) {
            state.isMuted = !state.isMuted;
            if (state.audioOutput) {
                state.audioOutput->setVolume(state.isMuted ? 0.0f : state.volume);
            }
            state.showControls = true;
            state.controlsTimer = 3.0f;
        }
        
        // F key: Fullscreen toggle
        static double lastFKeyToggle = 0.0;
        if (ImGui::IsKeyPressed(ImGuiKey_F)) {
            double currentTime = ImGui::GetTime();
            // Prevent rapid toggling - at least 500ms between toggles
            if (currentTime - lastFKeyToggle > 0.5) {
#ifdef __APPLE__
                ToggleFullscreen(window, state.isFullscreen);
#else
                state.isFullscreen = !state.isFullscreen;
#endif
                lastFKeyToggle = currentTime;
            }
            state.showControls = true;
            state.controlsTimer = 3.0f;
        }
        
        // Escape key: Exit fullscreen
        static double lastEscapeToggle = 0.0;
        if (ImGui::IsKeyPressed(ImGuiKey_Escape) && state.isFullscreen) {
            double currentTime = ImGui::GetTime();
            // Prevent rapid toggling
            if (currentTime - lastEscapeToggle > 0.5) {
#ifdef __APPLE__
                ToggleFullscreen(window, state.isFullscreen);
#else
                state.isFullscreen = false;
#endif
                lastEscapeToggle = currentTime;
            }
            state.showControls = true;
            state.controlsTimer = 3.0f;
        }
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
        
        // Title (top of controls area) - MUCH BIGGER for Netflix feel
        // Only show title in windowed mode, not in fullscreen
        if (!state.isFullscreen) {
            float titleY = screenSize.y - 260;
            controlDrawList->AddText(ImGui::GetFont(), 54.0f,  // Increased from 28px to 54px
                ImVec2(50, titleY),
                IM_COL32(255, 255, 255, (int)(255 * alpha)),
                state.currentTitle.c_str()
            );
        }
        
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
        ImGui::PushStyleColor(ImGuiCol_Border, ImVec4(0.0f, 0.0f, 0.0f, 0.0f)); // Remove border
        ImGui::PushStyleColor(ImGuiCol_NavHighlight, ImVec4(0.0f, 0.0f, 0.0f, 0.0f)); // Remove nav highlight
        ImGui::PushStyleVar(ImGuiStyleVar_FrameBorderSize, 0.0f); // No border
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
                
                // Set flag to prevent old frames from resetting currentTime
                state.justSeeked = true;
                state.videoStartTime = 0.0;
                
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
        
        // Draw custom progress bar appearance (Netflix style - thicker on hover)
        float barHeight = progressHovered ? 8.0f : 4.0f;  // Thicker on hover
        ImVec2 progressBarMin = ImVec2(50, progressY - barHeight * 0.5f + 3);
        ImVec2 progressBarMax = ImVec2(50 + progressWidth, progressY + barHeight * 0.5f + 3);
        float progress = state.currentTime / state.duration;
        
        // Background track (darker on hover)
        ImU32 bgColor = progressHovered ? IM_COL32(90, 90, 90, (int)(255 * alpha)) : IM_COL32(70, 70, 70, (int)(200 * alpha));
        controlDrawList->AddRectFilled(progressBarMin, progressBarMax, bgColor, barHeight * 0.5f);
        
        // Progress fill (Netflix red, brighter on hover)
        ImU32 fillColor = progressHovered ? IM_COL32(229, 9, 20, 255) : IM_COL32(229, 9, 20, (int)(255 * alpha));
        controlDrawList->AddRectFilled(progressBarMin, 
            ImVec2(progressBarMin.x + progressWidth * progress, progressBarMax.y),
            fillColor, barHeight * 0.5f);
        
        // Scrubber circle (only visible on hover)
        if (progressHovered) {
            ImVec2 scrubberPos = ImVec2(progressBarMin.x + progressWidth * progress, progressY + 3);
            controlDrawList->AddCircleFilled(scrubberPos, 10.0f,  // Larger scrubber
                IM_COL32(229, 9, 20, 255), 16);
            // White border on scrubber
            controlDrawList->AddCircle(scrubberPos, 10.0f,
                IM_COL32(255, 255, 255, 200), 16, 2.0f);
        }
        
        ImGui::PopStyleVar(2); // Pop 2 style vars
        ImGui::PopStyleColor(7); // Pop 7 colors
        
        // Control buttons (40px from bottom)
        float controlsY = screenSize.y - 40;
        float buttonSize = 48.0f;  // Consistent button size
        float buttonY = controlsY - buttonSize * 0.5f;  // Center vertically
        
        ImGui::SetCursorPos(ImVec2(50, buttonY));
        
        // Remove button background and hover boxes - we'll draw custom colored icons
        ImGui::PushStyleColor(ImGuiCol_Button, ImVec4(0, 0, 0, 0));
        ImGui::PushStyleColor(ImGuiCol_ButtonHovered, ImVec4(0, 0, 0, 0));  // Transparent - no box
        ImGui::PushStyleColor(ImGuiCol_ButtonActive, ImVec4(0, 0, 0, 0));   // Transparent - no box
        
        // Play/Pause button
        ImVec2 playButtonPos = ImGui::GetCursorScreenPos();
        
        // Update hover animation
        state.playButtonHovered = false;
        if (ImGui::Button("##PlayPause", ImVec2(buttonSize, buttonSize))) {
            state.isPlaying = !state.isPlaying;
            playPauseHandled = true;  // Prevent video click from also firing
            
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
        state.playButtonHovered = ImGui::IsItemHovered();
        ShowTooltip(state, state.isPlaying ? "Pause (Space)" : "Play (Space)");
        
        // Smooth hover animation
        float targetAnim = state.playButtonHovered ? 1.0f : 0.0f;
        state.playButtonHoverAnim += (targetAnim - state.playButtonHoverAnim) * io.DeltaTime * 10.0f;
        float scale = 1.0f + state.playButtonHoverAnim * 0.15f;  // Scale up 15% on hover
        
        ImVec2 playIconCenter = ImVec2(playButtonPos.x + buttonSize * 0.5f, playButtonPos.y + buttonSize * 0.5f);
        float iconSize = 24.0f * scale;
        
        // Netflix red on hover/press, white otherwise
        ImU32 iconColor = IM_COL32(255, 255, 255, (int)(255 * alpha));
        if (state.playButtonHovered || ImGui::IsItemActive()) {
            iconColor = IM_COL32(229, 9, 20, (int)(255 * alpha));  // Netflix red
        }
        
        if (state.isPlaying) {
            DrawPauseIcon(controlDrawList, playIconCenter, iconSize, iconColor);
        } else {
            DrawPlayIcon(controlDrawList, playIconCenter, iconSize, iconColor);
        }
        
        ImGui::SameLine(0, 8);
        
        // Skip backward button (Netflix-style accumulating)
        ImVec2 skipBackPos = ImGui::GetCursorScreenPos();
        state.skipBackButtonPos = skipBackPos;  // Save for animation
        if (ImGui::Button("##SkipBack", ImVec2(buttonSize, buttonSize)) && state.fileLoaded && state.decoder) {
            double currentTime = ImGui::GetTime();
            
            // Check if this is within 1 second of last tap (accumulate)
            if (currentTime - state.lastSkipBackTime < 1.0) {
                state.accumulatedSkipBackSeconds += 5;
            } else {
                state.accumulatedSkipBackSeconds = 5;  // Reset accumulation
            }
            state.lastSkipBackTime = currentTime;
            
            // Perform the seek
            state.currentTime = fmaxf(state.currentTime - 5.0f, 0.0f);
            
            // CRITICAL: Clear pending frame BEFORE seek
            if (state.pendingFrame) {
                delete state.pendingFrame;
                state.pendingFrame = nullptr;
            }
            
            state.decoder->seek(state.currentTime);
            state.justSeeked = true;
            state.videoStartTime = 0.0;
            
            // Reset audio clock
            if (state.audioOutput) {
                state.audioOutput->clearQueue();
                state.audioOutput->setAudioClock(state.currentTime);
            }
            state.lastVideoFramePTS = state.currentTime;
            
            // Trigger accumulation animation
            state.showSkipBackAccumulation = true;
            state.skipBackAnimTimer = 1.0f;  // 1 second animation
        }
        state.skipBackHovered = ImGui::IsItemHovered();
        ShowTooltip(state, "Rewind 5 seconds (Left Arrow)");
        float targetSkipBackAnim = state.skipBackHovered ? 1.0f : 0.0f;
        state.skipBackHoverAnim += (targetSkipBackAnim - state.skipBackHoverAnim) * io.DeltaTime * 10.0f;
        float skipBackScale = 1.0f + state.skipBackHoverAnim * 0.15f;
        
        // Netflix red on hover/press, white otherwise
        ImU32 skipBackColor = IM_COL32(255, 255, 255, (int)(255 * alpha));
        if (state.skipBackHovered || ImGui::IsItemActive()) {
            skipBackColor = IM_COL32(229, 9, 20, (int)(255 * alpha));  // Netflix red
        }
        
        DrawSkipIcon(controlDrawList, ImVec2(skipBackPos.x + buttonSize * 0.5f, skipBackPos.y + buttonSize * 0.5f), 
            18.0f * skipBackScale, false, skipBackColor);
        
        ImGui::SameLine(0, 8);
        
        // Skip forward button (Netflix-style accumulating)
        ImVec2 skipForwardPos = ImGui::GetCursorScreenPos();
        state.skipForwardButtonPos = skipForwardPos;  // Save for animation
        if (ImGui::Button("##SkipForward", ImVec2(buttonSize, buttonSize)) && state.fileLoaded && state.decoder) {
            double currentTime = ImGui::GetTime();
            
            // Check if this is within 1 second of last tap (accumulate)
            if (currentTime - state.lastSkipForwardTime < 1.0) {
                state.accumulatedSkipForwardSeconds += 5;
            } else {
                state.accumulatedSkipForwardSeconds = 5;  // Reset accumulation
            }
            state.lastSkipForwardTime = currentTime;
            
            // Perform the seek
            state.currentTime = fminf(state.currentTime + 5.0f, state.duration);
            
            // CRITICAL: Clear pending frame BEFORE seek
            if (state.pendingFrame) {
                delete state.pendingFrame;
                state.pendingFrame = nullptr;
            }
            
            state.decoder->seek(state.currentTime);
            state.justSeeked = true;
            state.videoStartTime = 0.0;
            
            // Reset audio clock
            if (state.audioOutput) {
                state.audioOutput->clearQueue();
                state.audioOutput->setAudioClock(state.currentTime);
            }
            state.lastVideoFramePTS = state.currentTime;
            
            // Trigger accumulation animation
            state.showSkipForwardAccumulation = true;
            state.skipForwardAnimTimer = 1.0f;  // 1 second animation
        }
        state.skipForwardHovered = ImGui::IsItemHovered();
        ShowTooltip(state, "Forward 5 seconds (Right Arrow)");
        float targetSkipForwardAnim = state.skipForwardHovered ? 1.0f : 0.0f;
        state.skipForwardHoverAnim += (targetSkipForwardAnim - state.skipForwardHoverAnim) * io.DeltaTime * 10.0f;
        float skipForwardScale = 1.0f + state.skipForwardHoverAnim * 0.15f;
        
        // Netflix red on hover/press, white otherwise
        ImU32 skipForwardColor = IM_COL32(255, 255, 255, (int)(255 * alpha));
        if (state.skipForwardHovered || ImGui::IsItemActive()) {
            skipForwardColor = IM_COL32(229, 9, 20, (int)(255 * alpha));  // Netflix red
        }
        
        DrawSkipIcon(controlDrawList, ImVec2(skipForwardPos.x + buttonSize * 0.5f, skipForwardPos.y + buttonSize * 0.5f), 
            18.0f * skipForwardScale, true, skipForwardColor);
        
        ImGui::SameLine(0, 16);
        
        // Volume icon and slider - properly aligned
        ImVec2 volumeIconPos = ImGui::GetCursorScreenPos();
        if (ImGui::Button("##VolumeIcon", ImVec2(buttonSize, buttonSize))) {
            state.isMuted = !state.isMuted;
            if (state.audioOutput) {
                state.audioOutput->setVolume(state.isMuted ? 0.0f : state.volume);
            }
        }
        bool volumeIconHovered = ImGui::IsItemHovered();
        ShowTooltip(state, state.isMuted ? "Unmute (M)" : "Mute (M)");
        ImU32 volumeColor = IM_COL32(255, 255, 255, (int)(255 * alpha));
        if (volumeIconHovered || ImGui::IsItemActive()) {
            volumeColor = IM_COL32(229, 9, 20, (int)(255 * alpha));  // Netflix red
        }
        DrawVolumeIcon(controlDrawList, ImVec2(volumeIconPos.x + buttonSize * 0.25f, volumeIconPos.y + buttonSize * 0.25f), 
            state.volume, state.isMuted, volumeColor);
        
        ImGui::SameLine(0, 4);
        
        // Volume slider
        ImGui::SetCursorPosY(buttonY + buttonSize * 0.35f);  // Center slider vertically with buttons
        ImGui::PushItemWidth(100);
        if (ImGui::SliderFloat("##Volume", &state.volume, 0.0f, 1.0f, "")) {
            if (state.audioOutput) {
                state.audioOutput->setVolume(state.volume);
            }
        }
        ImGui::PopItemWidth();
        
        ImGui::SameLine(0, 20);
        
        // Time display - centered with buttons
        std::string timeStr = FormatTime(state.currentTime) + " / " + FormatTime(state.duration);
        controlDrawList->AddText(ImGui::GetFont(), 18.0f,
            ImVec2(ImGui::GetCursorScreenPos().x, buttonY + buttonSize * 0.3f),
            IM_COL32(255, 255, 255, (int)(230 * alpha)), timeStr.c_str());
        
        // Right-side controls
        float rightControlsX = screenSize.x - 280;
        ImGui::SetCursorPos(ImVec2(rightControlsX, buttonY));
        
        // Playlist/Episodes button (disabled when no file loaded)
        ImVec2 playlistPos = ImGui::GetCursorScreenPos();
        bool playlistEnabled = state.fileLoaded && !state.playlistFiles.empty();
        if (!playlistEnabled) {
            ImGui::PushStyleVar(ImGuiStyleVar_Alpha, alpha * 0.3f);  // Dim when disabled
        }
        if (ImGui::Button("##Playlist", ImVec2(buttonSize, buttonSize)) && playlistEnabled) {
            state.showPlaylistPanel = !state.showPlaylistPanel;
        }
        state.playlistHovered = ImGui::IsItemHovered() && playlistEnabled;
        if (playlistEnabled) ShowTooltip(state, "Playlist");
        float targetPlaylistAnim = state.playlistHovered ? 1.0f : 0.0f;
        state.playlistHoverAnim += (targetPlaylistAnim - state.playlistHoverAnim) * io.DeltaTime * 10.0f;
        float playlistScale = 1.0f + state.playlistHoverAnim * 0.15f;
        
        ImU32 playlistColor = IM_COL32(255, 255, 255, (int)(255 * alpha * (playlistEnabled ? 1.0f : 0.3f)));
        if (state.playlistHovered || ImGui::IsItemActive()) {
            playlistColor = IM_COL32(229, 9, 20, (int)(255 * alpha));  // Netflix red
        }
        
        DrawPlaylistIcon(controlDrawList, ImVec2(playlistPos.x + buttonSize * 0.5f, playlistPos.y + buttonSize * 0.5f), 
            20.0f * playlistScale, playlistColor);
        if (!playlistEnabled) {
            ImGui::PopStyleVar();
        }
        
        ImGui::SameLine(0, 8);
        
        // Settings button
        ImVec2 settingsPos = ImGui::GetCursorScreenPos();
        if (ImGui::Button("##Settings", ImVec2(buttonSize, buttonSize))) {
            // TODO: Open settings
        }
        state.settingsHovered = ImGui::IsItemHovered();
        ShowTooltip(state, "Settings");
        float targetSettingsAnim = state.settingsHovered ? 1.0f : 0.0f;
        state.settingsHoverAnim += (targetSettingsAnim - state.settingsHoverAnim) * io.DeltaTime * 10.0f;
        float settingsScale = 1.0f + state.settingsHoverAnim * 0.15f;
        
        ImU32 settingsColor = IM_COL32(255, 255, 255, (int)(255 * alpha));
        if (state.settingsHovered || ImGui::IsItemActive()) {
            settingsColor = IM_COL32(229, 9, 20, (int)(255 * alpha));  // Netflix red
        }
        
        DrawSettingsIcon(controlDrawList, ImVec2(settingsPos.x + buttonSize * 0.5f, settingsPos.y + buttonSize * 0.5f), 
            22.0f * settingsScale, settingsColor);
        
        ImGui::SameLine(0, 8);
        
        // Audio button
        ImVec2 audioPos = ImGui::GetCursorScreenPos();
        if (ImGui::Button("##Audio", ImVec2(buttonSize, buttonSize))) {
            state.showAudioMenu = !state.showAudioMenu;
        }
        state.audioButtonHovered = ImGui::IsItemHovered();
        ShowTooltip(state, "Audio");
        float targetAudioAnim = state.audioButtonHovered ? 1.0f : 0.0f;
        state.audioButtonHoverAnim += (targetAudioAnim - state.audioButtonHoverAnim) * io.DeltaTime * 10.0f;
        float audioScale = 1.0f + state.audioButtonHoverAnim * 0.15f;
        
        ImU32 audioColor = IM_COL32(255, 255, 255, (int)(255 * alpha));
        if (state.audioButtonHovered || ImGui::IsItemActive()) {
            audioColor = IM_COL32(229, 9, 20, (int)(255 * alpha));  // Netflix red
        }
        
        DrawAudioIcon(controlDrawList, ImVec2(audioPos.x + buttonSize * 0.5f, audioPos.y + buttonSize * 0.5f), 
            22.0f * audioScale, audioColor);
        
        ImGui::SameLine(0, 8);
        
        // Subtitles button
        ImVec2 subtitlesPos = ImGui::GetCursorScreenPos();
        if (ImGui::Button("##Subtitles", ImVec2(buttonSize, buttonSize))) {
            state.showSubtitleMenu = !state.showSubtitleMenu;
        }
        state.subtitlesHovered = ImGui::IsItemHovered();
        ShowTooltip(state, "Subtitles (C)");
        float targetSubtitlesAnim = state.subtitlesHovered ? 1.0f : 0.0f;
        state.subtitlesHoverAnim += (targetSubtitlesAnim - state.subtitlesHoverAnim) * io.DeltaTime * 10.0f;
        float subtitlesScale = 1.0f + state.subtitlesHoverAnim * 0.15f;
        
        ImU32 subtitlesColor = IM_COL32(255, 255, 255, (int)(255 * alpha));
        if (state.subtitlesHovered || ImGui::IsItemActive()) {
            subtitlesColor = IM_COL32(229, 9, 20, (int)(255 * alpha));  // Netflix red
        }
        
        DrawSubtitlesIcon(controlDrawList, ImVec2(subtitlesPos.x + buttonSize * 0.5f, subtitlesPos.y + buttonSize * 0.5f), 
            22.0f * subtitlesScale, subtitlesColor);
        
        ImGui::SameLine(0, 8);
        
        // Fullscreen button
        static double lastButtonToggle = 0.0;
        ImVec2 fullscreenPos = ImGui::GetCursorScreenPos();
        if (ImGui::Button("##Fullscreen", ImVec2(buttonSize, buttonSize))) {
            double currentTime = ImGui::GetTime();
            // Prevent rapid toggling
            if (currentTime - lastButtonToggle > 0.5) {
#ifdef __APPLE__
                ToggleFullscreen(window, state.isFullscreen);
#else
                // Windows: Actually call the ToggleFullscreen function
                ToggleFullscreen((HWND)window, state.isFullscreen);
#endif
                lastButtonToggle = currentTime;
            }
        }
        state.fullscreenHovered = ImGui::IsItemHovered();
        ShowTooltip(state, state.isFullscreen ? "Exit Fullscreen (F)" : "Fullscreen (F)");
        float targetFullscreenAnim = state.fullscreenHovered ? 1.0f : 0.0f;
        state.fullscreenHoverAnim += (targetFullscreenAnim - state.fullscreenHoverAnim) * io.DeltaTime * 10.0f;
        float fullscreenScale = 1.0f + state.fullscreenHoverAnim * 0.15f;
        
        ImU32 fullscreenColor = IM_COL32(255, 255, 255, (int)(255 * alpha));
        if (state.fullscreenHovered || ImGui::IsItemActive()) {
            fullscreenColor = IM_COL32(229, 9, 20, (int)(255 * alpha));  // Netflix red
        }
        
        DrawFullscreenIcon(controlDrawList, ImVec2(fullscreenPos.x + buttonSize * 0.5f, fullscreenPos.y + buttonSize * 0.5f), 
            20.0f * fullscreenScale, fullscreenColor);
        
        // Render all tooltips
        RenderTooltip(state);
        
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
            
            // "+5" or "-5" or "+10" or "-10" text below icon
            char skipText[8];
            snprintf(skipText, sizeof(skipText), "%s%d", 
                state.skipAnimationDirection > 0 ? "+" : "-",
                state.skipAnimationSeconds);
            ImVec2 textSize = ImGui::CalcTextSize(skipText);
            ImVec2 textPos = ImVec2(center.x - textSize.x * 0.5f, center.y + 15);
            animDrawList->AddText(ImGui::GetFont(), 18.0f, textPos,
                IM_COL32(255, 255, 255, (int)(255 * animAlpha)), skipText);
        }
    }
    
    // Netflix-style pause overlay (large icons when paused)
    static bool playButtonClicked = false;  // Guard to prevent multiple clicks (outside if block)
    static double playButtonClickTime = 0.0;  // Time when play button was clicked
    
    // Reset click guard after 0.5 seconds
    double pauseOverlayTime = ImGui::GetTime();
    if (playButtonClicked && (pauseOverlayTime - playButtonClickTime) > 0.5) {
        playButtonClicked = false;
    }
    
    if (!state.isPlaying && state.fileLoaded) {
        ImVec2 center = ImVec2(screenSize.x * 0.5f, screenSize.y * 0.5f);
        ImDrawList* pauseDrawList = ImGui::GetWindowDrawList();
        
        float iconSize = 40.0f;
        float circleRadius = 70.0f;
        float spacing = 180.0f;
        
        // Left: Rewind 5s button
        ImVec2 leftCenter = ImVec2(center.x - spacing, center.y);
        ImGui::SetCursorScreenPos(ImVec2(leftCenter.x - circleRadius, leftCenter.y - circleRadius));
        ImGui::PushID("pause_overlay_rewind");
        bool leftHovered = false;
        bool leftClicked = ImGui::InvisibleButton("##rewind", ImVec2(circleRadius * 2, circleRadius * 2));
        leftHovered = ImGui::IsItemHovered();
        ImGui::PopID();
        
        ImU32 leftCircleColor = leftHovered ? IM_COL32(229, 9, 20, 200) : IM_COL32(0, 0, 0, 160);
        ImU32 leftIconColor = leftHovered ? IM_COL32(255, 255, 255, 255) : IM_COL32(255, 255, 255, 220);
        
        pauseDrawList->AddCircleFilled(leftCenter, circleRadius, leftCircleColor, 32);
        pauseDrawList->AddCircle(leftCenter, circleRadius, IM_COL32(255, 255, 255, 180), 32, 3.0f);
        DrawSkipIcon(pauseDrawList, leftCenter, iconSize, false, leftIconColor);
        
        if (leftClicked && state.decoder) {
            double currentTime = ImGui::GetTime();
            
            // Check if this is within 1 second of last tap (accumulate)
            if (currentTime - state.lastSkipBackTime < 1.0) {
                state.accumulatedSkipBackSeconds += 5;
            } else {
                state.accumulatedSkipBackSeconds = 5;  // Reset accumulation
            }
            state.lastSkipBackTime = currentTime;
            
            state.currentTime = fmaxf(state.currentTime - 5.0f, 0.0f);
            
            // Clear pending frame BEFORE seek
            if (state.pendingFrame) {
                delete state.pendingFrame;
                state.pendingFrame = nullptr;
            }
            
            // Perform the seek first
            state.decoder->seek(state.currentTime);
            state.justSeeked = true;
            state.videoStartTime = 0.0;
            
            // IMPORTANT: Pause AFTER seek (seek resumes decoder thread)
            state.isPlaying = false;
            state.ignoreNextClick = true;  // Prevent video surface button from toggling it back
            
            if (state.decoder) {
                state.decoder->pause();
            }
            
            if (state.audioOutput) {
                state.audioOutput->pause();
            }
            
            // Reset audio clock
            if (state.audioOutput) {
                state.audioOutput->clearQueue();
                state.audioOutput->setAudioClock(state.currentTime);
            }
            state.lastVideoFramePTS = state.currentTime;
            
            // Trigger accumulation animation
            state.showSkipBackAccumulation = true;
            state.skipBackAnimTimer = 1.0f;  // 1 second animation
        }
        
        // Center: Play button
        ImGui::SetCursorScreenPos(ImVec2(center.x - circleRadius, center.y - circleRadius));
        ImGui::PushID("pause_overlay_play");
        bool centerHovered = false;
        bool centerClicked = ImGui::InvisibleButton("##play", ImVec2(circleRadius * 2, circleRadius * 2));
        centerHovered = ImGui::IsItemHovered();
        ImGui::PopID();
        
        ImU32 centerCircleColor = centerHovered ? IM_COL32(229, 9, 20, 200) : IM_COL32(0, 0, 0, 160);
        ImU32 centerIconColor = centerHovered ? IM_COL32(255, 255, 255, 255) : IM_COL32(255, 255, 255, 220);
        
        pauseDrawList->AddCircleFilled(center, circleRadius, centerCircleColor, 32);
        pauseDrawList->AddCircle(center, circleRadius, IM_COL32(255, 255, 255, 180), 32, 3.0f);
        DrawPlayIcon(pauseDrawList, center, iconSize, centerIconColor);
        
        if (centerClicked) {
            if (!playButtonClicked) {
                playButtonClicked = true;
                playButtonClickTime = ImGui::GetTime();
                state.isPlaying = true;
                state.ignoreNextClick = true;  // Prevent video surface button from toggling it back
                
                // Resume playback
                if (state.decoder) {
                    state.decoder->play();
                }
                if (state.audioOutput) {
                    state.audioOutput->play();
                }
            }
        }
        
        // Right: Forward 5s button
        ImVec2 rightCenter = ImVec2(center.x + spacing, center.y);
        ImGui::SetCursorScreenPos(ImVec2(rightCenter.x - circleRadius, rightCenter.y - circleRadius));
        ImGui::PushID("pause_overlay_forward");
        bool rightHovered = false;
        bool rightClicked = ImGui::InvisibleButton("##forward", ImVec2(circleRadius * 2, circleRadius * 2));
        rightHovered = ImGui::IsItemHovered();
        ImGui::PopID();
        
        ImU32 rightCircleColor = rightHovered ? IM_COL32(229, 9, 20, 200) : IM_COL32(0, 0, 0, 160);
        ImU32 rightIconColor = rightHovered ? IM_COL32(255, 255, 255, 255) : IM_COL32(255, 255, 255, 220);
        
        pauseDrawList->AddCircleFilled(rightCenter, circleRadius, rightCircleColor, 32);
        pauseDrawList->AddCircle(rightCenter, circleRadius, IM_COL32(255, 255, 255, 180), 32, 3.0f);
        DrawSkipIcon(pauseDrawList, rightCenter, iconSize, true, rightIconColor);
        
        if (rightClicked && state.decoder) {
            double currentTime = ImGui::GetTime();
            
            // Check if this is within 1 second of last tap (accumulate)
            if (currentTime - state.lastSkipForwardTime < 1.0) {
                state.accumulatedSkipForwardSeconds += 5;
            } else {
                state.accumulatedSkipForwardSeconds = 5;  // Reset accumulation
            }
            state.lastSkipForwardTime = currentTime;
            
            state.currentTime = fminf(state.currentTime + 5.0f, state.duration);
            
            // Clear pending frame BEFORE seek
            if (state.pendingFrame) {
                delete state.pendingFrame;
                state.pendingFrame = nullptr;
            }
            
            // Perform the seek first
            state.decoder->seek(state.currentTime);
            state.justSeeked = true;
            state.videoStartTime = 0.0;
            
            // IMPORTANT: Pause AFTER seek (seek resumes decoder thread)
            state.isPlaying = false;
            state.ignoreNextClick = true;  // Prevent video surface button from toggling it back
            
            if (state.decoder) {
                state.decoder->pause();
            }
            
            if (state.audioOutput) {
                state.audioOutput->pause();
            }
            
            // Reset audio clock
            if (state.audioOutput) {
                state.audioOutput->clearQueue();
                state.audioOutput->setAudioClock(state.currentTime);
            }
            state.lastVideoFramePTS = state.currentTime;
            
            // Trigger accumulation animation
            state.showSkipForwardAccumulation = true;
            state.skipForwardAnimTimer = 1.0f;  // 1 second animation
            // Keep video paused - don't start playback
        }
    }
    
    // Netflix-style accumulating seek animations
    // Skip backward accumulation animation
    if (state.showSkipBackAccumulation) {
        state.skipBackAnimTimer -= io.DeltaTime;
        if (state.skipBackAnimTimer <= 0.0f) {
            state.showSkipBackAccumulation = false;
            state.accumulatedSkipBackSeconds = 0;
        } else {
            ImDrawList* animDrawList = ImGui::GetWindowDrawList();
            // Use screen center for animation, move up to avoid button overlap
            ImVec2 screenCenter = ImVec2(io.DisplaySize.x * 0.5f, io.DisplaySize.y * 0.5f - 120.0f);
            ImVec2 buttonCenter = screenCenter;
            
            // Animation timeline (normalized 0 to 1, where 1 is start)
            float t = state.skipBackAnimTimer;
            
            // Arrow rotation animation (0.0-0.2s = 0.8-1.0 normalized)
            float arrowRotation = 0.0f;
            if (t > 0.8f) {
                float phase = (t - 0.8f) / 0.2f;  // 0 to 1
                // Rotate 20 degrees and back
                arrowRotation = sinf(phase * 3.14159f) * 20.0f * (3.14159f / 180.0f);
            }
            
            // Background pulse animation (0.0-0.2s = 0.8-1.0 normalized)
            float bgOpacity = 0.0f;
            if (t > 0.8f) {
                float phase = (t - 0.8f) / 0.2f;
                bgOpacity = sinf(phase * 3.14159f) * 0.3f;
            }
            
            // Draw pulsing background
            if (bgOpacity > 0.0f) {
                animDrawList->AddCircleFilled(buttonCenter, state.controlButtonSize * 0.6f,
                    IM_COL32(229, 9, 20, (int)(255 * bgOpacity)), 32);
            }
            
            // Draw rotated arrow
            animDrawList->AddCircleFilled(buttonCenter, state.controlButtonSize * 0.4f,
                IM_COL32(20, 20, 20, 200), 32);
            // Note: ImGui doesn't support rotation easily, so we'll use color pulse instead
            ImU32 arrowColor = IM_COL32(229, 9, 20, 255);
            DrawSkipIcon(animDrawList, buttonCenter, 18.0f, false, arrowColor);
            
            // Duration label (\"5s\") - fades out at start (0-0.1s), fades in at end (0.1-0s = 0.9-1.0 normalized)
            float durationAlpha = 1.0f;
            if (t > 0.9f) {
                durationAlpha = 1.0f - ((t - 0.9f) / 0.1f);  // Fade out
            } else if (t < 0.1f) {
                durationAlpha = t / 0.1f;  // Fade in
            } else {
                durationAlpha = 0.0f;  // Hidden
            }
            
            if (durationAlpha > 0.0f) {
                const char* durationText = "5s";
                ImVec2 textSize = ImGui::CalcTextSize(durationText);
                ImVec2 textPos = ImVec2(buttonCenter.x - textSize.x * 0.5f, buttonCenter.y + state.controlButtonSize * 0.7f);
                animDrawList->AddText(ImGui::GetFont(), 14.0f, textPos,
                    IM_COL32(255, 255, 255, (int)(255 * durationAlpha)), durationText);
            }
            
            // Accumulation label - fades in (0.9-1.0), moves out (0.5-1.0), fades out (0-0.45)
            float accumAlpha = 0.0f;
            float accumOffset = 0.0f;
            
            if (t > 0.9f) {
                // Fade in phase (0.9-1.0s)
                accumAlpha = 1.0f - ((t - 0.9f) / 0.1f);
                accumOffset = 0.0f;
            } else if (t > 0.5f) {
                // Moving out phase (0.5-0.9s)
                accumAlpha = 1.0f;
                float movePhase = (0.9f - t) / 0.4f;  // 0 to 1
                // Custom easing curve (ease out)
                movePhase = 1.0f - powf(1.0f - movePhase, 3.0f);
                accumOffset = movePhase * 80.0f;  // Move 80px to the left
            } else if (t > 0.05f) {
                // At final position
                accumAlpha = 1.0f;
                accumOffset = 80.0f;
            } else {
                // Fade out phase (0-0.05s)
                accumAlpha = t / 0.05f;
                accumOffset = 80.0f;
            }
            
            if (accumAlpha > 0.0f) {
                char accumText[16];
                snprintf(accumText, sizeof(accumText), "-%ds", state.accumulatedSkipBackSeconds);
                ImVec2 accumTextSize = ImGui::CalcTextSize(accumText);
                ImVec2 accumPos = ImVec2(
                    buttonCenter.x - accumOffset - accumTextSize.x * 0.5f,
                    buttonCenter.y - accumTextSize.y * 0.5f
                );
                animDrawList->AddText(ImGui::GetFont(), 24.0f, accumPos,
                    IM_COL32(255, 255, 255, (int)(255 * accumAlpha)), accumText);
            }
        }
    }
    
    // Skip forward accumulation animation
    if (state.showSkipForwardAccumulation) {
        state.skipForwardAnimTimer -= io.DeltaTime;
        if (state.skipForwardAnimTimer <= 0.0f) {
            state.showSkipForwardAccumulation = false;
            state.accumulatedSkipForwardSeconds = 0;
        } else {
            ImDrawList* animDrawList = ImGui::GetWindowDrawList();
            // Use screen center for animation, move up to avoid button overlap
            ImVec2 screenCenter = ImVec2(io.DisplaySize.x * 0.5f, io.DisplaySize.y * 0.5f - 120.0f);
            ImVec2 buttonCenter = screenCenter;
            
            // Animation timeline (normalized 0 to 1, where 1 is start)
            float t = state.skipForwardAnimTimer;
            
            // Arrow rotation animation (0.0-0.2s = 0.8-1.0 normalized)
            float arrowRotation = 0.0f;
            if (t > 0.8f) {
                float phase = (t - 0.8f) / 0.2f;  // 0 to 1
                arrowRotation = sinf(phase * 3.14159f) * 20.0f * (3.14159f / 180.0f);
            }
            
            // Background pulse animation (0.0-0.2s = 0.8-1.0 normalized)
            float bgOpacity = 0.0f;
            if (t > 0.8f) {
                float phase = (t - 0.8f) / 0.2f;
                bgOpacity = sinf(phase * 3.14159f) * 0.3f;
            }
            
            // Draw pulsing background
            if (bgOpacity > 0.0f) {
                animDrawList->AddCircleFilled(buttonCenter, state.controlButtonSize * 0.6f,
                    IM_COL32(229, 9, 20, (int)(255 * bgOpacity)), 32);
            }
            
            // Draw rotated arrow
            animDrawList->AddCircleFilled(buttonCenter, state.controlButtonSize * 0.4f,
                IM_COL32(20, 20, 20, 200), 32);
            ImU32 arrowColor = IM_COL32(229, 9, 20, 255);
            DrawSkipIcon(animDrawList, buttonCenter, 18.0f, true, arrowColor);
            
            // Duration label ("5s")
            float durationAlpha = 1.0f;
            if (t > 0.9f) {
                durationAlpha = 1.0f - ((t - 0.9f) / 0.1f);  // Fade out
            } else if (t < 0.1f) {
                durationAlpha = t / 0.1f;  // Fade in
            } else {
                durationAlpha = 0.0f;  // Hidden
            }
            
            if (durationAlpha > 0.0f) {
                const char* durationText = "5s";
                ImVec2 textSize = ImGui::CalcTextSize(durationText);
                ImVec2 textPos = ImVec2(buttonCenter.x - textSize.x * 0.5f, buttonCenter.y + state.controlButtonSize * 0.7f);
                animDrawList->AddText(ImGui::GetFont(), 14.0f, textPos,
                    IM_COL32(255, 255, 255, (int)(255 * durationAlpha)), durationText);
            }
            
            // Accumulation label
            float accumAlpha = 0.0f;
            float accumOffset = 0.0f;
            
            if (t > 0.9f) {
                accumAlpha = 1.0f - ((t - 0.9f) / 0.1f);
                accumOffset = 0.0f;
            } else if (t > 0.5f) {
                accumAlpha = 1.0f;
                float movePhase = (0.9f - t) / 0.4f;
                movePhase = 1.0f - powf(1.0f - movePhase, 3.0f);
                accumOffset = movePhase * 80.0f;  // Move 80px to the right
            } else if (t > 0.05f) {
                accumAlpha = 1.0f;
                accumOffset = 80.0f;
            } else {
                accumAlpha = t / 0.05f;
                accumOffset = 80.0f;
            }
            
            if (accumAlpha > 0.0f) {
                char accumText[16];
                snprintf(accumText, sizeof(accumText), "+%ds", state.accumulatedSkipForwardSeconds);
                ImVec2 accumTextSize = ImGui::CalcTextSize(accumText);
                ImVec2 accumPos = ImVec2(
                    buttonCenter.x + accumOffset - accumTextSize.x * 0.5f,
                    buttonCenter.y - accumTextSize.y * 0.5f
                );
                animDrawList->AddText(ImGui::GetFont(), 24.0f, accumPos,
                    IM_COL32(255, 255, 255, (int)(255 * accumAlpha)), accumText);
            }
        }
    }
    
    // 2x Speed indicator (when holding mouse on video)
    if (state.show2xSpeedIndicator) {
        ImVec2 center = ImVec2(screenSize.x * 0.5f, screenSize.y * 0.5f);
        ImDrawList* speedDrawList = ImGui::GetWindowDrawList();
        
        // Semi-transparent background
        float bgWidth = 180.0f;
        float bgHeight = 60.0f;
        ImVec2 bgMin = ImVec2(center.x - bgWidth * 0.5f, center.y - bgHeight * 0.5f);
        ImVec2 bgMax = ImVec2(center.x + bgWidth * 0.5f, center.y + bgHeight * 0.5f);
        speedDrawList->AddRectFilled(bgMin, bgMax, IM_COL32(0, 0, 0, 180), 8.0f);
        speedDrawList->AddRect(bgMin, bgMax, IM_COL32(255, 255, 255, 200), 8.0f, 0, 2.0f);
        
        // "2x" text
        const char* speedText = "2.0x";
        ImVec2 textSize = ImGui::CalcTextSize(speedText);
        speedDrawList->AddText(ImGui::GetFont(), 32.0f,
            ImVec2(center.x - textSize.x, center.y - 16),
            IM_COL32(255, 255, 255, 255), speedText);
    }
    
    ImGui::End();
}

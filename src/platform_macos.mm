#ifdef __APPLE__

#import "platform.h"
#import <Cocoa/Cocoa.h>
#import <Metal/Metal.h>

// Metal device (shared)
static id<MTLDevice> g_metalDevice = nil;

bool InitializePlatform() {
    g_metalDevice = MTLCreateSystemDefaultDevice();
    return g_metalDevice != nil;
}

void ShutdownPlatform() {
    g_metalDevice = nil;
}

PlatformTexture CreateVideoTexture(int width, int height) {
    if (!g_metalDevice) {
        g_metalDevice = MTLCreateSystemDefaultDevice();
    }
    
    MTLTextureDescriptor* textureDescriptor = [MTLTextureDescriptor
        texture2DDescriptorWithPixelFormat:MTLPixelFormatRGBA8Unorm
        width:width
        height:height
        mipmapped:NO];
    textureDescriptor.usage = MTLTextureUsageShaderRead;
    
    return [g_metalDevice newTextureWithDescriptor:textureDescriptor];
}

void UpdateVideoTexture(PlatformTexture texture, uint8_t* rgbaData, int width, int height) {
    if (!texture || !rgbaData) return;
    
    MTLRegion region = MTLRegionMake2D(0, 0, width, height);
    [texture replaceRegion:region
              mipmapLevel:0
                withBytes:rgbaData
              bytesPerRow:width * 4];
}

void DestroyVideoTexture(PlatformTexture texture) {
    // ARC will handle cleanup
    (void)texture;
}

std::string OpenFileDialog() {
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

void ToggleFullscreen(PlatformWindow window, bool& isFullscreen) {
    if (window) {
        [window toggleFullScreen:nil];
        isFullscreen = !isFullscreen;
    }
}

#endif // __APPLE__

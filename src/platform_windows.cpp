#ifdef _WIN32

#include "platform.h"
#include <d3d11.h>
#include <windows.h>
#include <shobjidl.h>
#include <comdef.h>
#include <iostream>

// Global D3D11 device and context
static ID3D11Device* g_pd3dDevice = nullptr;
static ID3D11DeviceContext* g_pd3dDeviceContext = nullptr;
static IDXGISwapChain* g_pSwapChain = nullptr;
static ID3D11RenderTargetView* g_mainRenderTargetView = nullptr;

ID3D11Device* GetD3D11Device() {
    return g_pd3dDevice;
}

ID3D11DeviceContext* GetD3D11DeviceContext() {
    return g_pd3dDeviceContext;
}

bool InitializePlatform() {
    // D3D11 device is created by ImGui in main, so just return true here
    return true;
}

void ShutdownPlatform() {
    if (g_mainRenderTargetView) { g_mainRenderTargetView->Release(); g_mainRenderTargetView = nullptr; }
    if (g_pSwapChain) { g_pSwapChain->Release(); g_pSwapChain = nullptr; }
    if (g_pd3dDeviceContext) { g_pd3dDeviceContext->Release(); g_pd3dDeviceContext = nullptr; }
    if (g_pd3dDevice) { g_pd3dDevice->Release(); g_pd3dDevice = nullptr; }
}

// Set the D3D11 device (called from main after ImGui creates it)
void SetD3D11Device(ID3D11Device* device, ID3D11DeviceContext* context, IDXGISwapChain* swapChain, ID3D11RenderTargetView* rtv) {
    g_pd3dDevice = device;
    g_pd3dDeviceContext = context;
    g_pSwapChain = swapChain;
    g_mainRenderTargetView = rtv;
}

PlatformTexture CreateVideoTexture(int width, int height) {
    if (!g_pd3dDevice) return nullptr;
    
    // Create texture
    D3D11_TEXTURE2D_DESC desc = {};
    desc.Width = width;
    desc.Height = height;
    desc.MipLevels = 1;
    desc.ArraySize = 1;
    desc.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    desc.SampleDesc.Count = 1;
    desc.Usage = D3D11_USAGE_DEFAULT;
    desc.BindFlags = D3D11_BIND_SHADER_RESOURCE;
    desc.CPUAccessFlags = 0;
    
    ID3D11Texture2D* pTexture = nullptr;
    HRESULT hr = g_pd3dDevice->CreateTexture2D(&desc, nullptr, &pTexture);
    if (FAILED(hr)) return nullptr;
    
    // Create shader resource view
    D3D11_SHADER_RESOURCE_VIEW_DESC srvDesc = {};
    srvDesc.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
    srvDesc.ViewDimension = D3D11_SRV_DIMENSION_TEXTURE2D;
    srvDesc.Texture2D.MipLevels = desc.MipLevels;
    srvDesc.Texture2D.MostDetailedMip = 0;
    
    ID3D11ShaderResourceView* pSRV = nullptr;
    hr = g_pd3dDevice->CreateShaderResourceView(pTexture, &srvDesc, &pSRV);
    pTexture->Release();
    
    if (FAILED(hr)) return nullptr;
    return pSRV;
}

void UpdateVideoTexture(PlatformTexture srv, uint8_t* rgbaData, int width, int height) {
    if (!srv || !rgbaData || !g_pd3dDeviceContext) return;
    
    // Get the texture from the SRV
    ID3D11Resource* pResource = nullptr;
    srv->GetResource(&pResource);
    
    if (pResource) {
        g_pd3dDeviceContext->UpdateSubresource(pResource, 0, nullptr, rgbaData, width * 4, 0);
        pResource->Release();
    }
}

void DestroyVideoTexture(PlatformTexture srv) {
    if (srv) {
        srv->Release();
    }
}

std::string OpenFileDialog() {
    std::string result;
    
    // Initialize COM
    HRESULT hr = CoInitializeEx(NULL, COINIT_APARTMENTTHREADED | COINIT_DISABLE_OLE1DDE);
    if (FAILED(hr) && hr != RPC_E_CHANGED_MODE) {
        return result;
    }
    
    IFileOpenDialog* pFileOpen = nullptr;
    
    // Create the FileOpenDialog object
    hr = CoCreateInstance(CLSID_FileOpenDialog, NULL, CLSCTX_ALL,
                          IID_IFileOpenDialog, reinterpret_cast<void**>(&pFileOpen));
    
    if (SUCCEEDED(hr)) {
        // Set file type filters
        COMDLG_FILTERSPEC rgSpec[] = {
            { L"Video Files", L"*.mp4;*.mov;*.ts;*.mpeg;*.mpg;*.wmv;*.avi;*.mkv" },
            { L"Audio Files", L"*.mp3;*.wav" },
            { L"All Files", L"*.*" }
        };
        pFileOpen->SetFileTypes(ARRAYSIZE(rgSpec), rgSpec);
        pFileOpen->SetTitle(L"Open Media File");
        
        // Show the dialog
        hr = pFileOpen->Show(NULL);
        
        if (SUCCEEDED(hr)) {
            IShellItem* pItem = nullptr;
            hr = pFileOpen->GetResult(&pItem);
            if (SUCCEEDED(hr)) {
                PWSTR pszFilePath = nullptr;
                hr = pItem->GetDisplayName(SIGDN_FILESYSPATH, &pszFilePath);
                
                if (SUCCEEDED(hr)) {
                    // Convert wide string to std::string
                    int size_needed = WideCharToMultiByte(CP_UTF8, 0, pszFilePath, -1, NULL, 0, NULL, NULL);
                    if (size_needed > 0) {
                        char* buffer = new char[size_needed];
                        WideCharToMultiByte(CP_UTF8, 0, pszFilePath, -1, buffer, size_needed, NULL, NULL);
                        result = std::string(buffer);
                        delete[] buffer;
                    }
                    CoTaskMemFree(pszFilePath);
                }
                pItem->Release();
            }
        }
        pFileOpen->Release();
    }
    
    CoUninitialize();
    return result;
}

void ToggleFullscreen(PlatformWindow hwnd, bool& isFullscreen) {
    if (!hwnd) return;
    
    static WINDOWPLACEMENT g_wpPrev = { sizeof(g_wpPrev) };
    
    DWORD dwStyle = GetWindowLong(hwnd, GWL_STYLE);
    if (!isFullscreen) {
        // Going to fullscreen
        MONITORINFO mi = { sizeof(mi) };
        if (GetWindowPlacement(hwnd, &g_wpPrev) &&
            GetMonitorInfo(MonitorFromWindow(hwnd, MONITOR_DEFAULTTOPRIMARY), &mi)) {
            SetWindowLong(hwnd, GWL_STYLE, dwStyle & ~WS_OVERLAPPEDWINDOW);
            SetWindowPos(hwnd, HWND_TOP,
                         mi.rcMonitor.left, mi.rcMonitor.top,
                         mi.rcMonitor.right - mi.rcMonitor.left,
                         mi.rcMonitor.bottom - mi.rcMonitor.top,
                         SWP_NOOWNERZORDER | SWP_FRAMECHANGED);
        }
    } else {
        // Exiting fullscreen
        SetWindowLong(hwnd, GWL_STYLE, dwStyle | WS_OVERLAPPEDWINDOW);
        SetWindowPlacement(hwnd, &g_wpPrev);
        SetWindowPos(hwnd, NULL, 0, 0, 0, 0,
                     SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER |
                     SWP_NOOWNERZORDER | SWP_FRAMECHANGED);
    }
    isFullscreen = !isFullscreen;
}

#endif // _WIN32

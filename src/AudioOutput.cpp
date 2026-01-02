#include "AudioOutput.h"
#include "VideoDecoder.h"
#include <iostream>

AudioOutput::AudioOutput()
    : m_sampleRate(0)
    , m_channels(0)
    , m_volume(1.0f)
    , m_playbackRate(1.0f)
    , m_playing(false)
    , m_audioClock(0.0)
    , m_lastClockUpdate(0.0)
#ifdef __APPLE__
    , m_audioQueue(nullptr)
#endif
#ifdef _WIN32
    , m_deviceEnumerator(nullptr)
    , m_device(nullptr)
    , m_audioClient(nullptr)
    , m_renderClient(nullptr)
    , m_audioEvent(nullptr)
    , m_stopAudioThread(false)
#endif
{
#ifdef __APPLE__
    for (int i = 0; i < NUM_BUFFERS; i++) {
        m_buffers[i] = nullptr;
    }
#endif
}

AudioOutput::~AudioOutput() {
    shutdown();
}

bool AudioOutput::initialize(int sampleRate, int channels) {
    m_sampleRate = sampleRate;
    m_channels = channels;
    
#ifdef __APPLE__
    // Setup audio format
    AudioStreamBasicDescription format = {};
    format.mSampleRate = sampleRate;
    format.mFormatID = kAudioFormatLinearPCM;
    format.mFormatFlags = kLinearPCMFormatFlagIsFloat | kLinearPCMFormatFlagIsPacked;
    format.mBitsPerChannel = 32;
    format.mChannelsPerFrame = channels;
    format.mBytesPerFrame = channels * sizeof(float);
    format.mFramesPerPacket = 1;
    format.mBytesPerPacket = format.mBytesPerFrame;
    
    // Create audio queue
    OSStatus status = AudioQueueNewOutput(
        &format,
        audioCallback,
        this,
        nullptr,
        nullptr,
        0,
        &m_audioQueue
    );
    
    if (status != noErr) {
        std::cerr << "Failed to create audio queue: " << status << std::endl;
        return false;
    }
    
    // Allocate buffers
    int bufferSize = sampleRate * channels * sizeof(float) / 10; // 100ms buffers
    for (int i = 0; i < NUM_BUFFERS; i++) {
        status = AudioQueueAllocateBuffer(m_audioQueue, bufferSize, &m_buffers[i]);
        if (status != noErr) {
            std::cerr << "Failed to allocate audio buffer: " << status << std::endl;
            shutdown();
            return false;
        }
        
        // Prime the buffers with silence
        m_buffers[i]->mAudioDataByteSize = bufferSize;
        memset(m_buffers[i]->mAudioData, 0, bufferSize);
        AudioQueueEnqueueBuffer(m_audioQueue, m_buffers[i], 0, nullptr);
    }
    
    std::cout << "Audio initialized: " << sampleRate << "Hz, " << channels << " channels" << std::endl;
    
#elif defined(_WIN32)
    // Windows WASAPI implementation
    HRESULT hr = CoInitializeEx(nullptr, COINIT_MULTITHREADED);
    if (FAILED(hr) && hr != RPC_E_CHANGED_MODE) {
        std::cerr << "Failed to initialize COM: " << std::hex << hr << std::endl;
        return false;
    }
    
    // Create device enumerator
    hr = CoCreateInstance(__uuidof(MMDeviceEnumerator), nullptr, CLSCTX_ALL,
                          __uuidof(IMMDeviceEnumerator), (void**)&m_deviceEnumerator);
    if (FAILED(hr)) {
        std::cerr << "Failed to create device enumerator: " << std::hex << hr << std::endl;
        return false;
    }
    
    // Get default audio endpoint
    hr = m_deviceEnumerator->GetDefaultAudioEndpoint(eRender, eConsole, &m_device);
    if (FAILED(hr)) {
        std::cerr << "Failed to get default audio endpoint: " << std::hex << hr << std::endl;
        return false;
    }
    
    // Activate audio client
    hr = m_device->Activate(__uuidof(IAudioClient), CLSCTX_ALL, nullptr, (void**)&m_audioClient);
    if (FAILED(hr)) {
        std::cerr << "Failed to activate audio client: " << std::hex << hr << std::endl;
        return false;
    }
    
    // Set up audio format
    WAVEFORMATEX waveFormat = {};
    waveFormat.wFormatTag = WAVE_FORMAT_IEEE_FLOAT;
    waveFormat.nChannels = channels;
    waveFormat.nSamplesPerSec = sampleRate;
    waveFormat.wBitsPerSample = 32;
    waveFormat.nBlockAlign = (waveFormat.nChannels * waveFormat.wBitsPerSample) / 8;
    waveFormat.nAvgBytesPerSec = waveFormat.nSamplesPerSec * waveFormat.nBlockAlign;
    waveFormat.cbSize = 0;
    
    // Initialize audio client
    REFERENCE_TIME bufferDuration = 10000000; // 1 second in 100-nanosecond units
    hr = m_audioClient->Initialize(AUDCLNT_SHAREMODE_SHARED,
                                   AUDCLNT_STREAMFLAGS_EVENTCALLBACK,
                                   bufferDuration, 0, &waveFormat, nullptr);
    if (FAILED(hr)) {
        std::cerr << "Failed to initialize audio client: " << std::hex << hr << std::endl;
        return false;
    }
    
    // Create event for audio callback
    m_audioEvent = CreateEvent(nullptr, FALSE, FALSE, nullptr);
    if (!m_audioEvent) {
        std::cerr << "Failed to create audio event" << std::endl;
        return false;
    }
    
    hr = m_audioClient->SetEventHandle(m_audioEvent);
    if (FAILED(hr)) {
        std::cerr << "Failed to set event handle: " << std::hex << hr << std::endl;
        return false;
    }
    
    // Get render client
    hr = m_audioClient->GetService(__uuidof(IAudioRenderClient), (void**)&m_renderClient);
    if (FAILED(hr)) {
        std::cerr << "Failed to get render client: " << std::hex << hr << std::endl;
        return false;
    }
    
    std::cout << "WASAPI Audio initialized: " << sampleRate << "Hz, " << channels << " channels" << std::endl;
#endif
    
    return true;
}

void AudioOutput::shutdown() {
#ifdef __APPLE__
    if (m_audioQueue) {
        AudioQueueStop(m_audioQueue, true);
        AudioQueueDispose(m_audioQueue, true);
        m_audioQueue = nullptr;
    }
#elif defined(_WIN32)
    // Stop audio thread
    if (m_audioThread.joinable()) {
        m_stopAudioThread = true;
        if (m_audioEvent) {
            SetEvent(m_audioEvent);
        }
        m_audioThread.join();
    }
    
    // Stop audio client
    if (m_audioClient) {
        m_audioClient->Stop();
    }
    
    // Release COM interfaces
    if (m_renderClient) {
        m_renderClient->Release();
        m_renderClient = nullptr;
    }
    if (m_audioClient) {
        m_audioClient->Release();
        m_audioClient = nullptr;
    }
    if (m_device) {
        m_device->Release();
        m_device = nullptr;
    }
    if (m_deviceEnumerator) {
        m_deviceEnumerator->Release();
        m_deviceEnumerator = nullptr;
    }
    if (m_audioEvent) {
        CloseHandle(m_audioEvent);
        m_audioEvent = nullptr;
    }
#endif
    
    // Clear queue
    std::lock_guard<std::mutex> lock(m_queueMutex);
    while (!m_frameQueue.empty()) {
        delete m_frameQueue.front();
        m_frameQueue.pop();
    }
}

void AudioOutput::play() {
#ifdef __APPLE__
    if (m_audioQueue && !m_playing) {
        OSStatus status = AudioQueueStart(m_audioQueue, nullptr);
        if (status == noErr) {
            m_playing = true;
        }
    }
#elif defined(_WIN32)
    if (m_audioClient && !m_playing) {
        // Start audio client
        HRESULT hr = m_audioClient->Start();
        if (SUCCEEDED(hr)) {
            m_playing = true;
            
            // Start audio rendering thread
            if (!m_audioThread.joinable()) {
                m_stopAudioThread = false;
                m_audioThread = std::thread(&AudioOutput::audioThreadFunc, this);
            }
        } else {
            std::cerr << "Failed to start audio client: " << std::hex << hr << std::endl;
        }
    }
#endif
}

void AudioOutput::pause() {
#ifdef __APPLE__
    if (m_audioQueue && m_playing) {
        AudioQueuePause(m_audioQueue);
        m_playing = false;
    }
#elif defined(_WIN32)
    if (m_audioClient && m_playing) {
        m_audioClient->Stop();
        m_playing = false;
    }
#endif
}

void AudioOutput::setVolume(float volume) {
    m_volume = std::max(0.0f, std::min(1.0f, volume));
    
#ifdef __APPLE__
    if (m_audioQueue) {
        AudioQueueSetParameter(m_audioQueue, kAudioQueueParam_Volume, m_volume);
    }
#endif
}

void AudioOutput::setPlaybackRate(float rate) {
    float oldRate = m_playbackRate;
    m_playbackRate = std::max(0.5f, std::min(2.0f, rate));
    std::cout << "[AUDIO] setPlaybackRate called: " << rate << " -> clamped to: " << m_playbackRate << std::endl;
    
#ifdef __APPLE__
    if (m_audioQueue) {
        std::cout << "[AUDIO] Setting CoreAudio kAudioQueueParam_PlayRate to: " << m_playbackRate << std::endl;
        OSStatus status = AudioQueueSetParameter(m_audioQueue, kAudioQueueParam_PlayRate, m_playbackRate);
        if (status == noErr) {
            std::cout << "[AUDIO] CoreAudio playback rate set successfully" << std::endl;
        } else {
            std::cout << "[AUDIO] ERROR: Failed to set CoreAudio playback rate, status=" << status << std::endl;
        }
    } else {
        std::cout << "[AUDIO] WARNING: m_audioQueue is null, cannot set playback rate" << std::endl;
    }
#endif
}

void AudioOutput::pushAudioFrame(AudioFrame* frame) {
    std::lock_guard<std::mutex> lock(m_queueMutex);
    m_frameQueue.push(frame);
}

void AudioOutput::clearQueue() {
    std::lock_guard<std::mutex> lock(m_queueMutex);
    while (!m_frameQueue.empty()) {
        delete m_frameQueue.front();
        m_frameQueue.pop();
    }
}

#ifdef __APPLE__
void AudioOutput::audioCallback(void* userData, AudioQueueRef queue, AudioQueueBufferRef buffer) {
    AudioOutput* output = static_cast<AudioOutput*>(userData);
    
    std::lock_guard<std::mutex> lock(output->m_queueMutex);
    
    if (output->m_frameQueue.empty()) {
        // No audio data, output silence
        memset(buffer->mAudioData, 0, buffer->mAudioDataBytesCapacity);
        buffer->mAudioDataByteSize = buffer->mAudioDataBytesCapacity;
        
        // Advance audio clock based on buffer duration (time-based advancement)
        // This prevents audio clock from freezing when queue is empty
        if (output->m_playing && output->m_sampleRate > 0) {
            int numSamples = buffer->mAudioDataBytesCapacity / (output->m_channels * sizeof(float));
            double bufferDuration = (double)numSamples / output->m_sampleRate;
            output->m_audioClock = output->m_audioClock + bufferDuration;
        }
    } else {
        // Get audio frame
        AudioFrame* frame = output->m_frameQueue.front();
        output->m_frameQueue.pop();
        
        static int audioLogCounter = 0;
        bool shouldLog = (audioLogCounter++ % 100 == 0);  // Log every 100th audio frame
        
        // Update audio clock with frame PTS, scaled by playback rate
        // When playing at 2x, the audio plays faster but frame PTS is at original speed
        // We need to advance the clock proportionally faster
        if (output->m_playbackRate > 0.0f) {
            double oldClock = output->m_audioClock;
            double clockAdvance = frame->pts - output->m_lastClockUpdate;
            if (clockAdvance > 0 && output->m_lastClockUpdate > 0) {
                // Advance clock by the scaled amount
                output->m_audioClock = output->m_audioClock + (clockAdvance * output->m_playbackRate);
                if (shouldLog) {
                    std::cout << "[AUDIO CALLBACK] playbackRate=" << output->m_playbackRate 
                              << " framePTS=" << frame->pts
                              << " clockAdvance=" << clockAdvance
                              << " scaledAdvance=" << (clockAdvance * output->m_playbackRate)
                              << " oldClock=" << oldClock
                              << " newClock=" << output->m_audioClock << std::endl;
                }
            } else {
                // First frame or discontinuity - set directly
                output->m_audioClock = frame->pts * output->m_playbackRate;
                if (shouldLog) {
                    std::cout << "[AUDIO CALLBACK] First frame or discontinuity, setting clock to: " << output->m_audioClock << std::endl;
                }
            }
            output->m_lastClockUpdate = frame->pts;
        } else {
            output->m_audioClock = frame->pts;
            output->m_lastClockUpdate = frame->pts;
        }
        
        // Copy audio data
        int copySize = std::min((int)frame->size, (int)buffer->mAudioDataBytesCapacity);
        memcpy(buffer->mAudioData, frame->data, copySize);
        buffer->mAudioDataByteSize = copySize;
        
        delete frame;
    }
    
    // Re-enqueue buffer
    AudioQueueEnqueueBuffer(queue, buffer, 0, nullptr);
}
#endif

#ifdef _WIN32
void AudioOutput::audioThreadFunc() {
    // Get buffer size
    UINT32 bufferFrameCount;
    HRESULT hr = m_audioClient->GetBufferSize(&bufferFrameCount);
    if (FAILED(hr)) {
        std::cerr << "Failed to get buffer size: " << std::hex << hr << std::endl;
        return;
    }
    
    while (!m_stopAudioThread) {
        // Wait for buffer event
        DWORD waitResult = WaitForSingleObject(m_audioEvent, 100);
        
        if (waitResult != WAIT_OBJECT_0) {
            continue;
        }
        
        if (m_stopAudioThread) break;
        
        // Get current padding (how much buffer is filled)
        UINT32 numFramesPadding;
        hr = m_audioClient->GetCurrentPadding(&numFramesPadding);
        if (FAILED(hr)) continue;
        
        // Calculate available frames
        UINT32 numFramesAvailable = bufferFrameCount - numFramesPadding;
        
        if (numFramesAvailable == 0) continue;
        
        // Get buffer
        BYTE* data;
        hr = m_renderClient->GetBuffer(numFramesAvailable, &data);
        if (FAILED(hr)) continue;
        
        // Fill buffer with audio data
        UINT32 framesFilled = 0;
        float* floatBuffer = (float*)data;
        
        while (framesFilled < numFramesAvailable) {
            AudioFrame* frame = nullptr;
            
            {
                std::lock_guard<std::mutex> lock(m_queueMutex);
                if (!m_frameQueue.empty()) {
                    frame = m_frameQueue.front();
                    m_frameQueue.pop();
                }
            }
            
            if (!frame) {
                // No audio data, fill with silence
                UINT32 remainingFrames = numFramesAvailable - framesFilled;
                memset(floatBuffer, 0, remainingFrames * m_channels * sizeof(float));
                framesFilled = numFramesAvailable;
                
                // Advance audio clock based on buffer duration
                if (m_playing) {
                    double bufferDuration = (double)remainingFrames / m_sampleRate;
                    m_audioClock = m_audioClock + bufferDuration;
                }
                break;
            }
            
            // Update audio clock with frame PTS
            m_audioClock = frame->pts;
            m_lastClockUpdate = frame->pts;
            
            // Calculate how many frames we can copy
            UINT32 frameSamples = frame->size / (m_channels * sizeof(float));
            UINT32 framesToCopy = std::min(frameSamples, numFramesAvailable - framesFilled);
            
            // Copy audio data
            memcpy(floatBuffer, frame->data, framesToCopy * m_channels * sizeof(float));
            floatBuffer += framesToCopy * m_channels;
            framesFilled += framesToCopy;
            
            delete frame;
        }
        
        // Release buffer
        hr = m_renderClient->ReleaseBuffer(numFramesAvailable, 0);
        if (FAILED(hr)) {
            std::cerr << "Failed to release buffer: " << std::hex << hr << std::endl;
        }
    }
}
#endif

#include "AudioOutput.h"
#include "VideoDecoder.h"
#include <iostream>
#include <chrono>
#include <iomanip>

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
    , m_flushRequested(false)
    , m_partialFrame(nullptr)
    , m_partialFrameOffset(0)
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
        
        // Try to get the closest supported format
        WAVEFORMATEX* closestMatch = nullptr;
        hr = m_audioClient->IsFormatSupported(AUDCLNT_SHAREMODE_SHARED, &waveFormat, &closestMatch);
        if (closestMatch) {
            std::cout << "[AUDIO INIT] Suggested format: " << closestMatch->nSamplesPerSec << "Hz, " 
                      << closestMatch->nChannels << " channels" << std::endl;
            CoTaskMemFree(closestMatch);
        }
        return false;
    }
    
    // Verify actual format WASAPI negotiated
    WAVEFORMATEX* actualFormat = nullptr;
    hr = m_audioClient->GetMixFormat(&actualFormat);
    if (SUCCEEDED(hr) && actualFormat) {
        CoTaskMemFree(actualFormat);
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
    
    // Clean up partial frame
    if (m_partialFrame) {
        delete m_partialFrame;
        m_partialFrame = nullptr;
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
        // Start audio rendering thread if not already running
        if (!m_audioThread.joinable()) {
            m_stopAudioThread = false;
            m_audioThread = std::thread(&AudioOutput::audioThreadFunc, this);
        }
        
        // Start or restart audio client
        HRESULT hr = m_audioClient->Start();
        if (SUCCEEDED(hr) || hr == AUDCLNT_E_NOT_STOPPED) {
            // AUDCLNT_E_NOT_STOPPED means already playing, which is fine
            m_playing = true;
        } else {
            std::cerr << "[AUDIO] Failed to start audio client: 0x" << std::hex << hr << std::dec << std::endl;
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
    if (m_playing) {
        m_playing = false;
        // Request flush to clear buffered audio immediately
        m_flushRequested.store(true);
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
    
#ifdef __APPLE__
    if (m_audioQueue) {
        OSStatus status = AudioQueueSetParameter(m_audioQueue, kAudioQueueParam_PlayRate, m_playbackRate);
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
            } else {
                // First frame or discontinuity - set directly
                output->m_audioClock = frame->pts * output->m_playbackRate;
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
        
        // If paused, output silence
        if (!m_playing) {
            memset(floatBuffer, 0, numFramesAvailable * m_channels * sizeof(float));
            hr = m_renderClient->ReleaseBuffer(numFramesAvailable, 0);
            continue;
        }
        
        while (framesFilled < numFramesAvailable) {
            AudioFrame* frame = nullptr;
            UINT32 frameOffset = 0;
            
            // Check for partial frame first
            {
                std::lock_guard<std::mutex> lock(m_partialFrameMutex);
                if (m_partialFrame) {
                    // Check if partial frame is stale (seek happened)
                    // If PTS differs from clock by >1s, it's from before a seek
                    if (m_audioClock > 0.001 && fabs(m_partialFrame->pts - m_audioClock) > 1.0) {
                        // Stale partial frame - discard it
                        delete m_partialFrame;
                        m_partialFrame = nullptr;
                        m_partialFrameOffset = 0;
                    } else {
                        frame = m_partialFrame;
                        frameOffset = m_partialFrameOffset;
                        m_partialFrame = nullptr;
                        m_partialFrameOffset = 0;
                    }
                }
            }
            
            // Get new frame from queue if no partial frame
            if (!frame) {
                std::lock_guard<std::mutex> lock(m_queueMutex);
                if (!m_frameQueue.empty()) {
                    frame = m_frameQueue.front();
                    m_frameQueue.pop();
                    frameOffset = 0;
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
            
            // Calculate frame size and available samples from current offset
            UINT32 totalFrameSamples = frame->size / (m_channels * sizeof(float));
            UINT32 availableSamples = totalFrameSamples - frameOffset;
            
            // Detect seek: backward jump OR large forward jump (>0.5s)
            // Normal playback has small forward progression (~0.02s per frame)
            double timeDiff = frame->pts - m_audioClock;
            bool isSeekDetected = (frameOffset == 0) && 
                                  (m_audioClock > 0.001) && 
                                  ((timeDiff < 0) || (timeDiff > 0.5));
            
            if (isSeekDetected) {
                // Seek detected - request flush but DON'T update clock yet
                // Clock will be updated when we start copying new audio after flush
                double oldClock = m_audioClock;
                m_flushRequested.store(true);
                // Clean log format: SEEK POSITION - AUDIO CLOCK POSITION - VIDEO POSITION (no video info here)
                // We'll log this with more complete info when resume happens
                
                // Delete stale frame (decoder will provide fresh frames from new position)
                delete frame;
                
                // Fill with silence and release buffer, then break to exit loop
                memset(floatBuffer, 0, numFramesAvailable * m_channels * sizeof(float));
                break;  // Exit to release buffer at end
            } else if (m_audioClock < 0.001 && frameOffset == 0) {
                // Very first frame - initialize clock
                m_audioClock = frame->pts;
                m_lastClockUpdate = frame->pts;
            }
            
            // If flush is pending, fill silence and wait
            if (m_flushRequested.load()) {
                // Delete frame - it's from old position, decoder will provide fresh frames
                delete frame;
                
                // Fill with silence
                memset(floatBuffer, 0, numFramesAvailable * m_channels * sizeof(float));
                break;  // Exit to release buffer at end
            }
            
            // Log first frame after flush completes
            static bool wasFlushRequested = false;
            static bool logNextFrame = false;
            bool currentFlushState = m_flushRequested.load();
            
            if (currentFlushState && !wasFlushRequested) {
                wasFlushRequested = true;
            } else if (!currentFlushState && wasFlushRequested) {
                logNextFrame = true;
                wasFlushRequested = false;
            }
            
            if (logNextFrame && frameOffset == 0) {
                // First complete frame after flush - synchronize clock to new position
                double oldClock = m_audioClock;
                m_audioClock = frame->pts;
                m_lastClockUpdate = frame->pts;
                std::cout << frame->pts << " - " << m_audioClock << " - N/A" << std::endl;
                logNextFrame = false;
            }
            
            // Calculate how many samples we can copy from this frame
            UINT32 samplesToCopy = std::min(availableSamples, numFramesAvailable - framesFilled);
            
            // Copy audio data from the correct offset
            float* sourceData = (float*)frame->data + (frameOffset * m_channels);
            memcpy(floatBuffer, sourceData, samplesToCopy * m_channels * sizeof(float));
            floatBuffer += samplesToCopy * m_channels;
            framesFilled += samplesToCopy;
            
            // Advance clock by the actual samples written
            double actualDuration = (double)samplesToCopy / m_sampleRate;
            m_audioClock += actualDuration;
            m_lastClockUpdate = frame->pts;
            
            // Check if frame has remaining data
            UINT32 newOffset = frameOffset + samplesToCopy;
            if (newOffset < totalFrameSamples) {
                // Frame has remaining data - save as partial frame
                std::lock_guard<std::mutex> lock(m_partialFrameMutex);
                m_partialFrame = frame;
                m_partialFrameOffset = newOffset;
            } else {
                // Frame fully consumed
                delete frame;
            }
        }
        
        // Release buffer
        hr = m_renderClient->ReleaseBuffer(numFramesAvailable, 0);
        if (FAILED(hr)) {
            std::cerr << "Failed to release buffer: " << std::hex << hr << std::endl;
        }
    }
}

void AudioOutput::checkAndFlushIfNeeded() {
#ifdef _WIN32
    if (!m_flushRequested.load()) {
        return;  // No flush needed
    }
    
    // Lock to prevent multiple simultaneous flushes
    std::lock_guard<std::mutex> lock(m_flushMutex);
    
    // Double-check after acquiring lock
    if (!m_flushRequested.load()) {
        return;
    }
    
    // Stop audio client
    HRESULT hr = m_audioClient->Stop();
    if (FAILED(hr)) {
        m_flushRequested.store(false);
        return;
    }
    
    hr = m_audioClient->Reset();
    if (FAILED(hr)) {
        m_audioClient->Start();  // Try to restart anyway
        m_flushRequested.store(false);
        return;
    }
    
    hr = m_audioClient->Start();
    if (FAILED(hr)) {
        m_flushRequested.store(false);
        return;
    }
    
    // Clear the flush request flag - audio callback will resume normal operation
    m_flushRequested.store(false);
#endif
}
#endif

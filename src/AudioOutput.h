#pragma once

#include <atomic>
#include <queue>
#include <mutex>
#include <thread>

#ifdef __APPLE__
#include <AudioToolbox/AudioToolbox.h>
#endif

#ifdef _WIN32
#define NOMINMAX  // Prevent Windows.h from defining min/max macros
#include <mmdeviceapi.h>
#include <audioclient.h>
#include <comdef.h>
#endif

struct AudioFrame;

class AudioOutput {
public:
    AudioOutput();
    ~AudioOutput();
    
    bool initialize(int sampleRate, int channels);
    void shutdown();
    
    void play();
    void pause();
    void setVolume(float volume); // 0.0 to 1.0
    float getVolume() const { return m_volume; }
    void setPlaybackRate(float rate); // 0.5 to 2.0
    float getPlaybackRate() const { return m_playbackRate; }
    
    void pushAudioFrame(AudioFrame* frame);
    
    // Audio clock for A/V sync
    double getAudioClock() const { return m_audioClock; }
    void setAudioClock(double time) { m_audioClock = time; }
    
    // Clear audio queue (for seeking)
    void clearQueue();
    
private:
#ifdef __APPLE__
    AudioQueueRef m_audioQueue;
    static constexpr int NUM_BUFFERS = 3;
    AudioQueueBufferRef m_buffers[NUM_BUFFERS];
    
    static void audioCallback(void* userData, AudioQueueRef queue, AudioQueueBufferRef buffer);
#endif

#ifdef _WIN32
    IMMDeviceEnumerator* m_deviceEnumerator;
    IMMDevice* m_device;
    IAudioClient* m_audioClient;
    IAudioRenderClient* m_renderClient;
    HANDLE m_audioEvent;
    std::thread m_audioThread;
    std::atomic<bool> m_stopAudioThread;
    
    void audioThreadFunc();
#endif
    
    std::queue<AudioFrame*> m_frameQueue;
    std::mutex m_queueMutex;
    
    int m_sampleRate;
    int m_channels;
    float m_volume;
    float m_playbackRate;
    std::atomic<bool> m_playing;
    std::atomic<double> m_audioClock;
    std::atomic<double> m_lastClockUpdate;  // Time when clock was last updated
    
    static constexpr int SAMPLES_PER_BUFFER = 4096;
};

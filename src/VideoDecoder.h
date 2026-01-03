#pragma once

#include <string>
#include <memory>
#include <vector>
#include <atomic>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <queue>

// FFmpeg headers
extern "C" {
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/avutil.h>
#include <libavutil/imgutils.h>
#include <libswscale/swscale.h>
#include <libswresample/swresample.h>
}

struct VideoFrame {
    uint8_t* data;
    int width;
    int height;
    int linesize;
    double pts;  // Presentation timestamp in seconds
    
    VideoFrame() : data(nullptr), width(0), height(0), linesize(0), pts(0.0) {}
    ~VideoFrame() {
        if (data) {
            av_free(data);
        }
    }
};

struct AudioFrame {
    uint8_t* data;
    int size;
    double pts;
    
    AudioFrame() : data(nullptr), size(0), pts(0.0) {}
    ~AudioFrame() {
        if (data) {
            av_free(data);
        }
    }
};

class VideoDecoder {
public:
    VideoDecoder();
    ~VideoDecoder();
    
    // File operations
    bool open(const std::string& filename);
    void close();
    
    // Playback control
    void play();
    void pause();
    void stop();
    bool isPlaying() const { return m_playing; }
    
    // Seeking
    void seek(double seconds);
    
    // Frame retrieval
    VideoFrame* getNextVideoFrame();
    AudioFrame* getNextAudioFrame();
    
    // Media info
    double getDuration() const { return m_duration; }
    double getCurrentTime() const { return m_currentTime; }
    int getVideoWidth() const { return m_videoWidth; }
    int getVideoHeight() const { return m_videoHeight; }
    int getSampleRate() const { return m_sampleRate; }
    int getChannels() const { return m_channels; }
    
    bool hasVideo() const { return m_videoStreamIndex >= 0; }
    bool hasAudio() const { return m_audioStreamIndex >= 0; }
    
private:
    // FFmpeg context
    AVFormatContext* m_formatCtx;
    AVCodecContext* m_videoCodecCtx;
    AVCodecContext* m_audioCodecCtx;
    SwsContext* m_swsCtx;
    SwrContext* m_swrCtx;
    
    int m_videoStreamIndex;
    int m_audioStreamIndex;
    
    // Media properties
    double m_duration;
    double m_currentTime;
    int m_videoWidth;
    int m_videoHeight;
    int m_sampleRate;
    int m_channels;
    
    // Playback state
    std::atomic<bool> m_playing;
    std::atomic<bool> m_seeking;
    std::atomic<bool> m_stopRequested;
    double m_seekTargetTime;  // Accurate seek target in seconds
    
    // Threading
    std::thread m_decodeThread;
    void decodeLoop();
    
    // Frame queues
    std::queue<VideoFrame*> m_videoQueue;
    std::queue<AudioFrame*> m_audioQueue;
    std::mutex m_videoQueueMutex;
    std::mutex m_audioQueueMutex;
    std::condition_variable m_videoQueueCV;
    std::condition_variable m_audioQueueCV;
    
    // Mutex to protect FFmpeg contexts from concurrent access
    std::mutex m_ffmpegMutex;
    
    static constexpr int MAX_VIDEO_QUEUE_SIZE = 5;
    static constexpr int MAX_AUDIO_QUEUE_SIZE = 10;
    
    // Helper methods
    bool openCodecContext(AVMediaType type);
    VideoFrame* decodeVideoPacket(AVPacket* packet);
    AudioFrame* decodeAudioPacket(AVPacket* packet);
    void clearQueues();
};

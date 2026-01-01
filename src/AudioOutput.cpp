#include "AudioOutput.h"
#include "VideoDecoder.h"
#include <iostream>

AudioOutput::AudioOutput()
    : m_sampleRate(0)
    , m_channels(0)
    , m_volume(1.0f)
    , m_playing(false)
    , m_audioClock(0.0)
    , m_lastClockUpdate(0.0)
#ifdef __APPLE__
    , m_audioQueue(nullptr)
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
#endif
}

void AudioOutput::pause() {
#ifdef __APPLE__
    if (m_audioQueue && m_playing) {
        AudioQueuePause(m_audioQueue);
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
        
        // Update audio clock with frame PTS
        output->m_audioClock = frame->pts;
        output->m_lastClockUpdate = frame->pts;
        
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

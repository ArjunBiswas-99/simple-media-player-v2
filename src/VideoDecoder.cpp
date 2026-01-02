#include "VideoDecoder.h"
#include <iostream>

VideoDecoder::VideoDecoder()
    : m_formatCtx(nullptr)
    , m_videoCodecCtx(nullptr)
    , m_audioCodecCtx(nullptr)
    , m_swsCtx(nullptr)
    , m_swrCtx(nullptr)
    , m_videoStreamIndex(-1)
    , m_audioStreamIndex(-1)
    , m_duration(0.0)
    , m_currentTime(0.0)
    , m_videoWidth(0)
    , m_videoHeight(0)
    , m_sampleRate(0)
    , m_channels(0)
    , m_playing(false)
    , m_seeking(false)
    , m_stopRequested(false)
{
}

VideoDecoder::~VideoDecoder() {
    close();
}

bool VideoDecoder::open(const std::string& filename) {
    // Open input file
    if (avformat_open_input(&m_formatCtx, filename.c_str(), nullptr, nullptr) < 0) {
        std::cerr << "Could not open file: " << filename << std::endl;
        return false;
    }
    
    // Retrieve stream information
    if (avformat_find_stream_info(m_formatCtx, nullptr) < 0) {
        std::cerr << "Could not find stream information" << std::endl;
        avformat_close_input(&m_formatCtx);
        return false;
    }
    
    // Find video and audio streams
    for (unsigned int i = 0; i < m_formatCtx->nb_streams; i++) {
        AVCodecParameters* codecpar = m_formatCtx->streams[i]->codecpar;
        
        if (codecpar->codec_type == AVMEDIA_TYPE_VIDEO && m_videoStreamIndex < 0) {
            m_videoStreamIndex = i;
        } else if (codecpar->codec_type == AVMEDIA_TYPE_AUDIO && m_audioStreamIndex < 0) {
            m_audioStreamIndex = i;
        }
    }
    
    if (m_videoStreamIndex < 0 && m_audioStreamIndex < 0) {
        std::cerr << "Could not find video or audio stream" << std::endl;
        avformat_close_input(&m_formatCtx);
        return false;
    }
    
    // Open codecs
    if (m_videoStreamIndex >= 0) {
        if (!openCodecContext(AVMEDIA_TYPE_VIDEO)) {
            std::cerr << "Could not open video codec" << std::endl;
            close();
            return false;
        }
        
        m_videoWidth = m_videoCodecCtx->width;
        m_videoHeight = m_videoCodecCtx->height;
        
        // Initialize video scaler (convert to RGB24)
        m_swsCtx = sws_getContext(
            m_videoWidth, m_videoHeight, m_videoCodecCtx->pix_fmt,
            m_videoWidth, m_videoHeight, AV_PIX_FMT_RGB24,
            SWS_BILINEAR, nullptr, nullptr, nullptr
        );
        
        if (!m_swsCtx) {
            std::cerr << "Could not initialize video scaler" << std::endl;
            close();
            return false;
        }
    }
    
    if (m_audioStreamIndex >= 0) {
        if (!openCodecContext(AVMEDIA_TYPE_AUDIO)) {
            std::cerr << "Could not open audio codec" << std::endl;
            // Continue without audio
            m_audioStreamIndex = -1;
        } else {
            m_sampleRate = m_audioCodecCtx->sample_rate;
            m_channels = m_audioCodecCtx->ch_layout.nb_channels;
            
            // Initialize audio resampler (convert to stereo float)
            swr_alloc_set_opts2(&m_swrCtx,
                &m_audioCodecCtx->ch_layout, AV_SAMPLE_FMT_FLT, m_sampleRate,
                &m_audioCodecCtx->ch_layout, m_audioCodecCtx->sample_fmt, m_sampleRate,
                0, nullptr);
            
            if (m_swrCtx) {
                swr_init(m_swrCtx);
            }
        }
    }
    
    // Get duration
    if (m_formatCtx->duration != AV_NOPTS_VALUE) {
        m_duration = (double)m_formatCtx->duration / AV_TIME_BASE;
    }
    
    std::cout << "Opened: " << filename << std::endl;
    std::cout << "Duration: " << m_duration << " seconds" << std::endl;
    std::cout << "Video: " << m_videoWidth << "x" << m_videoHeight << std::endl;
    std::cout << "Audio: " << m_sampleRate << "Hz, " << m_channels << " channels" << std::endl;
    
    return true;
}

void VideoDecoder::close() {
    stop();
    
    if (m_decodeThread.joinable()) {
        m_stopRequested = true;
        m_videoQueueCV.notify_all();
        m_audioQueueCV.notify_all();
        m_decodeThread.join();
    }
    
    clearQueues();
    
    if (m_swsCtx) {
        sws_freeContext(m_swsCtx);
        m_swsCtx = nullptr;
    }
    
    if (m_swrCtx) {
        swr_free(&m_swrCtx);
    }
    
    if (m_videoCodecCtx) {
        avcodec_free_context(&m_videoCodecCtx);
    }
    
    if (m_audioCodecCtx) {
        avcodec_free_context(&m_audioCodecCtx);
    }
    
    if (m_formatCtx) {
        avformat_close_input(&m_formatCtx);
    }
    
    m_videoStreamIndex = -1;
    m_audioStreamIndex = -1;
}

bool VideoDecoder::openCodecContext(AVMediaType type) {
    int streamIndex = (type == AVMEDIA_TYPE_VIDEO) ? m_videoStreamIndex : m_audioStreamIndex;
    
    if (streamIndex < 0) {
        return false;
    }
    
    AVStream* stream = m_formatCtx->streams[streamIndex];
    AVCodecParameters* codecpar = stream->codecpar;
    
    // Find decoder
    const AVCodec* codec = avcodec_find_decoder(codecpar->codec_id);
    if (!codec) {
        std::cerr << "Codec not found" << std::endl;
        return false;
    }
    
    // Allocate codec context
    AVCodecContext* codecCtx = avcodec_alloc_context3(codec);
    if (!codecCtx) {
        std::cerr << "Could not allocate codec context" << std::endl;
        return false;
    }
    
    // Copy codec parameters
    if (avcodec_parameters_to_context(codecCtx, codecpar) < 0) {
        std::cerr << "Could not copy codec parameters" << std::endl;
        avcodec_free_context(&codecCtx);
        return false;
    }
    
    // Open codec
    if (avcodec_open2(codecCtx, codec, nullptr) < 0) {
        std::cerr << "Could not open codec" << std::endl;
        avcodec_free_context(&codecCtx);
        return false;
    }
    
    if (type == AVMEDIA_TYPE_VIDEO) {
        m_videoCodecCtx = codecCtx;
    } else {
        m_audioCodecCtx = codecCtx;
    }
    
    return true;
}

void VideoDecoder::play() {
    if (!m_playing && m_formatCtx) {
        m_playing = true;
        m_stopRequested = false;
        
        if (!m_decodeThread.joinable()) {
            m_decodeThread = std::thread(&VideoDecoder::decodeLoop, this);
        }
    }
}

void VideoDecoder::pause() {
    m_playing = false;
}

void VideoDecoder::stop() {
    m_playing = false;
    m_stopRequested = true;
}

void VideoDecoder::seek(double seconds) {
    std::cout << "[DEBUG VideoDecoder::seek] Called with seconds=" << seconds << std::endl;
    std::cout << "[DEBUG VideoDecoder::seek] this pointer=" << (void*)this << std::endl;
    
    if (!m_formatCtx) {
        std::cout << "[DEBUG VideoDecoder::seek] m_formatCtx is NULL, returning" << std::endl;
        return;
    }
    
    std::cout << "[DEBUG VideoDecoder::seek] Setting m_seeking=true" << std::endl;
    m_seeking = true;
    std::cout << "[DEBUG VideoDecoder::seek] m_seeking is now: " << m_seeking.load() << std::endl;
    
    // Give decode thread time to see m_seeking flag and stop
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    
    // Lock FFmpeg mutex to prevent decode thread from using contexts
    std::cout << "[DEBUG VideoDecoder::seek] Locking FFmpeg mutex" << std::endl;
    std::lock_guard<std::mutex> ffmpegLock(m_ffmpegMutex);
    std::cout << "[DEBUG VideoDecoder::seek] FFmpeg mutex locked" << std::endl;
    
    int64_t timestamp = (int64_t)(seconds * AV_TIME_BASE);
    std::cout << "[DEBUG VideoDecoder::seek] Calling av_seek_frame with timestamp=" << timestamp << std::endl;
    av_seek_frame(m_formatCtx, -1, timestamp, AVSEEK_FLAG_BACKWARD);
    std::cout << "[DEBUG VideoDecoder::seek] av_seek_frame completed" << std::endl;
    
    if (m_videoCodecCtx) {
        std::cout << "[DEBUG VideoDecoder::seek] Flushing video codec buffers" << std::endl;
        avcodec_flush_buffers(m_videoCodecCtx);
    }
    if (m_audioCodecCtx) {
        std::cout << "[DEBUG VideoDecoder::seek] Flushing audio codec buffers" << std::endl;
        avcodec_flush_buffers(m_audioCodecCtx);
    }
    
    std::cout << "[DEBUG VideoDecoder::seek] About to call clearQueues()" << std::endl;
    clearQueues();
    std::cout << "[DEBUG VideoDecoder::seek] clearQueues() returned" << std::endl;
    
    m_currentTime = seconds;
    std::cout << "[DEBUG VideoDecoder::seek] Unlocking FFmpeg mutex and setting m_seeking=false" << std::endl;
    // FFmpeg mutex will be unlocked here when ffmpegLock goes out of scope
    m_seeking = false;
    std::cout << "[DEBUG VideoDecoder::seek] Seek completed successfully" << std::endl;
}

void VideoDecoder::decodeLoop() {
    AVPacket* packet = av_packet_alloc();
    
    while (!m_stopRequested) {
        if (!m_playing) {
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
            continue;
        }
        
        // Skip decoding if we're currently seeking
        if (m_seeking) {
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
            continue;
        }
        
        // Check if queues are full
        {
            std::unique_lock<std::mutex> lock(m_videoQueueMutex);
            if (m_videoQueue.size() >= MAX_VIDEO_QUEUE_SIZE) {
                m_videoQueueCV.wait_for(lock, std::chrono::milliseconds(10));
                continue;
            }
        }
        
        // Lock FFmpeg mutex before accessing contexts
        std::lock_guard<std::mutex> ffmpegLock(m_ffmpegMutex);
        
        // Double-check m_seeking after acquiring lock
        if (m_seeking) {
            continue;
        }
        
        // Read packet
        int ret = av_read_frame(m_formatCtx, packet);
        
        if (ret < 0) {
            if (ret == AVERROR_EOF) {
                // End of file
                m_playing = false;
            }
            break;
        }
        
        // Decode video packet
        if (packet->stream_index == m_videoStreamIndex) {
            VideoFrame* frame = decodeVideoPacket(packet);
            if (frame) {
                std::lock_guard<std::mutex> lock(m_videoQueueMutex);
                m_videoQueue.push(frame);
                m_videoQueueCV.notify_one();
            }
        }
        // Decode audio packet
        else if (packet->stream_index == m_audioStreamIndex) {
            AudioFrame* frame = decodeAudioPacket(packet);
            if (frame) {
                std::lock_guard<std::mutex> lock(m_audioQueueMutex);
                m_audioQueue.push(frame);
                m_audioQueueCV.notify_one();
            }
        }
        
        av_packet_unref(packet);
    }
    
    av_packet_free(&packet);
}

VideoFrame* VideoDecoder::decodeVideoPacket(AVPacket* packet) {
    if (!m_videoCodecCtx) return nullptr;
    
    // Send packet to decoder
    int ret = avcodec_send_packet(m_videoCodecCtx, packet);
    if (ret < 0) {
        return nullptr;
    }
    
    // Receive frame from decoder
    AVFrame* frame = av_frame_alloc();
    ret = avcodec_receive_frame(m_videoCodecCtx, frame);
    
    if (ret < 0) {
        av_frame_free(&frame);
        return nullptr;
    }
    
    // Convert to RGB24
    VideoFrame* videoFrame = new VideoFrame();
    videoFrame->width = m_videoWidth;
    videoFrame->height = m_videoHeight;
    videoFrame->linesize = m_videoWidth * 3;  // RGB24 format
    
    int bufferSize = av_image_get_buffer_size(AV_PIX_FMT_RGB24, m_videoWidth, m_videoHeight, 1);
    videoFrame->data = (uint8_t*)av_malloc(bufferSize);
    
    uint8_t* dst_data[4] = { videoFrame->data, nullptr, nullptr, nullptr };
    int dst_linesize[4] = { videoFrame->linesize, 0, 0, 0 };
    
    sws_scale(m_swsCtx, frame->data, frame->linesize, 0, m_videoHeight,
              dst_data, dst_linesize);
    
    // Calculate PTS
    if (frame->pts != AV_NOPTS_VALUE) {
        AVStream* stream = m_formatCtx->streams[m_videoStreamIndex];
        videoFrame->pts = frame->pts * av_q2d(stream->time_base);
        m_currentTime = videoFrame->pts;
    }
    
    av_frame_free(&frame);
    
    return videoFrame;
}

AudioFrame* VideoDecoder::decodeAudioPacket(AVPacket* packet) {
    if (!m_audioCodecCtx) return nullptr;
    
    // Send packet to decoder
    int ret = avcodec_send_packet(m_audioCodecCtx, packet);
    if (ret < 0) {
        return nullptr;
    }
    
    // Receive frame from decoder
    AVFrame* frame = av_frame_alloc();
    ret = avcodec_receive_frame(m_audioCodecCtx, frame);
    
    if (ret < 0) {
        av_frame_free(&frame);
        return nullptr;
    }
    
    AudioFrame* audioFrame = new AudioFrame();
    
    // Resample if needed
    if (m_swrCtx) {
        int out_samples = swr_get_out_samples(m_swrCtx, frame->nb_samples);
        audioFrame->size = out_samples * m_channels * sizeof(float);
        audioFrame->data = (uint8_t*)av_malloc(audioFrame->size);
        
        uint8_t* out_buf[1] = { audioFrame->data };
        swr_convert(m_swrCtx, out_buf, out_samples,
                    (const uint8_t**)frame->data, frame->nb_samples);
    } else {
        audioFrame->size = frame->nb_samples * m_channels * sizeof(float);
        audioFrame->data = (uint8_t*)av_malloc(audioFrame->size);
        memcpy(audioFrame->data, frame->data[0], audioFrame->size);
    }
    
    // Calculate PTS
    if (frame->pts != AV_NOPTS_VALUE) {
        AVStream* stream = m_formatCtx->streams[m_audioStreamIndex];
        double time_base = av_q2d(stream->time_base);
        double rawPTS = frame->pts * time_base;
        
        // CRITICAL FIX: Some files have audio PTS that increments by frame size instead of 1
        // Detect this and correct it
        static double lastPTS = -1.0;
        static double expectedDuration = 0.0;
        static bool needsCorrection = false;
        static bool correctionChecked = false;
        static int logCount = 0;
        
        if (!correctionChecked && frame->nb_samples > 0) {
            expectedDuration = (double)frame->nb_samples / m_sampleRate;
            
            if (lastPTS >= 0) {
                double actualDuration = rawPTS - lastPTS;
                // If actual duration is more than 10x expected, we need correction
                if (actualDuration > expectedDuration * 10.0) {
                    needsCorrection = true;
                    double correctionFactor = expectedDuration / actualDuration;
                    std::cout << "[AUDIO FIX] Detected incorrect PTS scaling!" << std::endl;
                    std::cout << "  Expected frame duration: " << expectedDuration << "s" << std::endl;
                    std::cout << "  Actual PTS jump: " << actualDuration << "s" << std::endl;
                    std::cout << "  Applying correction: dividing by " << (actualDuration/expectedDuration) << std::endl;
                } else {
                    std::cout << "[AUDIO CHECK] PTS scaling is correct, no fix needed" << std::endl;
                    std::cout << "  Expected: " << expectedDuration << "s, Actual: " << actualDuration << "s" << std::endl;
                }
                correctionChecked = true;
            }
            lastPTS = rawPTS;
        }
        
        // Apply correction if needed
        if (needsCorrection && frame->nb_samples > 0) {
            // Calculate PTS based on frame position and duration instead
            audioFrame->pts = lastPTS + expectedDuration;
            lastPTS = audioFrame->pts;
            
            if (logCount < 3) {
                std::cout << "[AUDIO FIX] Frame " << logCount << ": rawPTS=" << rawPTS 
                          << " -> correctedPTS=" << audioFrame->pts << std::endl;
                logCount++;
            }
        } else {
            audioFrame->pts = rawPTS;
            lastPTS = rawPTS;
            
            if (logCount < 3) {
                std::cout << "[AUDIO] Frame " << logCount << ": PTS=" << audioFrame->pts 
                          << " (no correction)" << std::endl;
                logCount++;
            }
        }
    }
    
    av_frame_free(&frame);
    
    return audioFrame;
}

VideoFrame* VideoDecoder::getNextVideoFrame() {
    std::lock_guard<std::mutex> lock(m_videoQueueMutex);
    
    if (m_videoQueue.empty()) {
        return nullptr;
    }
    
    VideoFrame* frame = m_videoQueue.front();
    m_videoQueue.pop();
    m_videoQueueCV.notify_one();
    
    return frame;
}

AudioFrame* VideoDecoder::getNextAudioFrame() {
    std::lock_guard<std::mutex> lock(m_audioQueueMutex);
    
    if (m_audioQueue.empty()) {
        return nullptr;
    }
    
    AudioFrame* frame = m_audioQueue.front();
    m_audioQueue.pop();
    m_audioQueueCV.notify_one();
    
    return frame;
}

void VideoDecoder::clearQueues() {
    std::cout << "[DEBUG VideoDecoder::clearQueues] Starting to clear queues, this=" << (void*)this << std::endl;
    std::cout << "[DEBUG VideoDecoder::clearQueues] m_seeking=" << m_seeking.load() << std::endl;
    
    // Wait longer for decode thread to detect m_seeking flag and stop adding frames
    std::cout << "[DEBUG VideoDecoder::clearQueues] About to sleep for 50ms" << std::endl;
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
    std::cout << "[DEBUG VideoDecoder::clearQueues] Sleep completed" << std::endl;
    
    std::cout << "[DEBUG VideoDecoder::clearQueues] About to lock video queue" << std::endl;
    
    {
        std::lock_guard<std::mutex> lock(m_videoQueueMutex);
        std::cout << "[DEBUG VideoDecoder::clearQueues] Video queue locked, size: " << m_videoQueue.size() << std::endl;
        
        while (!m_videoQueue.empty()) {
            VideoFrame* frame = m_videoQueue.front();
            if (frame != nullptr) {
                std::cout << "[DEBUG VideoDecoder::clearQueues] Deleting video frame at " << (void*)frame << std::endl;
                delete frame;
            }
            m_videoQueue.pop();
        }
        std::cout << "[DEBUG VideoDecoder::clearQueues] Video queue cleared" << std::endl;
    }
    
    std::cout << "[DEBUG VideoDecoder::clearQueues] About to lock audio queue" << std::endl;
    
    {
        std::lock_guard<std::mutex> lock(m_audioQueueMutex);
        std::cout << "[DEBUG VideoDecoder::clearQueues] Audio queue locked, size: " << m_audioQueue.size() << std::endl;
        
        while (!m_audioQueue.empty()) {
            AudioFrame* frame = m_audioQueue.front();
            if (frame != nullptr) {
                std::cout << "[DEBUG VideoDecoder::clearQueues] Deleting audio frame at " << (void*)frame << std::endl;
                delete frame;
            }
            m_audioQueue.pop();
        }
        std::cout << "[DEBUG VideoDecoder::clearQueues] Audio queue cleared" << std::endl;
    }
    
    std::cout << "[DEBUG VideoDecoder::clearQueues] clearQueues completed" << std::endl;
}

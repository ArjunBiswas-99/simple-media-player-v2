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
    if (!m_formatCtx) return;
    
    m_seeking = true;
    
    int64_t timestamp = (int64_t)(seconds * AV_TIME_BASE);
    av_seek_frame(m_formatCtx, -1, timestamp, AVSEEK_FLAG_BACKWARD);
    
    if (m_videoCodecCtx) {
        avcodec_flush_buffers(m_videoCodecCtx);
    }
    if (m_audioCodecCtx) {
        avcodec_flush_buffers(m_audioCodecCtx);
    }
    
    clearQueues();
    
    m_currentTime = seconds;
    m_seeking = false;
}

void VideoDecoder::decodeLoop() {
    AVPacket* packet = av_packet_alloc();
    
    while (!m_stopRequested) {
        if (!m_playing) {
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
        audioFrame->pts = frame->pts * av_q2d(stream->time_base);
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
    {
        std::lock_guard<std::mutex> lock(m_videoQueueMutex);
        while (!m_videoQueue.empty()) {
            delete m_videoQueue.front();
            m_videoQueue.pop();
        }
    }
    
    {
        std::lock_guard<std::mutex> lock(m_audioQueueMutex);
        while (!m_audioQueue.empty()) {
            delete m_audioQueue.front();
            m_audioQueue.pop();
        }
    }
}

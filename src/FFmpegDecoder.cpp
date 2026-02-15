#include "FFmpegDecoder.h"
#include <QDebug>

FFmpegDecoder::FFmpegDecoder()
    : m_formatContext(nullptr), m_videoCodecContext(nullptr),
      m_videoCodec(nullptr), m_videoStreamIndex(-1), m_swsContext(nullptr) {
}

FFmpegDecoder::~FFmpegDecoder() {
    close();
}

bool FFmpegDecoder::openFile(const QString &filePath) {
    cleanup();
    
    const char *filename = filePath.toStdString().c_str();
    
    // Open file
    if (avformat_open_input(&m_formatContext, filename, nullptr, nullptr) != 0) {
        qWarning() << "Could not open file:" << filePath;
        return false;
    }
    
    // Find stream info
    if (avformat_find_stream_info(m_formatContext, nullptr) < 0) {
        qWarning() << "Could not find stream info";
        cleanup();
        return false;
    }
    
    // Find video stream
    m_videoStreamIndex = -1;
    for (unsigned int i = 0; i < m_formatContext->nb_streams; i++) {
        if (m_formatContext->streams[i]->codecpar->codec_type == AVMEDIA_TYPE_VIDEO) {
            m_videoStreamIndex = i;
            break;
        }
    }
    
    if (m_videoStreamIndex == -1) {
        qWarning() << "No video stream found";
        cleanup();
        return false;
    }
    
    // Get codec and open it
    AVCodecParameters *codecpar = m_formatContext->streams[m_videoStreamIndex]->codecpar;
    m_videoCodec = avcodec_find_decoder(codecpar->codec_id);
    if (!m_videoCodec) {
        qWarning() << "Codec not found";
        cleanup();
        return false;
    }
    
    m_videoCodecContext = avcodec_alloc_context3(m_videoCodec);
    avcodec_parameters_to_context(m_videoCodecContext, codecpar);
    
    if (avcodec_open2(m_videoCodecContext, m_videoCodec, nullptr) < 0) {
        qWarning() << "Could not open codec";
        cleanup();
        return false;
    }
    
    // Initialize swscale
    m_swsContext = sws_getContext(
        m_videoCodecContext->width, m_videoCodecContext->height,
        m_videoCodecContext->pix_fmt,
        m_videoCodecContext->width, m_videoCodecContext->height,
        AV_PIX_FMT_RGB32, SWS_BILINEAR, nullptr, nullptr, nullptr
    );
    
    if (!m_swsContext) {
        qWarning() << "Could not initialize swscale context";
        cleanup();
        return false;
    }
    
    qDebug() << "Opened file successfully:" << filePath;
    return true;
}

void FFmpegDecoder::close() {
    cleanup();
}

qint64 FFmpegDecoder::getDuration() const {
    if (!m_formatContext) return 0;
    return (m_formatContext->duration / AV_TIME_BASE) * 1000; // Convert to ms
}

bool FFmpegDecoder::seek(qint64 ms) {
    if (!m_formatContext) return false;
    
    int64_t timestamp = (ms / 1000) * AV_TIME_BASE;
    return av_seek_frame(m_formatContext, -1, timestamp, AVSEEK_FLAG_BACKWARD) >= 0;
}

bool FFmpegDecoder::getNextFrame(QImage &frame) {
    if (!m_formatContext || !m_videoCodecContext) return false;
    
    AVPacket packet;
    AVFrame *pFrame = av_frame_alloc();
    AVFrame *pFrameRGB = av_frame_alloc();
    
    if (!pFrame || !pFrameRGB) {
        av_frame_free(&pFrame);
        av_frame_free(&pFrameRGB);
        return false;
    }
    
    int buffer_size = av_image_get_buffer_size(AV_PIX_FMT_RGB32, m_videoCodecContext->width,
                                                m_videoCodecContext->height, 1);
    uint8_t *buffer = new uint8_t[buffer_size];
    av_image_fill_arrays(pFrameRGB->data, pFrameRGB->linesize, buffer, AV_PIX_FMT_RGB32,
                        m_videoCodecContext->width, m_videoCodecContext->height, 1);
    
    bool frameDecoded = false;
    while (av_read_frame(m_formatContext, &packet) >= 0) {
        if (packet.stream_index == m_videoStreamIndex) {
            avcodec_send_packet(m_videoCodecContext, &packet);
            
            if (avcodec_receive_frame(m_videoCodecContext, pFrame) == 0) {
                sws_scale(m_swsContext, (uint8_t const * const *)pFrame->data,
                         pFrame->linesize, 0, m_videoCodecContext->height,
                         pFrameRGB->data, pFrameRGB->linesize);
                
                frame = QImage(buffer, m_videoCodecContext->width, m_videoCodecContext->height,
                             QImage::Format_RGB32).copy();
                frameDecoded = true;
                av_packet_unref(&packet);
                break;
            }
        }
        av_packet_unref(&packet);
    }
    
    av_frame_free(&pFrame);
    av_frame_free(&pFrameRGB);
    delete[] buffer;
    
    return frameDecoded;
}

int FFmpegDecoder::getWidth() const {
    return m_videoCodecContext ? m_videoCodecContext->width : 0;
}

int FFmpegDecoder::getHeight() const {
    return m_videoCodecContext ? m_videoCodecContext->height : 0;
}

double FFmpegDecoder::getFrameRate() const {
    if (!m_formatContext || m_videoStreamIndex < 0) return 0.0;
    
    AVStream *stream = m_formatContext->streams[m_videoStreamIndex];
    return av_q2d(stream->r_frame_rate);
}

void FFmpegDecoder::cleanup() {
    if (m_swsContext) {
        sws_freeContext(m_swsContext);
        m_swsContext = nullptr;
    }
    
    if (m_videoCodecContext) {
        avcodec_free_context(&m_videoCodecContext);
        m_videoCodecContext = nullptr;
    }
    
    if (m_formatContext) {
        avformat_close_input(&m_formatContext);
        m_formatContext = nullptr;
    }
}

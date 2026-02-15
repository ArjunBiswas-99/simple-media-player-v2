#ifndef FFMPEGDECODER_H
#define FFMPEGDECODER_H

#include <QString>
#include <QImage>
#include <memory>

extern "C" {
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <libswscale/swscale.h>
}

class FFmpegDecoder {
public:
    FFmpegDecoder();
    ~FFmpegDecoder();

    bool openFile(const QString &filePath);
    void close();
    
    qint64 getDuration() const;
    bool seek(qint64 ms);
    bool getNextFrame(QImage &frame);
    
    int getWidth() const;
    int getHeight() const;
    double getFrameRate() const;

private:
    AVFormatContext *m_formatContext;
    AVCodecContext *m_videoCodecContext;
    const AVCodec *m_videoCodec;
    int m_videoStreamIndex;
    SwsContext *m_swsContext;
    
    void cleanup();
};

#endif // FFMPEGDECODER_H

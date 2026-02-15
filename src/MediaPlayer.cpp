#include "MediaPlayer.h"
#include "FFmpegDecoder.h"
#include "SubtitleManager.h"
#include "VideoFilter.h"
#include <QDebug>
#include <QFileInfo>

MediaPlayer::MediaPlayer(QObject *parent)
    : QObject(parent), m_duration(0), m_position(0), m_isPlaying(false),
      m_currentPlaylistIndex(0), m_loopMode(0), m_shuffle(false),
      m_decoder(std::make_unique<FFmpegDecoder>()),
      m_subtitleManager(std::make_unique<SubtitleManager>()),
      m_videoFilter(std::make_unique<VideoFilter>()) {
    m_status = "Stopped";
    
    m_playbackTimer = new QTimer(this);
    connect(m_playbackTimer, &QTimer::timeout, this, &MediaPlayer::onPlaybackTick);
}

MediaPlayer::~MediaPlayer() {
}

QString MediaPlayer::currentFile() const {
    return m_currentFile;
}

QString MediaPlayer::status() const {
    return m_status;
}

qint64 MediaPlayer::duration() const {
    return m_duration;
}

qint64 MediaPlayer::position() const {
    return m_position;
}

bool MediaPlayer::isPlaying() const {
    return m_isPlaying;
}

QString MediaPlayer::playlist() const {
    QString result;
    for (int i = 0; i < m_playlist.size(); ++i) {
        result += QString::number(i) + ": " + QFileInfo(m_playlist[i]).fileName();
        if (i < m_playlist.size() - 1) result += "\n";
    }
    return result;
}

void MediaPlayer::openFile(const QString &filePath) {
    if (filePath.isEmpty()) return;
    
    QFileInfo fi(filePath);
    if (!fi.exists()) {
        emit error(QString("File not found: %1").arg(filePath));
        return;
    }
    
    // Try to open with FFmpeg decoder
    if (m_decoder->openFile(filePath)) {
        m_currentFile = filePath;
        m_duration = m_decoder->getDuration();
        m_position = 0;
        m_isPlaying = false;
        m_status = "Opened";
        qDebug() << "Opened file with FFmpeg, duration:" << m_duration << "ms";
    } else {
        // Fallback to mock duration if FFmpeg fails
        m_currentFile = filePath;
        m_duration = 180000; // Mock: 3 minutes
        m_position = 0;
        m_isPlaying = false;
        m_status = "Opened (mock playback)";
        qDebug() << "FFmpeg decoder failed, using mock duration";
    }
    
    emit currentFileChanged();
    emit statusChanged();
    emit durationChanged();
    emit positionChanged();
    emit isPlayingChanged();
}

void MediaPlayer::play() {
    if (m_currentFile.isEmpty()) {
        emit error("No file loaded");
        return;
    }
    
    m_isPlaying = true;
    m_status = "Playing";
    m_playbackTimer->start(100); // Update every 100ms
    
    emit isPlayingChanged();
    emit statusChanged();
}

void MediaPlayer::pause() {
    if (!m_isPlaying) return;
    
    m_isPlaying = false;
    m_status = "Paused";
    m_playbackTimer->stop();
    
    emit isPlayingChanged();
    emit statusChanged();
}

void MediaPlayer::stop() {
    m_isPlaying = false;
    m_position = 0;
    m_status = "Stopped";
    m_playbackTimer->stop();
    
    emit isPlayingChanged();
    emit statusChanged();
    emit positionChanged();
}

void MediaPlayer::seek(qint64 ms) {
    m_position = qBound(0LL, ms, m_duration);
    emit positionChanged();
}

void MediaPlayer::addToPlaylist(const QString &filePath) {
    QFileInfo fi(filePath);
    if (!fi.exists()) {
        emit error(QString("File not found: %1").arg(filePath));
        return;
    }
    
    m_playlist.append(filePath);
    emit playlistChanged();
}

void MediaPlayer::removeFromPlaylist(int index) {
    if (index >= 0 && index < m_playlist.size()) {
        m_playlist.removeAt(index);
        emit playlistChanged();
    }
}

void MediaPlayer::playNext() {
    if (m_playlist.isEmpty()) return;
    
    m_currentPlaylistIndex = (m_currentPlaylistIndex + 1) % m_playlist.size();
    openFile(m_playlist[m_currentPlaylistIndex]);
    play();
}

void MediaPlayer::playPrevious() {
    if (m_playlist.isEmpty()) return;
    
    m_currentPlaylistIndex = (m_currentPlaylistIndex - 1 + m_playlist.size()) % m_playlist.size();
    openFile(m_playlist[m_currentPlaylistIndex]);
    play();
}

void MediaPlayer::setLoopMode(int mode) {
    m_loopMode = mode;
}

void MediaPlayer::setShuffle(bool enabled) {
    m_shuffle = enabled;
}

void MediaPlayer::loadSubtitles(const QString &filePath) {
    m_subtitleManager->loadSRTFile(filePath);
    qDebug() << "Loaded subtitles from:" << filePath;
}

void MediaPlayer::setBrightness(float value) {
    m_videoFilter->brightness = value;
}

void MediaPlayer::setContrast(float value) {
    m_videoFilter->contrast = value;
}

void MediaPlayer::setSaturation(float value) {
    m_videoFilter->saturation = value;
}

void MediaPlayer::onPlaybackTick() {
    if (!m_isPlaying) return;
    
    m_position += 100; // Advance by 100ms
    
    if (m_position >= m_duration) {
        // File ended
        if (m_loopMode == 1) {
            // Loop one
            m_position = 0;
        } else if (m_loopMode == 2) {
            // Loop all
            playNext();
        } else {
            // No loop, play next or stop
            if (!m_playlist.isEmpty() && m_currentPlaylistIndex < m_playlist.size() - 1) {
                playNext();
            } else {
                stop();
            }
        }
    }
    
    emit positionChanged();
}

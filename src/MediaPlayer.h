#ifndef MEDIAPLAYER_H
#define MEDIAPLAYER_H

#include <QObject>
#include <QString>
#include <QTimer>
#include <QList>
#include <memory>

class FFmpegDecoder;
class SubtitleManager;
struct VideoFilter;

class MediaPlayer : public QObject {
    Q_OBJECT
    Q_PROPERTY(QString currentFile READ currentFile NOTIFY currentFileChanged)
    Q_PROPERTY(QString status READ status NOTIFY statusChanged)
    Q_PROPERTY(qint64 duration READ duration NOTIFY durationChanged)
    Q_PROPERTY(qint64 position READ position NOTIFY positionChanged)
    Q_PROPERTY(bool isPlaying READ isPlaying NOTIFY isPlayingChanged)
    Q_PROPERTY(QString playlist READ playlist NOTIFY playlistChanged)

public:
    explicit MediaPlayer(QObject *parent = nullptr);
    ~MediaPlayer();

    QString currentFile() const;
    QString status() const;
    qint64 duration() const;
    qint64 position() const;
    bool isPlaying() const;
    QString playlist() const;

public slots:
    void openFile(const QString &filePath);
    void play();
    void pause();
    void stop();
    void seek(qint64 ms);
    void addToPlaylist(const QString &filePath);
    void removeFromPlaylist(int index);
    void playNext();
    void playPrevious();
    void setLoopMode(int mode); // 0=no loop, 1=loop one, 2=loop all
    void setShuffle(bool enabled);
    void loadSubtitles(const QString &filePath);
    void setBrightness(float value);
    void setContrast(float value);
    void setSaturation(float value);

signals:
    void currentFileChanged();
    void statusChanged();
    void durationChanged();
    void positionChanged();
    void isPlayingChanged();
    void playlistChanged();
    void error(const QString &message);

private slots:
    void onPlaybackTick();

private:
    void updateStatus();
    
    QString m_currentFile;
    QString m_status;
    qint64 m_duration;
    qint64 m_position;
    bool m_isPlaying;
    QList<QString> m_playlist;
    int m_currentPlaylistIndex;
    int m_loopMode;
    bool m_shuffle;
    QTimer *m_playbackTimer;
    std::unique_ptr<FFmpegDecoder> m_decoder;
    std::unique_ptr<SubtitleManager> m_subtitleManager;
    std::unique_ptr<VideoFilter> m_videoFilter;
};

#endif // MEDIAPLAYER_H

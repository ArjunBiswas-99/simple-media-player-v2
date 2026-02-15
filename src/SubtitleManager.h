#ifndef SUBTITLEMANAGER_H
#define SUBTITLEMANAGER_H

#include <QString>
#include <QList>
#include <QMap>

struct Subtitle {
    qint64 startTime;  // ms
    qint64 endTime;    // ms
    QString text;
};

class SubtitleManager {
public:
    SubtitleManager();
    
    bool loadSRTFile(const QString &filePath);
    QString getSubtitleAtTime(qint64 timeMs) const;
    QList<Subtitle> getSubtitles() const { return m_subtitles; }
    void clear() { m_subtitles.clear(); }

private:
    QList<Subtitle> m_subtitles;
    
    bool parseSRTTime(const QString &timeStr, qint64 &ms);
};

#endif // SUBTITLEMANAGER_H

#include "SubtitleManager.h"
#include <QFile>
#include <QTextStream>
#include <QRegularExpression>
#include <QDebug>

SubtitleManager::SubtitleManager() {
}

bool SubtitleManager::loadSRTFile(const QString &filePath) {
    QFile file(filePath);
    if (!file.open(QIODevice::ReadOnly | QIODevice::Text)) {
        qWarning() << "Could not open subtitle file:" << filePath;
        return false;
    }
    
    m_subtitles.clear();
    QTextStream in(&file);
    
    while (!in.atEnd()) {
        QString line = in.readLine().trimmed();
        
        // Skip empty lines and sequence numbers
        if (line.isEmpty() || line.toInt() > 0) {
            continue;
        }
        
        // Parse timecode line (e.g., "00:00:01,000 --> 00:00:05,000")
        if (line.contains("-->")) {
            QStringList times = line.split("-->");
            if (times.size() != 2) continue;
            
            Subtitle sub;
            if (!parseSRTTime(times[0].trimmed(), sub.startTime) ||
                !parseSRTTime(times[1].trimmed(), sub.endTime)) {
                continue;
            }
            
            // Read subtitle text lines
            sub.text = "";
            while (!in.atEnd()) {
                line = in.readLine().trimmed();
                if (line.isEmpty()) break;
                if (sub.text.isEmpty()) {
                    sub.text = line;
                } else {
                    sub.text += "\n" + line;
                }
            }
            
            m_subtitles.append(sub);
        }
    }
    
    file.close();
    qDebug() << "Loaded" << m_subtitles.size() << "subtitles from" << filePath;
    return true;
}

QString SubtitleManager::getSubtitleAtTime(qint64 timeMs) const {
    for (const auto &sub : m_subtitles) {
        if (timeMs >= sub.startTime && timeMs <= sub.endTime) {
            return sub.text;
        }
    }
    return "";
}

bool SubtitleManager::parseSRTTime(const QString &timeStr, qint64 &ms) {
    // Format: HH:MM:SS,mmm
    QRegularExpression re("(\\d+):(\\d+):(\\d+),(\\d+)");
    QRegularExpressionMatch match = re.match(timeStr);
    
    if (!match.hasMatch()) {
        return false;
    }
    
    int h = match.captured(1).toInt();
    int m = match.captured(2).toInt();
    int s = match.captured(3).toInt();
    int milli = match.captured(4).toInt();
    
    ms = (h * 3600 + m * 60 + s) * 1000 + milli;
    return true;
}

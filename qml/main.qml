import QtQuick 2.15
import QtQuick.Controls 2.15
import ArjunBiswasMediaPlayer 1.0

ApplicationWindow {
    id: root
    visible: true
    width: 1200
    height: 600
    title: "ArjunBiswasMediaPlayer - Prototype"

    MediaPlayer {
        id: player
    }

    Player {
        anchors.fill: parent
    }
}

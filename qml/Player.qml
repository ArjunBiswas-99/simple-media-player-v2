import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Dialogs 1.3
import ArjunBiswasMediaPlayer 1.0

Rectangle {
    id: canvas
    color: "#000000"

    FileDialog {
        id: fileDialog
        title: "Open Media File"
        folder: shortcuts.home
        onAccepted: {
            player.openFile(fileDialog.fileUrl.toString().replace("file://", ""))
        }
    }

    FileDialog {
        id: subtitleDialog
        title: "Load Subtitles"
        folder: shortcuts.home
        nameFilters: ["Subtitle files (*.srt *.vtt)", "All files (*)"]
        onAccepted: {
            player.loadSubtitles(subtitleDialog.fileUrl.toString().replace("file://", ""))
        }
    }

    Popup {
        id: filterPopup
        x: parent.width - width - 10
        y: parent.height - height - 100
        width: 250
        height: 200
        background: Rectangle { color: "#222"; border.color: "#444" }

        Column {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 10

            Text { text: "Video Filters"; color: "#aaa"; font.bold: true }

            Row {
                spacing: 10
                Text { text: "Brightness"; color: "#888" }
                Slider { width: 150; from: -100; to: 100; onMoved: player.setBrightness(value) }
            }

            Row {
                spacing: 10
                Text { text: "Contrast"; color: "#888" }
                Slider { width: 150; from: -100; to: 100; onMoved: player.setContrast(value) }
            }

            Row {
                spacing: 10
                Text { text: "Saturation"; color: "#888" }
                Slider { width: 150; from: -100; to: 100; onMoved: player.setSaturation(value) }
            }
        }
    }

    // Video area
    Rectangle {
        id: videoArea
        anchors.left: parent.left
        anchors.right: playlistArea.left
        anchors.top: parent.top
        anchors.bottom: controls.top
        color: "black"
        border.color: "#222"

        Column {
            anchors.centerIn: parent
            spacing: 10

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: player.currentFile ? player.currentFile.split("/").pop() : "No File Loaded"
                color: "#aaa"
                font.pixelSize: 16
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Status: " + player.status
                color: "#888"
                font.pixelSize: 14
            }

            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                text: "Video Canvas (placeholder)"
                color: "#666"
                font.pixelSize: 20
            }
        }
    }

    // Playlist sidebar
    Rectangle {
        id: playlistArea
        width: 200
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: controls.top
        color: "#0a0a0a"
        border.left: 1
        border.color: "#333"

        Column {
            anchors.fill: parent
            spacing: 0

            Text {
                text: "Playlist"
                color: "#aaa"
                font.bold: true
                padding: 10
                width: parent.width
            }

            ListView {
                width: parent.width
                height: parent.height - 40
                model: player.playlist.split("\n").filter(x => x.length > 0)

                delegate: Rectangle {
                    width: parent.width
                    height: 30
                    color: index === 0 ? "#1a1a1a" : "transparent"
                    border.bottom: 1
                    border.color: "#222"

                    Text {
                        text: modelData
                        color: "#aaa"
                        anchors.fill: parent
                        anchors.margins: 5
                        elide: Text.ElideRight
                        verticalAlignment: Text.AlignVCenter
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            var idx = parseInt(modelData.split(":")[0])
                            player.openFile(player.playlist.split("\n")[idx].replace(/^\d+: /, ""))
                        }
                    }
                }
            }
        }
    }

    // Subtitle display overlay
    Rectangle {
        id: subtitleArea
        anchors.left: parent.left
        anchors.right: playlistArea.left
        anchors.bottom: timeline.top
        anchors.margins: 20
        height: 60
        color: "transparent"

        Text {
            anchors.centerIn: parent
            text: "Subtitle placeholder"
            color: "#fff"
            font.pixelSize: 16
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
            width: parent.width
        }
    }

    // Timeline / Progress bar
    Rectangle {
        id: timeline
        height: 8
        anchors.left: parent.left
        anchors.right: playlistArea.left
        anchors.bottom: controls.top
        color: "#222"

        Rectangle {
            height: parent.height
            width: player.duration > 0 ? (player.position / player.duration) * parent.width : 0
            color: "#ff6b35"
        }

        MouseArea {
            anchors.fill: parent
            onClicked: {
                var ratio = mouse.x / parent.width
                player.seek(ratio * player.duration)
            }
        }
    }

    // Controls bar
    Rectangle {
        id: controls
        height: 80
        anchors.left: parent.left
        anchors.right: playlistArea.left
        anchors.bottom: parent.bottom
        color: "#111"
        opacity: 0.95

        Column {
            anchors.fill: parent
            spacing: 5
            padding: 10

            Row {
                spacing: 5

                Text {
                    text: formatTime(player.position)
                    color: "#aaa"
                    font.pixelSize: 12
                }

                Text {
                    text: " / " + formatTime(player.duration)
                    color: "#666"
                    font.pixelSize: 12
                }
            }

            Row {
                spacing: 10

                Button {
                    text: "📂 Open"
                    onClicked: fileDialog.open()
                }

                Button {
                    text: player.isPlaying ? "⏸ Pause" : "▶ Play"
                    onClicked: player.isPlaying ? player.pause() : player.play()
                }

                Button {
                    text: "⏹ Stop"
                    onClicked: player.stop()
                }

                Button {
                    text: "⏮ Prev"
                    onClicked: player.playPrevious()
                }

                Button {
                    text: "⏭ Next"
                    onClicked: player.playNext()
                }

                CheckBox {
                    text: "Loop All"
                    onClicked: player.setLoopMode(checked ? 2 : 0)
                }

                CheckBox {
                    text: "Shuffle"
                    onClicked: player.setShuffle(checked)
                }

                Button {
                    text: "📝 Subtitles"
                    onClicked: subtitleDialog.open()
                }

                Button {
                    text: "⚙ Filters"
                    onClicked: filterPopup.open()
                }
            }
        }
    }

    function formatTime(ms) {
        var seconds = Math.floor(ms / 1000)
        var minutes = Math.floor(seconds / 60)
        var hours = Math.floor(minutes / 60)
        
        var h = hours
        var m = minutes % 60
        var s = seconds % 60
        
        return (h > 0 ? h + ":" : "") + 
               (m < 10 && h > 0 ? "0" : "") + m + ":" + 
               (s < 10 ? "0" : "") + s
    }
}

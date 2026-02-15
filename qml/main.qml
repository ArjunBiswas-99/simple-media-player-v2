import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ApplicationWindow {
    id: root
    visible: true
    width: 1200
    height: 600
    title: "Media Player - Prototype"

    Rectangle {
        anchors.fill: parent
        color: "#1a1a1a"

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 10

            // Video area
            Rectangle {
                id: videoArea
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: "#000000"
                
                Text {
                    anchors.centerIn: parent
                    text: "Video Player Area"
                    color: "#ffffff"
                    font.pixelSize: 20
                }
            }

            // Controls
            RowLayout {
                Layout.fillWidth: true
                spacing: 5

                Button {
                    text: "Open File"
                    onClicked: {
                        console.log("Open File clicked")
                    }
                }

                Button {
                    text: "Play"
                    onClicked: {
                        console.log("Play clicked")
                    }
                }

                Button {
                    text: "Pause"
                    onClicked: {
                        console.log("Pause clicked")
                    }
                }

                Button {
                    text: "Stop"
                    onClicked: {
                        console.log("Stop clicked")
                    }
                }

                Slider {
                    Layout.fillWidth: true
                    from: 0
                    to: 100
                    value: 0
                }

                Text {
                    text: "00:00 / 00:00"
                    color: "#ffffff"
                }
            }
        }
    }
}

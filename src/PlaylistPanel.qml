import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: playlistPanel
    width: 400
    color: "#1C1C1C"
    
    property bool isOpen: false
    
    // Shadow effect using simple border
    border.width: 1
    border.color: "#000000"
    
    ColumnLayout {
        anchors.fill: parent
        spacing: 0
        
        // Header
        Rectangle {
            Layout.fillWidth: true
            height: 60
            color: "#242424"
            
            RowLayout {
                anchors.fill: parent
                anchors.margins: 15
                
                Text {
                    text: "Playlist"
                    color: "#FFFFFF"
                    font.pixelSize: 20
                    font.bold: true
                    Layout.fillWidth: true
                }
                
                Button {
                    id: closeBtn
                    width: 32
                    height: 32
                    
                    background: Rectangle {
                        color: closeBtn.hovered ? "#E50914" : "transparent"
                        radius: 4
                    }
                    
                    contentItem: Text {
                        text: "✕"
                        color: "#FFFFFF"
                        font.pixelSize: 18
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    
                    onClicked: {
                        playlistPanel.isOpen = false
                    }
                }
            }
        }
        
        // Playlist items
        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            
            ListView {
                id: playlistView
                anchors.fill: parent
                spacing: 2
                
                // Mock data
                model: ListModel {
                    ListElement {
                        title: "Sample Video 1.mp4"
                        duration: "12:34"
                        thumbnail: ""
                    }
                    ListElement {
                        title: "Sample Video 2.mov"
                        duration: "8:45"
                        thumbnail: ""
                    }
                    ListElement {
                        title: "Sample Video 3.ts"
                        duration: "15:22"
                        thumbnail: ""
                    }
                    ListElement {
                        title: "Sample Video 4.mp4"
                        duration: "6:30"
                        thumbnail: ""
                    }
                    ListElement {
                        title: "Sample Video 5.wmv"
                        duration: "10:15"
                        thumbnail: ""
                    }
                }
                
                delegate: Rectangle {
                    width: playlistView.width
                    height: 120
                    color: mouseArea.containsMouse ? "#2C2C2C" : "transparent"
                    
                    Behavior on color {
                        ColorAnimation { duration: 150 }
                    }
                    
                    MouseArea {
                        id: mouseArea
                        anchors.fill: parent
                        hoverEnabled: true
                    }
                    
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 15
                        
                        // Thumbnail placeholder
                        Rectangle {
                            width: 160
                            height: 90
                            color: "#000000"
                            radius: 4
                            
                            Layout.alignment: Qt.AlignVCenter
                            
                            Text {
                                anchors.centerIn: parent
                                text: "🎬"
                                color: "#666666"
                                font.pixelSize: 32
                            }
                            
                            // Duration overlay
                            Rectangle {
                                anchors.right: parent.right
                                anchors.bottom: parent.bottom
                                anchors.margins: 5
                                width: durationText.width + 8
                                height: durationText.height + 4
                                color: "#CC000000"
                                radius: 2
                                
                                Text {
                                    id: durationText
                                    anchors.centerIn: parent
                                    text: model.duration
                                    color: "#FFFFFF"
                                    font.pixelSize: 11
                                }
                            }
                        }
                        
                        // Video info
                        ColumnLayout {
                            Layout.fillWidth: true
                            Layout.alignment: Qt.AlignVCenter
                            spacing: 5
                            
                            Text {
                                text: model.title
                                color: "#FFFFFF"
                                font.pixelSize: 14
                                elide: Text.ElideRight
                                Layout.fillWidth: true
                            }
                            
                            Text {
                                text: "Ready to play"
                                color: "#AAAAAA"
                                font.pixelSize: 12
                            }
                        }
                    }
                }
            }
        }
    }
}

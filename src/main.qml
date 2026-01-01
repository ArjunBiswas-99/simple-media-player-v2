import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ApplicationWindow {
    id: mainWindow
    visible: true
    width: 1280
    height: 720
    minimumWidth: 800
    minimumHeight: 600
    title: "Simple Media Player"
    color: "#141414"
    
    // File dialog for opening media files
    FileDialog {
        id: fileDialog
        title: "Open Media File"
        nameFilters: ["Media files (*.mp4 *.mov *.wmv *.ts *.mpeg *.mp3 *.wav)", "All files (*)"]
        onAccepted: {
            mediaPlayer.openFile(fileDialog.selectedFile.toString())
        }
    }
    
    // Menu Bar (VLC-style)
    menuBar: MenuBar {
        background: Rectangle {
            color: "#1C1C1C"
            
            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: "#333333"
            }
        }
        
        delegate: MenuBarItem {
            id: menuBarItem
            
            contentItem: Text {
                text: menuBarItem.text.replace("&", "")
                font.pixelSize: 13
                opacity: enabled ? 1.0 : 0.3
                color: menuBarItem.highlighted ? "#E50914" : "#FFFFFF"
                horizontalAlignment: Text.AlignLeft
                verticalAlignment: Text.AlignVCenter
                elide: Text.ElideRight
            }
            
            background: Rectangle {
                opacity: enabled ? 1 : 0.3
                color: menuBarItem.highlighted ? "#2C2C2C" : "transparent"
            }
        }
        
        Menu {
            title: "&Media"
            
            background: Rectangle {
                color: "#1C1C1C"
                border.color: "#333333"
                border.width: 1
            }
            
            delegate: MenuItem {
                id: menuItem
                
                implicitWidth: 200
                implicitHeight: 30
                
                contentItem: Text {
                    text: menuItem.text.replace("&", "")
                    font.pixelSize: 13
                    opacity: enabled ? 1.0 : 0.3
                    color: "#FFFFFF"
                    horizontalAlignment: Text.AlignLeft
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                    leftPadding: 10
                    rightPadding: menuItem.subMenu ? 30 : 10
                }
                
                arrow: Text {
                    visible: menuItem.subMenu
                    text: "▶"
                    color: "#FFFFFF"
                    opacity: 0.6
                    font.pixelSize: 10
                }
                
                background: Rectangle {
                    opacity: enabled ? 1 : 0.3
                    color: menuItem.highlighted ? "#E50914" : "transparent"
                }
            }
            
            Action {
                text: "Open &File..."
                shortcut: "Ctrl+O"
                onTriggered: fileDialog.open()
            }
            
            Action {
                text: "Open F&older..."
                shortcut: "Ctrl+F"
            }
            
            MenuSeparator {
                contentItem: Rectangle {
                    implicitWidth: 200
                    implicitHeight: 1
                    color: "#333333"
                }
            }
            
            Action {
                text: "&Quit"
                shortcut: "Ctrl+Q"
                onTriggered: Qt.quit()
            }
        }
        
        Menu {
            title: "&Playback"
            
            background: Rectangle {
                color: "#1C1C1C"
                border.color: "#333333"
                border.width: 1
            }
            
            delegate: MenuItem {
                id: playbackMenuItem
                
                implicitWidth: 200
                implicitHeight: 30
                
                contentItem: Text {
                    text: playbackMenuItem.text.replace("&", "")
                    font.pixelSize: 13
                    opacity: enabled ? 1.0 : 0.3
                    color: "#FFFFFF"
                    horizontalAlignment: Text.AlignLeft
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                    leftPadding: 10
                    rightPadding: playbackMenuItem.subMenu ? 30 : 10
                }
                
                arrow: Text {
                    visible: playbackMenuItem.subMenu
                    text: "▶"
                    color: "#FFFFFF"
                    opacity: 0.6
                    font.pixelSize: 10
                }
                
                background: Rectangle {
                    opacity: enabled ? 1 : 0.3
                    color: playbackMenuItem.highlighted ? "#E50914" : "transparent"
                }
            }
            
            Menu {
                title: "Speed"
                
                background: Rectangle {
                    color: "#1C1C1C"
                    border.color: "#333333"
                    border.width: 1
                }
                
                delegate: MenuItem {
                    id: speedMenuItem
                    
                    implicitWidth: 200
                    implicitHeight: 30
                    
                    contentItem: Text {
                        text: speedMenuItem.text.replace("&", "")
                        font.pixelSize: 13
                        opacity: enabled ? 1.0 : 0.3
                        color: "#FFFFFF"
                        horizontalAlignment: Text.AlignLeft
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                        leftPadding: 10
                        rightPadding: 10
                    }
                    
                    background: Rectangle {
                        opacity: enabled ? 1 : 0.3
                        color: speedMenuItem.highlighted ? "#E50914" : "transparent"
                    }
                }
                
                Action { text: "Faster" }
                Action { text: "Normal" }
                Action { text: "Slower" }
            }
        }
        
        Menu {
            title: "&Audio"
            
            background: Rectangle {
                color: "#1C1C1C"
                border.color: "#333333"
                border.width: 1
            }
            
            delegate: MenuItem {
                id: audioMenuItem
                
                implicitWidth: 200
                implicitHeight: 30
                
                contentItem: Text {
                    text: audioMenuItem.text.replace("&", "")
                    font.pixelSize: 13
                    opacity: enabled ? 1.0 : 0.3
                    color: "#FFFFFF"
                    horizontalAlignment: Text.AlignLeft
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                    leftPadding: 10
                    rightPadding: audioMenuItem.subMenu ? 30 : 10
                }
                
                arrow: Text {
                    visible: audioMenuItem.subMenu
                    text: "▶"
                    color: "#FFFFFF"
                    opacity: 0.6
                    font.pixelSize: 10
                }
                
                background: Rectangle {
                    opacity: enabled ? 1 : 0.3
                    color: audioMenuItem.highlighted ? "#E50914" : "transparent"
                }
            }
            
            Menu {
                title: "Audio Track"
                
                background: Rectangle {
                    color: "#1C1C1C"
                    border.color: "#333333"
                    border.width: 1
                }
                
                delegate: MenuItem {
                    id: audioTrackMenuItem
                    
                    implicitWidth: 200
                    implicitHeight: 30
                    
                    contentItem: Text {
                        text: audioTrackMenuItem.text.replace("&", "")
                        font.pixelSize: 13
                        opacity: enabled ? 1.0 : 0.3
                        color: "#FFFFFF"
                        horizontalAlignment: Text.AlignLeft
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                        leftPadding: 10
                        rightPadding: 10
                    }
                    
                    background: Rectangle {
                        opacity: enabled ? 1 : 0.3
                        color: audioTrackMenuItem.highlighted ? "#E50914" : "transparent"
                    }
                }
                
                Action { text: "Track 1" }
                Action { text: "Disable" }
            }
        }
        
        Menu {
            title: "&Video"
            
            background: Rectangle {
                color: "#1C1C1C"
                border.color: "#333333"
                border.width: 1
            }
            
            delegate: MenuItem {
                id: videoMenuItem
                
                implicitWidth: 200
                implicitHeight: 30
                
                contentItem: Text {
                    text: videoMenuItem.text.replace("&", "")
                    font.pixelSize: 13
                    opacity: enabled ? 1.0 : 0.3
                    color: "#FFFFFF"
                    horizontalAlignment: Text.AlignLeft
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                    leftPadding: 10
                    rightPadding: videoMenuItem.subMenu ? 30 : 10
                }
                
                arrow: Text {
                    visible: videoMenuItem.subMenu
                    text: "▶"
                    color: "#FFFFFF"
                    opacity: 0.6
                    font.pixelSize: 10
                }
                
                background: Rectangle {
                    opacity: enabled ? 1 : 0.3
                    color: videoMenuItem.highlighted ? "#E50914" : "transparent"
                }
            }
            
            Menu {
                title: "Video Track"
                
                background: Rectangle {
                    color: "#1C1C1C"
                    border.color: "#333333"
                    border.width: 1
                }
                
                delegate: MenuItem {
                    id: videoTrackMenuItem
                    
                    implicitWidth: 200
                    implicitHeight: 30
                    
                    contentItem: Text {
                        text: videoTrackMenuItem.text.replace("&", "")
                        font.pixelSize: 13
                        opacity: enabled ? 1.0 : 0.3
                        color: "#FFFFFF"
                        horizontalAlignment: Text.AlignLeft
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                        leftPadding: 10
                        rightPadding: 10
                    }
                    
                    background: Rectangle {
                        opacity: enabled ? 1 : 0.3
                        color: videoTrackMenuItem.highlighted ? "#E50914" : "transparent"
                    }
                }
                
                Action { text: "Track 1" }
                Action { text: "Disable" }
            }
            
            MenuSeparator {
                contentItem: Rectangle {
                    implicitWidth: 200
                    implicitHeight: 1
                    color: "#333333"
                }
            }
            
            Menu {
                title: "Aspect Ratio"
                
                background: Rectangle {
                    color: "#1C1C1C"
                    border.color: "#333333"
                    border.width: 1
                }
                
                delegate: MenuItem {
                    id: aspectMenuItem
                    
                    implicitWidth: 200
                    implicitHeight: 30
                    
                    contentItem: Text {
                        text: aspectMenuItem.text.replace("&", "")
                        font.pixelSize: 13
                        opacity: enabled ? 1.0 : 0.3
                        color: "#FFFFFF"
                        horizontalAlignment: Text.AlignLeft
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                        leftPadding: 10
                        rightPadding: 10
                    }
                    
                    background: Rectangle {
                        opacity: enabled ? 1 : 0.3
                        color: aspectMenuItem.highlighted ? "#E50914" : "transparent"
                    }
                }
                
                Action { text: "Default" }
                Action { text: "16:9" }
                Action { text: "4:3" }
                Action { text: "1:1" }
            }
            
            Menu {
                title: "Crop"
                
                background: Rectangle {
                    color: "#1C1C1C"
                    border.color: "#333333"
                    border.width: 1
                }
                
                delegate: MenuItem {
                    id: cropMenuItem
                    
                    implicitWidth: 200
                    implicitHeight: 30
                    
                    contentItem: Text {
                        text: cropMenuItem.text.replace("&", "")
                        font.pixelSize: 13
                        opacity: enabled ? 1.0 : 0.3
                        color: "#FFFFFF"
                        horizontalAlignment: Text.AlignLeft
                        verticalAlignment: Text.AlignVCenter
                        elide: Text.ElideRight
                        leftPadding: 10
                        rightPadding: 10
                    }
                    
                    background: Rectangle {
                        opacity: enabled ? 1 : 0.3
                        color: cropMenuItem.highlighted ? "#E50914" : "transparent"
                    }
                }
                
                Action { text: "Default" }
                Action { text: "16:9" }
                Action { text: "4:3" }
            }
        }
        
        Menu {
            title: "&Tools"
            
            background: Rectangle {
                color: "#1C1C1C"
                border.color: "#333333"
                border.width: 1
            }
            
            delegate: MenuItem {
                id: toolsMenuItem
                
                implicitWidth: 200
                implicitHeight: 30
                
                contentItem: Text {
                    text: toolsMenuItem.text.replace("&", "")
                    font.pixelSize: 13
                    opacity: enabled ? 1.0 : 0.3
                    color: "#FFFFFF"
                    horizontalAlignment: Text.AlignLeft
                    verticalAlignment: Text.AlignVCenter
                    elide: Text.ElideRight
                    leftPadding: 10
                    rightPadding: 10
                }
                
                background: Rectangle {
                    opacity: enabled ? 1 : 0.3
                    color: toolsMenuItem.highlighted ? "#E50914" : "transparent"
                }
            }
            
            Action { text: "Preferences..." }
        }
    }
    
    // Main content area (placeholder for video)
    Rectangle {
        id: videoArea
        anchors.fill: parent
        color: "#000000"
        
        // Mouse tracking for control bar visibility
        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            propagateComposedEvents: true
            
            onPositionChanged: {
                controlBar.visible = true
                controlBar.opacity = 1.0
                hideTimer.restart()
            }
            
            onExited: {
                hideTimer.restart()
            }
        }
        
        // Timer to auto-hide controls after 3 seconds of inactivity
        Timer {
            id: hideTimer
            interval: 3000
            repeat: false
            
            onTriggered: {
                if (!playlistPanel.isOpen) {
                    controlBar.opacity = 0.0
                }
            }
        }
        
        Component.onCompleted: {
            hideTimer.start()
        }
        
        // Video placeholder
        Rectangle {
            anchors.fill: parent
            color: "#000000"
            
            Text {
                anchors.centerIn: parent
                text: "Video Display Area\n(Placeholder)"
                color: "#666666"
                font.pixelSize: 32
                horizontalAlignment: Text.AlignHCenter
            }
        }
        
        // Playlist Panel (slide-in from right)
        PlaylistPanel {
            id: playlistPanel
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.right: parent.right
            anchors.rightMargin: playlistPanel.isOpen ? 0 : -playlistPanel.width
            
            Behavior on anchors.rightMargin {
                NumberAnimation {
                    duration: 300
                    easing.type: Easing.OutCubic
                }
            }
        }
        
        // Control bar overlay (positioned at bottom)
        ControlBar {
            id: controlBar
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            
            opacity: 1.0
            
            Behavior on opacity {
                NumberAnimation {
                    duration: 300
                    easing.type: Easing.InOutQuad
                }
            }
            
            onPlaylistToggled: {
                playlistPanel.isOpen = !playlistPanel.isOpen
                if (playlistPanel.isOpen) {
                    // Keep controls visible when playlist is open
                    hideTimer.stop()
                    controlBar.opacity = 1.0
                } else {
                    hideTimer.restart()
                }
            }
        }
    }
}

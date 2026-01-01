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
        Menu {
            title: "&Media"
            
            Action {
                text: "Open &File..."
                shortcut: "Ctrl+O"
                onTriggered: fileDialog.open()
            }
            
            Action {
                text: "Open F&older..."
                shortcut: "Ctrl+F"
            }
            
            MenuSeparator {}
            
            Action {
                text: "&Quit"
                shortcut: "Ctrl+Q"
                onTriggered: Qt.quit()
            }
        }
        
        Menu {
            title: "&Playback"
            
            Menu {
                title: "Speed"
                
                Action { text: "Faster" }
                Action { text: "Normal" }
                Action { text: "Slower" }
            }
        }
        
        Menu {
            title: "&Audio"
            
            Menu {
                title: "Audio Track"
                
                Action { text: "Track 1" }
                Action { text: "Disable" }
            }
        }
        
        Menu {
            title: "&Video"
            
            Menu {
                title: "Video Track"
                
                Action { text: "Track 1" }
                Action { text: "Disable" }
            }
            
            MenuSeparator {}
            
            Menu {
                title: "Aspect Ratio"
                
                Action { text: "Default" }
                Action { text: "16:9" }
                Action { text: "4:3" }
                Action { text: "1:1" }
            }
            
            Menu {
                title: "Crop"
                
                Action { text: "Default" }
                Action { text: "16:9" }
                Action { text: "4:3" }
            }
        }
        
        Menu {
            title: "&Tools"
            
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

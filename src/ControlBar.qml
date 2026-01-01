import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: controlBar
    height: 120
    color: "transparent"
    
    // Signal to communicate with parent
    signal playlistToggled()
    
    // Format seconds to MM:SS
    function formatTime(seconds) {
        if (isNaN(seconds) || seconds < 0) return "0:00"
        var mins = Math.floor(seconds / 60)
        var secs = Math.floor(seconds % 60)
        return mins + ":" + (secs < 10 ? "0" : "") + secs
    }
    
    // Gradient background overlay
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "transparent" }
            GradientStop { position: 1.0; color: "#CC000000" }
        }
    }
    
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 10
        
        // Progress bar area
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            
            Text {
                id: currentTime
                text: controlBar.formatTime(mediaPlayer ? mediaPlayer.position : 0)
                color: "#FFFFFF"
                font.pixelSize: 14
            }
            
            Rectangle {
                id: progressBarBackground
                Layout.fillWidth: true
                height: 6
                color: "#404040"
                radius: 3
                
                Rectangle {
                    id: progressBarFill
                    width: (mediaPlayer && mediaPlayer.duration > 0) ? (mediaPlayer.position / mediaPlayer.duration) * parent.width : 0
                    height: parent.height
                    color: "#E50914"
                    radius: 3
                }
                
                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    
                    onEntered: {
                        progressBarBackground.height = 8
                    }
                    
                    onExited: {
                        progressBarBackground.height = 6
                    }
                    
                    onClicked: {
                        if (mediaPlayer && mediaPlayer.duration > 0) {
                            var newPosition = (mouse.x / width) * mediaPlayer.duration
                            mediaPlayer.setPosition(newPosition)
                        }
                    }
                }
            }
            
            Text {
                id: totalTime
                text: controlBar.formatTime(mediaPlayer ? mediaPlayer.duration : 0)
                color: "#FFFFFF"
                font.pixelSize: 14
            }
        }
        
        // Control buttons row
        RowLayout {
            Layout.fillWidth: true
            spacing: 15
            
            // Left section: Play controls
            RowLayout {
                spacing: 15
                
                // Play/Pause button
                Button {
                    id: playPauseBtn
                    width: 44
                    height: 44
                    
                    scale: playPauseBtn.pressed ? 0.95 : (playPauseBtn.hovered ? 1.05 : 1.0)
                    
                    Behavior on scale {
                        NumberAnimation {
                            duration: 100
                            easing.type: Easing.OutQuad
                        }
                    }
                    
                    background: Rectangle {
                        color: playPauseBtn.hovered ? "#E50914" : "transparent"
                        radius: 22
                        border.width: playPauseBtn.hovered ? 0 : 2
                        border.color: "#FFFFFF"
                        
                        Behavior on color {
                            ColorAnimation { duration: 150 }
                        }
                    }
                    
                    contentItem: Text {
                        text: (mediaPlayer && mediaPlayer.playing) ? "⏸" : "▶"
                        color: "#FFFFFF"
                        font.pixelSize: 18
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    
                    onClicked: {
                        if (mediaPlayer) mediaPlayer.togglePlayPause()
                    }
                }
                
                // Previous button (seek backward)
                Button {
                    id: previousBtn
                    width: 36
                    height: 36
                    
                    scale: previousBtn.pressed ? 0.9 : 1.0
                    opacity: previousBtn.hovered ? 1.0 : 0.8
                    
                    Behavior on scale {
                        NumberAnimation { duration: 100 }
                    }
                    
                    Behavior on opacity {
                        NumberAnimation { duration: 150 }
                    }
                    
                    background: Rectangle {
                        color: previousBtn.hovered ? "#FFFFFF22" : "transparent"
                        radius: 4
                    }
                    
                    contentItem: Text {
                        text: "⏮"
                        color: "#FFFFFF"
                        font.pixelSize: 16
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    
                    onClicked: {
                        if (mediaPlayer) mediaPlayer.seek(-10)
                    }
                }
                
                // Next button (seek forward)
                Button {
                    id: nextBtn
                    width: 36
                    height: 36
                    
                    scale: nextBtn.pressed ? 0.9 : 1.0
                    opacity: nextBtn.hovered ? 1.0 : 0.8
                    
                    Behavior on scale {
                        NumberAnimation { duration: 100 }
                    }
                    
                    Behavior on opacity {
                        NumberAnimation { duration: 150 }
                    }
                    
                    background: Rectangle {
                        color: nextBtn.hovered ? "#FFFFFF22" : "transparent"
                        radius: 4
                    }
                    
                    contentItem: Text {
                        text: "⏭"
                        color: "#FFFFFF"
                        font.pixelSize: 16
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                    
                    onClicked: {
                        if (mediaPlayer) mediaPlayer.seek(10)
                    }
                }
                
                // Volume controls
                RowLayout {
                    spacing: 10
                    
                    Button {
                        id: muteBtn
                        width: 32
                        height: 32
                        
                        background: Rectangle {
                            color: muteBtn.hovered ? "#FFFFFF22" : "transparent"
                            radius: 4
                        }
                        
                        contentItem: Text {
                            text: "🔊"
                            color: "#FFFFFF"
                            font.pixelSize: 16
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                        
                        onClicked: {
                            if (mediaPlayer) mediaPlayer.toggleMute()
                        }
                    }
                    
                    Slider {
                        id: volumeSlider
                        from: 0
                        to: 100
                        value: mediaPlayer ? mediaPlayer.volume : 80
                        width: 100
                        
                        onValueChanged: {
                            if (mediaPlayer && Math.abs(value - mediaPlayer.volume) > 1) {
                                mediaPlayer.setVolume(value)
                            }
                        }
                        
                        background: Rectangle {
                            x: volumeSlider.leftPadding
                            y: volumeSlider.topPadding + volumeSlider.availableHeight / 2 - height / 2
                            width: volumeSlider.availableWidth
                            height: 4
                            radius: 2
                            color: "#404040"
                            
                            Rectangle {
                                width: volumeSlider.visualPosition * parent.width
                                height: parent.height
                                color: "#FFFFFF"
                                radius: 2
                            }
                        }
                        
                        handle: Rectangle {
                            x: volumeSlider.leftPadding + volumeSlider.visualPosition * (volumeSlider.availableWidth - width)
                            y: volumeSlider.topPadding + volumeSlider.availableHeight / 2 - height / 2
                            width: 14
                            height: 14
                            radius: 7
                            color: volumeSlider.pressed ? "#E50914" : "#FFFFFF"
                        }
                    }
                }
            }
            
            // Spacer
            Item {
                Layout.fillWidth: true
            }
            
            // Right section: Playlist and Fullscreen
            RowLayout {
                spacing: 15
                
                // Playlist button (Netflix "Episodes" style)
                Button {
                    id: playlistBtn
                    height: 36
                    
                    scale: playlistBtn.pressed ? 0.95 : 1.0
                    
                    Behavior on scale {
                        NumberAnimation { duration: 100 }
                    }
                    
                    background: Rectangle {
                        color: playlistBtn.hovered ? "#FFFFFF22" : "transparent"
                        radius: 4
                        border.width: 1
                        border.color: "#FFFFFF44"
                    }
                    
                    contentItem: RowLayout {
                        spacing: 8
                        
                        Text {
                            text: "☰"
                            color: "#FFFFFF"
                            font.pixelSize: 18
                        }
                        
                        Text {
                            text: "Playlist"
                            color: "#FFFFFF"
                            font.pixelSize: 14
                        }
                    }
                    
                    onClicked: {
                        controlBar.playlistToggled()
                    }
                }
                
                // Fullscreen button
                Button {
                    id: fullscreenBtn
                    width: 36
                    height: 36
                    
                    scale: fullscreenBtn.pressed ? 0.9 : 1.0
                    opacity: fullscreenBtn.hovered ? 1.0 : 0.8
                    
                    Behavior on scale {
                        NumberAnimation { duration: 100 }
                    }
                    
                    Behavior on opacity {
                        NumberAnimation { duration: 150 }
                    }
                    
                    background: Rectangle {
                        color: fullscreenBtn.hovered ? "#FFFFFF22" : "transparent"
                        radius: 4
                    }
                    
                    contentItem: Text {
                        text: "⛶"
                        color: "#FFFFFF"
                        font.pixelSize: 18
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }
    }
}

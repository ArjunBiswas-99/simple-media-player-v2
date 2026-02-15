import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ApplicationWindow {
    id: root
    visible: true
    width: 1400
    height: 800
    title: "ArjunBiswasMediaPlayer"
    color: "#000000"

    property bool controlsVisible: true
    property int hideControlsTimer: 0

    // Timer to auto-hide controls (Netflix style)
    Timer {
        id: autoHideTimer
        interval: 3000
        running: false
        onTriggered: {
            if (videoArea.containsMouse) {
                controlsVisible = false
            }
        }
    }

    // ============= MENU BAR =============
    menuBar: MenuBar {
        id: menuBar
        background: Rectangle {
            color: "#1a1a1a"
            border.color: "#333333"
            border.width: 1
        }

        Menu {
            title: "File"
            MenuItem { text: "Open File..."; onTriggered: fileDialog.open() }
            MenuItem { text: "Open URL..."; }
            MenuSeparator { }
            MenuItem { text: "Recent Files"; }
            MenuSeparator { }
            MenuItem { text: "Exit"; onTriggered: root.close() }
        }

        Menu {
            title: "Edit"
            MenuItem { text: "Preferences..."; }
            MenuItem { text: "Clear Playlist"; }
        }

        Menu {
            title: "View"
            MenuItem { text: "Fullscreen"; checkable: true; }
            MenuItem { text: "Always on Top"; checkable: true; }
            MenuSeparator { }
            MenuItem { text: "Playlist"; checkable: true; checked: true; onTriggered: sidebarLoader.item.visible = !sidebarLoader.item.visible }
            MenuItem { text: "Equalizer"; }
            MenuItem { text: "Video Effects"; }
            MenuSeparator { }
            MenuItem { text: "Aspect Ratio"; }
            MenuItem { text: "Crop"; }
        }

        Menu {
            title: "Tools"
            MenuItem { text: "Synchronization"; }
            MenuItem { text: "Messages/Logs"; }
            MenuItem { text: "Plugins"; }
            MenuItem { text: "Media Information"; }
            MenuItem { text: "Convert/Save"; }
            MenuItem { text: "Streaming"; }
        }

        Menu {
            title: "Playback"
            MenuItem { text: "Play"; }
            MenuItem { text: "Pause"; }
            MenuItem { text: "Stop"; }
            MenuSeparator { }
            MenuItem { text: "Play/Enqueue"; }
            MenuItem { text: "Fast Forward"; }
            MenuItem { text: "Rewind"; }
            MenuSeparator { }
            MenuItem { text: "Frame Forward"; }
            MenuItem { text: "Frame Backward"; }
            MenuSeparator { }
            MenuItem { text: "Normal Speed"; }
            MenuItem { text: "Faster"; }
            MenuItem { text: "Slower"; }
        }

        Menu {
            title: "Audio"
            MenuItem { text: "Audio Track"; }
            MenuItem { text: "Audio Delay"; }
            MenuItem { text: "Volume Up"; }
            MenuItem { text: "Volume Down"; }
            MenuItem { text: "Mute"; checkable: true; }
        }

        Menu {
            title: "Subtitle"
            MenuItem { text: "Subtitle Track"; }
            MenuItem { text: "Load External Subtitle..."; onTriggered: subtitleDialog.open() }
            MenuItem { text: "Delay"; }
            MenuItem { text: "Font Size"; }
        }

        Menu {
            title: "Help"
            MenuItem { text: "Help..."; }
            MenuItem { text: "Check for Updates"; }
            MenuItem { text: "About"; }
        }
    }

    // ============= FILE DIALOGS =============
    FolderDialog {
        id: fileDialog
        onAccepted: console.log("File selected:", selectedFile)
    }

    FolderDialog {
        id: subtitleDialog
        onAccepted: console.log("Subtitle selected:", selectedFile)
    }

    // ============= MAIN LAYOUT =============
    RowLayout {
        anchors.fill: parent
        spacing: 0

        // Video Area
        Rectangle {
            id: videoArea
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#000000"

            MouseArea {
                id: videoMouseArea
                anchors.fill: parent
                hoverEnabled: true

                onEntered: {
                    controlsVisible = true
                    autoHideTimer.stop()
                }

                onExited: {
                    autoHideTimer.start()
                }

                onPositionChanged: {
                    controlsVisible = true
                    autoHideTimer.restart()
                }

                onDoubleClicked: {
                    root.showFullScreen()
                }

                onClicked: {
                    playButton.clicked()
                }
            }

            // Video placeholder
            Text {
                anchors.centerIn: parent
                text: "Video Player Canvas\n\nDouble-click for fullscreen\nSingle-click to play/pause"
                color: "#888888"
                horizontalAlignment: Text.AlignHCenter
                font.pixelSize: 20
            }

            // ============= NETFLIX-STYLE CONTROL BAR =============
            Rectangle {
                id: controlBar
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                height: controlsVisible ? 80 : 0
                color: "transparent"
                clip: true

                Behavior on height {
                    NumberAnimation { duration: 200 }
                }

                // Gradient overlay above controls
                Rectangle {
                    anchors.fill: parent
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "#00000000" }
                        GradientStop { position: 0.5; color: "#80000000" }
                        GradientStop { position: 1.0; color: "#cc000000" }
                    }
                }

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 5

                    // Progress Bar
                    Rectangle {
                        Layout.fillWidth: true
                        height: 4
                        color: "#404040"
                        radius: 2

                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                console.log("Seek to position:", mouse.x / width * 100)
                            }
                        }

                        Rectangle {
                            width: parent.width * 0.3
                            height: parent.height
                            color: "#e50914"
                            radius: 2
                        }
                    }

                    // Controls Row
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        spacing: 10

                        // Playback Controls
                        Button {
                            text: "⏮"
                            font.pixelSize: 16
                            onClicked: console.log("Previous")
                            background: Rectangle { color: "transparent" }
                            contentItem: Text {
                                text: parent.text
                                color: "#ffffff"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                        }

                        Button {
                            id: playButton
                            text: "▶"
                            font.pixelSize: 20
                            onClicked: {
                                text = text === "▶" ? "⏸" : "▶"
                                console.log("Play/Pause toggled")
                            }
                            background: Rectangle { color: "transparent" }
                            contentItem: Text {
                                text: parent.text
                                color: "#ffffff"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                        }

                        Button {
                            text: "⏭"
                            font.pixelSize: 16
                            onClicked: console.log("Next")
                            background: Rectangle { color: "transparent" }
                            contentItem: Text {
                                text: parent.text
                                color: "#ffffff"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                        }

                        Button {
                            text: "⏹"
                            font.pixelSize: 16
                            onClicked: console.log("Stop")
                            background: Rectangle { color: "transparent" }
                            contentItem: Text {
                                text: parent.text
                                color: "#ffffff"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                        }

                        // Time Display
                        Text {
                            text: "00:00"
                            color: "#ffffff"
                            font.pixelSize: 12
                            Layout.preferredWidth: 40
                        }

                        // Volume Control
                        Button {
                            text: "🔊"
                            font.pixelSize: 14
                            background: Rectangle { color: "transparent" }
                            contentItem: Text {
                                text: parent.text
                                color: "#ffffff"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                        }

                        Slider {
                            from: 0
                            to: 100
                            value: 80
                            Layout.preferredWidth: 80
                            Layout.fillHeight: true
                        }

                        // Duration Display
                        Text {
                            text: "00:00"
                            color: "#ffffff"
                            font.pixelSize: 12
                            Layout.preferredWidth: 40
                        }

                        Item { Layout.fillWidth: true }

                        // Advanced Controls
                        Button {
                            text: "🔁"
                            font.pixelSize: 14
                            checkable: true
                            onClicked: console.log("Loop toggled")
                            background: Rectangle { 
                                color: parent.checked ? "#e50914" : "transparent"
                                radius: 3
                            }
                            contentItem: Text {
                                text: parent.text
                                color: "#ffffff"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                        }

                        Button {
                            text: "🔀"
                            font.pixelSize: 14
                            checkable: true
                            onClicked: console.log("Shuffle toggled")
                            background: Rectangle { 
                                color: parent.checked ? "#e50914" : "transparent"
                                radius: 3
                            }
                            contentItem: Text {
                                text: parent.text
                                color: "#ffffff"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                        }

                        Button {
                            text: "🎨"
                            font.pixelSize: 14
                            onClicked: {
                                filterPopup.visible = !filterPopup.visible
                            }
                            background: Rectangle { color: "transparent" }
                            contentItem: Text {
                                text: parent.text
                                color: "#ffffff"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                        }

                        Button {
                            text: "⛶"
                            font.pixelSize: 14
                            onClicked: root.showFullScreen()
                            background: Rectangle { color: "transparent" }
                            contentItem: Text {
                                text: parent.text
                                color: "#ffffff"
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                        }
                    }
                }
            }

            // ============= FILTER POPUP =============
            Rectangle {
                id: filterPopup
                visible: false
                width: 280
                height: 200
                color: "#1a1a1a"
                border.color: "#404040"
                border.width: 1
                radius: 5
                anchors.bottom: controlBar.top
                anchors.right: parent.right
                anchors.rightMargin: 10
                anchors.bottomMargin: 10

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 10
                    spacing: 10

                    Text {
                        text: "Video Filters"
                        color: "#ffffff"
                        font.bold: true
                        font.pixelSize: 14
                    }

                    ColumnLayout {
                        spacing: 8

                        RowLayout {
                            Text { text: "Brightness"; color: "#cccccc"; Layout.preferredWidth: 80 }
                            Slider { from: -100; to: 100; value: 0; Layout.fillWidth: true }
                        }

                        RowLayout {
                            Text { text: "Contrast"; color: "#cccccc"; Layout.preferredWidth: 80 }
                            Slider { from: -100; to: 100; value: 0; Layout.fillWidth: true }
                        }

                        RowLayout {
                            Text { text: "Saturation"; color: "#cccccc"; Layout.preferredWidth: 80 }
                            Slider { from: -100; to: 100; value: 0; Layout.fillWidth: true }
                        }
                    }

                    Button {
                        text: "Reset"
                        Layout.fillWidth: true
                        onClicked: console.log("Filters reset")
                    }
                }
            }
        }

        // ============= SIDEBAR (PLAYLIST) =============
        Loader {
            id: sidebarLoader
            sourceComponent: playlistSidebar
            Layout.preferredWidth: 250
            Layout.fillHeight: true
        }
    }

    // ============= SIDEBAR COMPONENT =============
    Component {
        id: playlistSidebar
        Rectangle {
            color: "#1a1a1a"
            border.color: "#333333"
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 10

                Text {
                    text: "Playlist"
                    color: "#ffffff"
                    font.bold: true
                    font.pixelSize: 14
                }

                RowLayout {
                    Button {
                        text: "+"
                        Layout.preferredWidth: 40
                        onClicked: fileDialog.open()
                    }

                    Button {
                        text: "−"
                        Layout.preferredWidth: 40
                        onClicked: console.log("Remove from playlist")
                    }

                    Button {
                        text: "✕"
                        Layout.preferredWidth: 40
                        onClicked: console.log("Clear playlist")
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    color: "#0a0a0a"
                    radius: 3

                    ListView {
                        anchors.fill: parent
                        anchors.margins: 5
                        spacing: 3

                        model: ListModel {
                            ListElement { name: "Video 1.mp4"; duration: "2:34:15" }
                            ListElement { name: "Video 2.mkv"; duration: "1:45:30" }
                            ListElement { name: "Video 3.avi"; duration: "3:20:00" }
                        }

                        delegate: Rectangle {
                            width: parent.width - 10
                            height: 40
                            color: ListView.isCurrentItem ? "#e50914" : "#333333"
                            radius: 2

                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    parent.ListView.view.currentIndex = index
                                    console.log("Playing:", model.name)
                                }
                            }

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 5
                                spacing: 2

                                Text {
                                    text: model.name
                                    color: "#ffffff"
                                    font.pixelSize: 12
                                    elide: Text.ElideRight
                                }

                                Text {
                                    text: model.duration
                                    color: "#999999"
                                    font.pixelSize: 10
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
